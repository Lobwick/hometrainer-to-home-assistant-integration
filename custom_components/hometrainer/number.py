"""Réglages numériques : FTP et délai « sur le vélo »."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HomeTrainerConfigEntry
from .entity import HomeTrainerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomeTrainerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Ajoute les réglages numériques."""
    trainer = entry.runtime_data
    async_add_entities(
        [
            FtpNumber(entry, trainer, "ftp"),
            DelayNumber(entry, trainer, "on_bike_delay"),
            MinPedalingNumber(entry, trainer, "on_bike_min_pedaling"),
        ]
    )


class FtpNumber(HomeTrainerEntity, NumberEntity):
    """FTP utilisée pour calculer les zones."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:lightning-bolt"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 50
    _attr_native_max_value = 600
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    @property
    def native_value(self) -> float:
        """FTP actuelle."""
        return self.trainer.settings.ftp

    async def async_set_native_value(self, value: float) -> None:
        """Nouvelle FTP."""
        self.trainer.update_settings(ftp=int(value))


class DelayNumber(HomeTrainerEntity, NumberEntity):
    """Délai pendant lequel on reste « sur le vélo » après le dernier coup de pédale."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-sand"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> float:
        """Délai actuel."""
        return self.trainer.settings.on_bike_delay

    async def async_set_native_value(self, value: float) -> None:
        """Nouveau délai."""
        self.trainer.update_settings(on_bike_delay=int(value))


class MinPedalingNumber(HomeTrainerEntity, NumberEntity):
    """Pédalage continu nécessaire avant de passer « sur le vélo »."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-play-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 60
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> float:
        """Pédalage minimum actuel."""
        return self.trainer.settings.on_bike_min_pedaling

    async def async_set_native_value(self, value: float) -> None:
        """Nouveau pédalage minimum."""
        self.trainer.update_settings(on_bike_min_pedaling=int(value))
