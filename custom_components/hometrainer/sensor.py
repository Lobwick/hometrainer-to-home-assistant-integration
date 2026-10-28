"""Capteurs du home trainer."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HomeTrainerConfigEntry
from .entity import HomeTrainerEntity
from .trainer import Trainer


@dataclass(frozen=True, kw_only=True)
class TrainerSensorDescription(SensorEntityDescription):
    """Capteur calculé à partir de l'état du home trainer."""

    value_fn: Callable[[Trainer], Any]
    attrs_fn: Callable[[Trainer], Mapping[str, Any]] | None = None


SENSORS: tuple[TrainerSensorDescription, ...] = (
    TrainerSensorDescription(
        key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda t: t.metric("power"),
    ),
    TrainerSensorDescription(
        key="power_avg",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda t: t.power_avg,
    ),
    TrainerSensorDescription(
        key="cadence",
        icon="mdi:rotate-right",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda t: t.metric("cadence"),
    ),
    TrainerSensorDescription(
        key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda t: t.metric("speed"),
    ),
    TrainerSensorDescription(
        key="heart_rate",
        icon="mdi:heart-pulse",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda t: t.metric("heart_rate"),
    ),
    TrainerSensorDescription(
        key="distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=2,
        value_fn=lambda t: t.metric("distance"),
    ),
    TrainerSensorDescription(
        key="energy",
        icon="mdi:fire",
        native_unit_of_measurement="kcal",
        value_fn=lambda t: t.metric("energy"),
    ),
    TrainerSensorDescription(
        key="ftp_percent",
        icon="mdi:speedometer",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda t: t.ftp_percent,
    ),
    TrainerSensorDescription(
        key="zone",
        icon="mdi:palette",
        value_fn=lambda t: t.zone,
        attrs_fn=lambda t: t.zone_attributes(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomeTrainerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Ajoute les capteurs."""
    async_add_entities(
        TrainerSensor(entry, entry.runtime_data, description) for description in SENSORS
    )


class TrainerSensor(HomeTrainerEntity, SensorEntity):
    """Capteur du home trainer."""

    entity_description: TrainerSensorDescription
    # Les attributs de zone changent souvent : inutile de les stocker en base.
    _unrecorded_attributes = frozenset(
        {"zone_name", "hex_color", "rgb_color", "ftp_percent", "power_min", "power_max"}
    )

    def __init__(
        self,
        entry: HomeTrainerConfigEntry,
        trainer: Trainer,
        description: TrainerSensorDescription,
    ) -> None:
        super().__init__(entry, trainer, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Valeur courante."""
        return self.entity_description.value_fn(self.trainer)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Attributs complémentaires (capteur de zone)."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.trainer)
