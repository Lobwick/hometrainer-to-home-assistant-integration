"""Entité de base rattachée à l'appareil home trainer."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER
from .trainer import Trainer


class HomeTrainerEntity(Entity):
    """Entité poussée par le home trainer (pas d'interrogation périodique)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, trainer: Trainer, key: str) -> None:
        self.trainer = trainer
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model="Home trainer connecté",
        )

    async def async_added_to_hass(self) -> None:
        """Se met à jour à chaque envoi de l'app ou changement de réglage."""
        await super().async_added_to_hass()
        self.async_on_remove(self.trainer.add_listener(self.async_write_ha_state))
