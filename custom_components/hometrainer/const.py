"""Constantes de l'intégration HomeTrainer To Home Assistant."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "hometrainer"
MANUFACTURER: Final = "HomeTrainer To Home Assistant"

CONF_WEBHOOK_ID: Final = "webhook_id"
CONF_CLOUDHOOK_URL: Final = "cloudhook_url"

# Réglages (stockés dans les options de l'entrée, modifiables depuis les entités
# de configuration ou le bouton « Configurer »).
OPT_FTP: Final = "ftp"
OPT_ON_BIKE_DELAY: Final = "on_bike_delay"  # minutes
OPT_ON_BIKE_MIN_PEDALING: Final = "on_bike_min_pedaling"  # minutes
OPT_ZONE_COLORS: Final = "zone_colors"  # 6 couleurs #RRGGBB (zones 1 à 6)
OPT_ZONE_THRESHOLDS: Final = "zone_thresholds"  # 5 seuils en % de la FTP
OPT_STALE_TIMEOUT: Final = "stale_timeout"  # secondes sans données = déconnecté

DEFAULT_NAME: Final = "Home trainer"
DEFAULT_FTP: Final = 250
DEFAULT_ON_BIKE_DELAY: Final = 20
# Pédalage continu nécessaire avant de passer « sur le vélo » (un test ou quelques
# coups de pédale ne comptent pas).
DEFAULT_ON_BIKE_MIN_PEDALING: Final = 5
# Pause de pédalage tolérée sans interrompre la série en cours (s).
PEDALING_PAUSE_TOLERANCE: Final = 30
# Couleurs des zones Zwift (gris, bleu, vert, jaune, orange, rouge).
DEFAULT_ZONE_COLORS: Final = [
    "#A0A0A0",
    "#0078FF",
    "#00C83C",
    "#FFD700",
    "#FF7800",
    "#FF0000",
]
# Bornes basses des zones 2 à 6, en % de la FTP (découpage Zwift).
DEFAULT_ZONE_THRESHOLDS: Final = [60.0, 76.0, 90.0, 105.0, 119.0]
DEFAULT_STALE_TIMEOUT: Final = 5

DEFAULT_OPTIONS: Final = {
    OPT_FTP: DEFAULT_FTP,
    OPT_ON_BIKE_DELAY: DEFAULT_ON_BIKE_DELAY,
    OPT_ON_BIKE_MIN_PEDALING: DEFAULT_ON_BIKE_MIN_PEDALING,
    OPT_ZONE_COLORS: DEFAULT_ZONE_COLORS,
    OPT_ZONE_THRESHOLDS: DEFAULT_ZONE_THRESHOLDS,
    OPT_STALE_TIMEOUT: DEFAULT_STALE_TIMEOUT,
}

ZONE_COUNT: Final = 6
ZONE_NAMES: Final = [
    "Arrêt",
    "Récupération",
    "Endurance",
    "Tempo",
    "Seuil",
    "VO2max",
    "Anaérobie",
]

# Fenêtre de la puissance lissée (s).
POWER_AVERAGE_WINDOW: Final = 3

COLOR_PATTERN: Final = r"^#[0-9A-Fa-f]{6}$"
