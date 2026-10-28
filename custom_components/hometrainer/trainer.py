"""État du home trainer : mesures reçues, puissance lissée, zone, présence sur le vélo.

Ce module ne dépend pas de Home Assistant pour pouvoir être testé seul : l'heure
est fournie par une fonction ``now`` et les entités s'abonnent via ``add_listener``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .const import (
    DEFAULT_FTP,
    DEFAULT_ON_BIKE_DELAY,
    DEFAULT_STALE_TIMEOUT,
    DEFAULT_ZONE_COLORS,
    DEFAULT_ZONE_THRESHOLDS,
    OPT_FTP,
    OPT_ON_BIKE_DELAY,
    OPT_STALE_TIMEOUT,
    OPT_ZONE_COLORS,
    OPT_ZONE_THRESHOLDS,
    POWER_AVERAGE_WINDOW,
    ZONE_COUNT,
    ZONE_NAMES,
)

# Clés acceptées dans les données envoyées par l'app.
METRIC_KEYS = ("power", "cadence", "speed", "heart_rate", "distance", "energy")
# Mesures qui retombent à 0 quand le home trainer ne transmet plus.
ZEROED_WHEN_IDLE = ("power", "cadence", "speed")
# Mesures sans valeur quand le home trainer ne transmet plus.
UNKNOWN_WHEN_IDLE = ("heart_rate",)


def hex_to_rgb(color: str) -> list[int]:
    """Convertit « #RRGGBB » en [r, g, b]."""
    color = color.lstrip("#")
    return [int(color[i : i + 2], 16) for i in (0, 2, 4)]


@dataclass
class Settings:
    """Réglages modifiables de l'appareil."""

    ftp: int = DEFAULT_FTP
    on_bike_delay: int = DEFAULT_ON_BIKE_DELAY  # minutes
    zone_colors: list[str] = field(default_factory=lambda: list(DEFAULT_ZONE_COLORS))
    zone_thresholds: list[float] = field(
        default_factory=lambda: list(DEFAULT_ZONE_THRESHOLDS)
    )
    stale_timeout: int = DEFAULT_STALE_TIMEOUT  # secondes

    @classmethod
    def from_options(cls, options: Mapping[str, Any]) -> Settings:
        """Construit les réglages depuis les options de l'entrée."""
        colors = list(options.get(OPT_ZONE_COLORS, DEFAULT_ZONE_COLORS))
        colors = (colors + DEFAULT_ZONE_COLORS)[:ZONE_COUNT]
        thresholds = list(options.get(OPT_ZONE_THRESHOLDS, DEFAULT_ZONE_THRESHOLDS))
        if len(thresholds) != ZONE_COUNT - 1:
            thresholds = list(DEFAULT_ZONE_THRESHOLDS)
        return cls(
            ftp=int(options.get(OPT_FTP, DEFAULT_FTP)),
            on_bike_delay=int(options.get(OPT_ON_BIKE_DELAY, DEFAULT_ON_BIKE_DELAY)),
            zone_colors=colors,
            zone_thresholds=sorted(float(t) for t in thresholds),
            stale_timeout=int(options.get(OPT_STALE_TIMEOUT, DEFAULT_STALE_TIMEOUT)),
        )

    def as_options(self) -> dict[str, Any]:
        """Réglages au format des options de l'entrée."""
        return {
            OPT_FTP: self.ftp,
            OPT_ON_BIKE_DELAY: self.on_bike_delay,
            OPT_ZONE_COLORS: list(self.zone_colors),
            OPT_ZONE_THRESHOLDS: list(self.zone_thresholds),
            OPT_STALE_TIMEOUT: self.stale_timeout,
        }


