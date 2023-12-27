"""Sensor platform integration for Sungrow Inverters"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import (
    DEVICE_CLASS_STATE_CLASSES,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
)
from .core import signals
from .core.inverter import SungrowInverter

logger = logging.getLogger(__name__)


def guess_device_class(unit: str | None) -> SensorDeviceClass | None:
    # A solar specific copy of homeassistant.components.sensor.const.DEVICE_CLASS_UNITS.
    # Note: this is a first guess to avoid writing this in the yaml file.
    device_class_units = {
        SensorDeviceClass.BATTERY: ["%"],
        SensorDeviceClass.POWER: ["kW", "KW", "W"],
        SensorDeviceClass.CURRENT: ["A"],
        SensorDeviceClass.TEMPERATURE: ["°C"],
        SensorDeviceClass.DURATION: ["h", "min"],
        SensorDeviceClass.FREQUENCY: ["Hz"],
        SensorDeviceClass.WEIGHT: ["kg"],
        SensorDeviceClass.REACTIVE_POWER: ["kVar", "Var"],
        SensorDeviceClass.ENERGY: ["kWh"],
        SensorDeviceClass.VOLTAGE: ["V"],
        SensorDeviceClass.APPARENT_POWER: ["VA"],
        # FYI: MM is minute and month. Let's just preserve that bug.
        None: ["k-ohm", "YYYY", "MM", "DD", "HH", "MM", "SS"],
    }

    # If there is no unit, it's probably a fixed value
    if unit is None:
        return SensorDeviceClass.ENUM
    else:
        for device_class, units in device_class_units.items():
            if unit in units:
                return device_class

    logger.warning(f"Unknown unit '{unit}', not sure what device class to use.")
    return None


def guess_state_class(device_class: SensorDeviceClass | None):
    """Guess SensorStateClass.MESAUREMENT or TOTAL"""

    if device_class:
        state_classes = DEVICE_CLASS_STATE_CLASSES.get(device_class, None)
        if state_classes:
            return next(iter(state_classes))

    return SensorStateClass.MEASUREMENT


def create_sensor_entities_from_registers(
    signal_definitions: signals.SignalDefinitions,
    device_entry: DeviceEntry,
    coordinator: DataUpdateCoordinator,
) -> list[SungrowInverterSensorEntity]:
    """Register sensor entities based on the inverter data."""

    entities = []
    for signal in signal_definitions._definitions.values():
        # Don't create entities for disabled signals
        if signal.disabled:
            continue
        entities.append(SungrowInverterSensorEntity(coordinator, signal, device_entry))
    return entities


class InverterCoordinator(DataUpdateCoordinator):
    """Coordinator for pilling data from one inverter."""

    def __init__(self, hass, inverter, update_interval):
        """Initialize the coordinator."""
        self.inverter = inverter
        super().__init__(
            hass,
            logger,
            name="Sungrow Inverter Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        data = await self.inverter.pull_data()
        if data:
            return data
        else:
            raise UpdateFailed("Failed pulling data from Sungrow Inverter")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Setup sensors from a config entry created in the integrations UI.

    Called upon config_flow completion and on start of Home Assistant.
    """

    unique_device_id = config_entry.data.get["device_id"]

    inverter = await SungrowInverter.create(config_entry.data)
    if not inverter:
        # ToDo: better error handling
        raise Exception("Failed to create inverter")

    with inverter:
        # ToDo: ensure timedelta is at least MIN_TIME_BETWEEN_UPDATES
        coordinator = InverterCoordinator(
            hass,
            inverter=inverter,
            update_interval=timedelta(seconds=config_entry.data[CONF_SCAN_INTERVAL]),
        )

        # Fetch data once so it's available for the first update.
        # ToDo: is this really needed?
        await coordinator.async_refresh()

        # Register our inverter device
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, unique_device_id)},
            manufacturer="Sungrow",
            name=f"Sungrow {inverter.getInverterModel()}",
            model=inverter.getInverterModel(),
            serial_number=unique_device_id,
        )

        entities = create_sensor_entities_from_registers(
            inverter._signals, device_entry, coordinator
        )
        logger.warning(f"sensor async_setup_entry entities={entities}")
        async_add_entities(entities, update_before_add=True)

        inverter.detach()


class SungrowInverterSensorEntity(SensorEntity):
    """Implementation of a Sungrow Inverter sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        signal: signals.ModbusSignalDefinition,
        device_entry: DeviceEntry,
    ):
        self.coordinator = coordinator
        self.device_entry = device_entry
        self.signal = signal

        self._attr_device_class = guess_device_class(signal.unit)
        self._attr_state_class = guess_state_class(self.device_class)
        self._attr_name = signal.name.replace("_", " ").title()
        self._attr_native_unit_of_measurement = signal.unit

        self._attr_available = False

        # All data is preserved based on unique id.
        # Note: you'll not see this ID anywhere in the UI.
        sn = coordinator.data["serial_number"]
        self._attr_unique_id = f"sungrow_{sn}_{signal.name}"

    @property
    def suggested_object_id(self) -> str:
        """This is the 'Entity ID' in the UI"""

        # By default (see SensorEntity) this is derived from the name.
        # In order to set them separately, we need to override this property.

        # This object/entity id is the one you'll see across the UI, incl automations.
        # We need object id to be something simple, so it's usable in shared dashboards!

        # ToDo: We don't have access to all inverters here, as this happens one by one.
        #       So it's currently impossible to pick an automatic reasonable name.
        #       We can barely detect whether this is e.g. a master or a slave.
        #       But there is no way to detect if this is a simple master + slave
        #       combination or something else.

        master = self.coordinator.data["is_master"]
        master_str = "master" if master else "slave"

        object_id = f"sungrow_{master_str}_{self.signal.name}"

        logger.warning(f"sensor object id: {object_id}")
        return object_id

    @property
    def native_value(self):
        """Return the state of the sensor. This runs very quickly."""

        # latest data is stored by the coordinator
        data = self.coordinator.data

        value = data.get(self.signal.name, None)
        self._attr_available = value is not None
        return value
