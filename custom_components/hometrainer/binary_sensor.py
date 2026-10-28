"""Capteurs binaires : sur le vélo, app connectée."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HomeTrainerConfigEntry
from .entity import HomeTrainerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomeTrainerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Ajoute les capteurs binaires."""
    trainer = entry.runtime_data
    async_add_entities(
        [OnBikeSensor(entry, trainer, "on_bike"), ConnectedSensor(entry, trainer, "connected")]
    )


class OnBikeSensor(HomeTrainerEntity, BinarySensorEntity):
    """Vrai pendant la séance et jusqu'au délai configuré après le dernier coup de pédale."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:bike"

    @property
    def is_on(self) -> bool:
        """Sur le vélo ?"""
        return self.trainer.on_bike

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Dernier coup de pédale et fin prévue."""
        until = self.trainer.on_bike_until
        last = self.trainer.last_pedaling
        return {
            "last_pedaling": last.isoformat() if last else None,
            "until": until.isoformat() if until else None,
            "delay_minutes": self.trainer.settings.on_bike_delay,
        }


class ConnectedSensor(HomeTrainerEntity, BinarySensorEntity):
    """Vrai tant que l'app envoie des données."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """App connectée ?"""
        return self.trainer.connected

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Nom du home trainer et dernier envoi."""
        last = self.trainer.last_data
        return {
            "trainer": self.trainer.device_name,
            "last_data": last.isoformat() if last else None,
        }