class Trainer:
    """Mesures et calculs d'un home trainer."""

    def __init__(
        self,
        settings: Settings,
        now: Callable[[], datetime],
        on_settings_changed: Callable[[Settings], None] | None = None,
    ) -> None:
        self.settings = settings
        self._now = now
        self._on_settings_changed = on_settings_changed
        self._metrics: dict[str, float | None] = dict.fromkeys(METRIC_KEYS)
        self._power_window: deque[tuple[datetime, float]] = deque()
        self.last_data: datetime | None = None
        self.last_pedaling: datetime | None = None
        self.device_name: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._snapshot: tuple[Any, ...] | None = None

    # ------------------------------------------------------------------ abonnés
    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Abonne une entité ; renvoie la fonction de désabonnement."""
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify(self) -> None:
        self._snapshot = self._state_snapshot()
        for listener in list(self._listeners):
            listener()

    def _state_snapshot(self) -> tuple[Any, ...]:
        return (
            self.connected,
            self.on_bike,
            self.metric("power"),
            self.metric("cadence"),
            self.metric("speed"),
            self.metric("heart_rate"),
            self.power_avg,
            self.zone,
        )

    def tick(self) -> None:
        """Appelé chaque seconde : prévient les entités si un état a changé tout seul
        (fin de la fenêtre de lissage, perte de connexion, fin du délai « sur le vélo »)."""
        self._prune_window()
        if self._state_snapshot() != self._snapshot:
            self._notify()

    # ------------------------------------------------------------- réception
    def handle_data(self, data: Mapping[str, Any]) -> None:
        """Intègre un envoi de l'app : seules les clés présentes sont mises à jour."""
        now = self._now()
        for key in METRIC_KEYS:
            if key in data and data[key] is not None:
                self._metrics[key] = float(data[key])
        if name := data.get("device"):
            self.device_name = str(name)
        self.last_data = now
        power = self._metrics["power"]
        if power is not None:
            self._power_window.append((now, power))
            if power > 0:
                self.last_pedaling = now
        self._prune_window()
        self._notify()

    def _prune_window(self) -> None:
        limit = self._now() - timedelta(seconds=POWER_AVERAGE_WINDOW)
        while self._power_window and self._power_window[0][0] < limit:
            self._power_window.popleft()

    # ---------------------------------------------------------------- calculs
    @property
    def connected(self) -> bool:
        """Vrai si l'app a envoyé des données récemment."""
        if self.last_data is None:
            return False
        return self._now() - self.last_data <= timedelta(
            seconds=self.settings.stale_timeout
        )

    def metric(self, key: str) -> float | None:
        """Valeur d'une mesure, ramenée à 0 (ou inconnue) quand plus rien n'arrive."""
        if not self.connected:
            if key in ZEROED_WHEN_IDLE:
                return 0
            if key in UNKNOWN_WHEN_IDLE:
                return None
        return self._metrics[key]

    @property
    def power_avg(self) -> float:
        """Puissance moyenne sur les dernières secondes (0 si déconnecté)."""
        if not self.connected or not self._power_window:
            return 0
        return round(sum(p for _, p in self._power_window) / len(self._power_window), 0)

    @property
    def ftp_percent(self) -> float:
        """Puissance lissée en % de la FTP."""
        if self.settings.ftp <= 0:
            return 0
        return round(self.power_avg / self.settings.ftp * 100, 1)

    @property
    def zone(self) -> int:
        """Zone de puissance : 0 = arrêt, 1 à 6 selon les seuils en % de la FTP."""
        if self.power_avg <= 0:
            return 0
        percent = self.ftp_percent
        return 1 + sum(1 for t in self.settings.zone_thresholds if percent >= t)

    def zone_color(self, zone: int) -> str | None:
        """Couleur #RRGGBB d'une zone (aucune pour la zone 0)."""
        if zone < 1:
            return None
        return self.settings.zone_colors[zone - 1]

    def zone_bounds(self, zone: int) -> tuple[int | None, int | None]:
        """Bornes en watts d'une zone (None = pas de borne)."""
        if zone < 1:
            return None, None
        edges = [0.0, *self.settings.zone_thresholds, None]
        low, high = edges[zone - 1], edges[zone]
        ftp = self.settings.ftp
        return (
            round(low * ftp / 100) if low is not None else None,
            round(high * ftp / 100) if high is not None else None,
        )

    def zone_attributes(self) -> dict[str, Any]:
        """Attributs du capteur de zone, pratiques pour les automatisations."""
        zone = self.zone
        color = self.zone_color(zone)
        low, high = self.zone_bounds(zone)
        return {
            "zone_name": ZONE_NAMES[zone],
            "hex_color": color,
            "rgb_color": hex_to_rgb(color) if color else None,
            "ftp_percent": self.ftp_percent,
            "power_min": low,
            "power_max": high,
        }

    @property
    def on_bike(self) -> bool:
        """Vrai pendant le pédalage et jusqu'au délai configuré après le dernier coup de pédale."""
        if self.last_pedaling is None:
            return False
        if self.connected and (self._metrics["power"] or 0) > 0:
            return True
        return self._now() - self.last_pedaling <= timedelta(
            minutes=self.settings.on_bike_delay
        )

    @property
    def on_bike_until(self) -> datetime | None:
        """Heure à laquelle « sur le vélo » repassera à faux si le pédalage ne reprend pas."""
        if self.last_pedaling is None:
            return None
        return self.last_pedaling + timedelta(minutes=self.settings.on_bike_delay)

    # ---------------------------------------------------------------- réglages
    def update_settings(self, **changes: Any) -> None:
        """Modifie des réglages, les enregistre et rafraîchit les entités."""
        for key, value in changes.items():
            setattr(self.settings, key, value)
        if self._on_settings_changed:
            self._on_settings_changed(self.settings)
        self._notify()

    def set_zone_color(self, zone: int, color: str) -> None:
        """Change la couleur d'une zone (1 à 6)."""
        colors = list(self.settings.zone_colors)
        colors[zone - 1] = color.upper()
        self.update_settings(zone_colors=colors)
