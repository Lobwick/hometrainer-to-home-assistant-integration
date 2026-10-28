"""Couleur de chaque zone de puissance (#RRGGBB)."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HomeTrainerConfigEntry
from .const import COLOR_PATTERN, ZONE_COUNT
from .entity import HomeTrainerEntity
from .trainer import Trainer


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomeTrainerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Ajoute une couleur par zone."""
    trainer = entry.runtime_data
    async_add_entities(
        ZoneColorText(entry, trainer, zone) for zone in range(1, ZONE_COUNT + 1)
    )


class ZoneColorText(HomeTrainerEntity, TextEntity):
    """Couleur d'une zone de puissance."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:palette"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 7
    _attr_native_max = 7
    _attr_pattern = COLOR_PATTERN

    def __init__(self, entry: HomeTrainerConfigEntry, trainer: Trainer, zone: int) -> None:
        super().__init__(entry, trainer, f"zone_{zone}_color")
        self._zone = zone
        self._attr_translation_key = "zone_color"
        self._attr_translation_placeholders = {"zone": str(zone)}

    @property
    def native_value(self) -> str:
        """Couleur actuelle."""
        return self.trainer.settings.zone_colors[self._zone - 1]

    async def async_set_value(self, value: str) -> None:
        """Nouvelle couleur."""
        self.trainer.set_zone_color(self._zone, value)
