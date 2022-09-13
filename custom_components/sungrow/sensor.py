"""Integration platform for Sungrow Inverters"""

from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass
import pathlib
import os
import yaml
from pprint import pformat
import logging
import voluptuous as vol

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    DEVICE_CLASS_ENERGY,
    ATTR_MODEL,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PORT,
    CONF_SLAVE,
    CONF_TIMEOUT,
    CONF_HOST,
    ENERGY_KILO_WATT_HOUR,
    PERCENTAGE,
    POWER_WATT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_SCAN_INTERVAL
)
from homeassistant.components.sensor import (
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    DEVICE_CLASS_ENERGY,
    ENERGY_KILO_WATT_HOUR,
    DEVICE_CLASS_POWER,
    POWER_WATT
)

from .SunGather.inverter import SungrowInverter

from .const import (
    MIN_TIME_BETWEEN_UPDATES,
    SUNGROW_DAILY_EXPORT_ENERGY,
    SUNGROW_DAILY_POWER_YIELDS,
    SUNGROW_DAILY_PV_EXPORT,
    SUNGROW_ENERGY_GENERATION,
    SUNGROW_ARRAY1_ENERGY_GENERATION,
    SUNGROW_ARRAY2_ENERGY_GENERATION,
    SUNGROW_EXPORT_POWER_HYBRID,
    SUNGROW_POWER_EXPORT_TO_GRID,
    SUNGROW_POWER_IMPORT_FROM_GRID,
    SUNGROW_LOAD_POWER_HYBRID,
    SUNGROW_METER_POWER,
    SUNGROW_SELF_CONSUMPTION_OF_DAY,
    SUNGROW_TOTAL_ACTIVE_POWER,
    SUNGROW_TOTAL_EXPORT_ENERGY,
    SUNGROW_TOTAL_PV_EXPORT,
    SUNGROW_DAILY_OUTPUT_ENERGY,
    SUNGROW_TOTAL_OUTPUT_ENERGY,
    SUNGROW_LOAD_POWER,
    SUNGROW_EXPORT_POWER,
    SUNGROW_DAILY_BATTERY_CHARGE_PV_ENERGY,
    SUNGROW_TOTAL_BATTERY_CHARGE_PV_ENERGY,
    SUNGROW_DAILY_PV_ENERGY,
    SUNGROW_TOTAL_PV_ENERGY,
    SUNGROW_DAILY_DIRECT_ENERGY_CONSUMPTION,
    SUNGROW_TOTAL_DIRECT_ENERGY_CONSUMPTION,
    SUNGROW_DAILY_IMPORT_ENERGY,
    SUNGROW_TOTAL_IMPORT_ENERGY,
    SUNGROW_DAILY_BATTERY_DISCHARGE_ENERGY,
    SUNGROW_TOTAL_BATTERY_DISCHARGE_ENERGY,
    SUNGROW_DAILY_EXPORT_ENERGY_FROM_PV,
    SUNGROW_TOTAL_EXPORT_ENERGY_FROM_PV,
    SUNGROW_DAILY_EXPORT_ENERGY_FROM_BATTERY,
    SUNGROW_TOTAL_EXPORT_ENERGY_FROM_BATTERY,
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SLAVE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    MIN_TIME_BETWEEN_UPDATES,
)


logger = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
        vol.Optional(CONF_SLAVE, default=DEFAULT_SLAVE): cv.positive_int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(ATTR_MODEL): cv.string,
    }
)


@dataclass
class SungrowInverterSensorEntityDescription(SensorEntityDescription):
    register: str|None = None
    device_id: str|None = None
    device_model: str|None = None


SENSOR_TYPES = (
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_ENERGY_GENERATION,
        register=SUNGROW_ENERGY_GENERATION,
        name="Current PV Power Generation",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_ARRAY1_ENERGY_GENERATION,
        register=SUNGROW_ARRAY1_ENERGY_GENERATION,
        name="Current PV Array 1 Power Generation",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_ARRAY2_ENERGY_GENERATION,
        register=SUNGROW_ARRAY2_ENERGY_GENERATION,
        name="Current PV Array 2 Power Generation",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_OUTPUT_ENERGY,
        register=SUNGROW_DAILY_OUTPUT_ENERGY,
        name="Daily Output Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_OUTPUT_ENERGY,
        register=SUNGROW_TOTAL_OUTPUT_ENERGY,
        name="Total Output Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_LOAD_POWER,
        register=SUNGROW_LOAD_POWER,
        name="Current Load Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_LOAD_POWER_HYBRID,
        register=SUNGROW_LOAD_POWER_HYBRID,
        name="Current Load Power (Hybrid)",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_EXPORT_POWER,
        register=SUNGROW_EXPORT_POWER,
        name="Current Export Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_EXPORT_POWER_HYBRID,
        register=SUNGROW_EXPORT_POWER_HYBRID,
        name="Current Export Power (Hybrid)",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_PV_ENERGY,
        register=SUNGROW_DAILY_PV_ENERGY,
        name="Daily PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_PV_ENERGY,
        register=SUNGROW_TOTAL_PV_ENERGY,
        name="Total PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_BATTERY_CHARGE_PV_ENERGY,
        register=SUNGROW_DAILY_BATTERY_CHARGE_PV_ENERGY,
        name="Daily Battery Charge PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_BATTERY_CHARGE_PV_ENERGY,
        register=SUNGROW_TOTAL_BATTERY_CHARGE_PV_ENERGY,
        name="Total Battery Charge PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_DIRECT_ENERGY_CONSUMPTION,
        register=SUNGROW_DAILY_DIRECT_ENERGY_CONSUMPTION,
        name="Daily Direct Energy Consumption",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_DIRECT_ENERGY_CONSUMPTION,
        register=SUNGROW_TOTAL_DIRECT_ENERGY_CONSUMPTION,
        name="Total Direct Energy Consumption",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_IMPORT_ENERGY,
        register=SUNGROW_DAILY_IMPORT_ENERGY,
        name="Daily Grid Import Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_IMPORT_ENERGY,
        register=SUNGROW_TOTAL_IMPORT_ENERGY,
        name="Total Grid Import Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_BATTERY_DISCHARGE_ENERGY,
        register=SUNGROW_DAILY_BATTERY_DISCHARGE_ENERGY,
        name="Daily Battery Discharge Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_BATTERY_DISCHARGE_ENERGY,
        register=SUNGROW_TOTAL_BATTERY_DISCHARGE_ENERGY,
        name="Total Battery Discharge Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_EXPORT_ENERGY_FROM_PV,
        register=SUNGROW_DAILY_EXPORT_ENERGY_FROM_PV,
        name="Daily Export Energy From PV",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_EXPORT_ENERGY_FROM_PV,
        register=SUNGROW_TOTAL_EXPORT_ENERGY_FROM_PV,
        name="Total Export Energy From PV",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_EXPORT_ENERGY_FROM_BATTERY,
        register=SUNGROW_DAILY_EXPORT_ENERGY_FROM_BATTERY,
        name="Daily Export Energy From Battery",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_EXPORT_ENERGY_FROM_BATTERY,
        register=SUNGROW_TOTAL_EXPORT_ENERGY_FROM_BATTERY,
        name="Total Export Energy From Battery",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_EXPORT_ENERGY,
        register=SUNGROW_DAILY_EXPORT_ENERGY,
        name="Daily Export Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_EXPORT_ENERGY,
        register=SUNGROW_TOTAL_EXPORT_ENERGY,
        name="Total Export Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_PV_EXPORT,
        register=SUNGROW_DAILY_PV_EXPORT,
        name="Daily PV Export",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_PV_EXPORT,
        register=SUNGROW_TOTAL_PV_EXPORT,
        name="Total Export Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_SELF_CONSUMPTION_OF_DAY,
        register=SUNGROW_SELF_CONSUMPTION_OF_DAY,
        name="Daily Self Consumption",
        native_unit_of_measurement=PERCENTAGE,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_DAILY_POWER_YIELDS,
        register=SUNGROW_DAILY_POWER_YIELDS,
        name="Daily Energy Yields",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_METER_POWER,
        register=SUNGROW_METER_POWER,
        name="Current Meter Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_TOTAL_ACTIVE_POWER,
        register=SUNGROW_TOTAL_ACTIVE_POWER,
        name="Current Active Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_POWER_EXPORT_TO_GRID,
        register=SUNGROW_POWER_EXPORT_TO_GRID,
        name="Current Power Exported to Grid",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SungrowInverterSensorEntityDescription(
        key=SUNGROW_POWER_IMPORT_FROM_GRID,
        register=SUNGROW_POWER_IMPORT_FROM_GRID,
        name="Current Power Imported from Grid",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
)


def data_updater(inverter: SungrowInverter):
    """Function called by DataUpdateCoordinator to do the data refresh from the inverter"""
    def u():
        logger.debug(f'async_update_data scrape inverter={inverter}')
        is_connected = inverter.connect()
        logger.debug(f'async_update_data is_connected={is_connected}')
        inverter.scrape()
        logger.debug(
            f'async_update_data latest_scrape={pformat(inverter.latest_scrape)}')
        if inverter.latest_scrape == {}:
            raise UpdateFailed(f"Failed scraping Sungrow Inverter")
        return inverter
    return u


# Called automagically by Home Assistant
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    # Get a unique id for the inverter device
    # unique_id is set during the initial configuration step
    if (unique_device_id := config_entry.unique_id) is None:
        unique_device_id = config_entry.entry_id

    """Setup sensors from a config entry created in the integrations UI."""
    # Configure SungrowInverter
    config_inverter = {
        # client config
        'host': config_entry.data[CONF_HOST],
        # one of: 502 for modbus, 8082 for http
        'port': config_entry.data.get(CONF_PORT, '8082'),
        'timeout': int(config_entry.data.get(CONF_TIMEOUT, 10)),
        'retries': 3,
        'slave': config_entry.data.get(CONF_SLAVE, DEFAULT_SLAVE),
        # inverter config
        # None to autodetect, string of model name otherwise
        'model': config_entry.data.get('model'),
        # Information request level
        # 0 = Model and Solar Generation,
        # 1 = Useful data, all required for exports,
        # 2 everything your Inverter supports,
        # 3 Everything from every register
        'level': config_entry.data.get('level', 2),
        # boolean
        'use_local_time': config_entry.data.get('use_local_time', False),
        'smart_meter': config_entry.data.get('smart_meter'),
        # one of: http, sungrow, modbus
        'connection': config_entry.data.get('connection', 'http')
    }

    # Async construct inverter object
    def create_inverter():
        pwd = pathlib.Path(__file__).parent.absolute()
        registersfile = yaml.safe_load(
            open(os.path.join(pwd, 'registers-sungrow.yaml'), encoding="utf-8"))
        inverter = SungrowInverter(config_inverter)
        if not inverter.checkConnection():
            logger.error(
                f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}")
        inverter.configure_registers(registersfile)
        if not inverter.inverter_config['connection'] == "http":
            inverter.close()
        return inverter
    inverter: SungrowInverter = await hass.async_add_executor_job(create_inverter)

    # Make sure we can connect to the inverter
    is_connected = inverter.connect()
    logger.debug(f'sensor async_setup_entry is_connected={is_connected}')

    # Configure DataUpdateCoordinator
    async def f():
        return await hass.async_add_executor_job(data_updater(inverter))
    coordinator = DataUpdateCoordinator(
        hass,
        logger,
        name=DOMAIN,
        update_method=f,
        update_interval=max(timedelta(seconds=config_entry.data.get(CONF_SCAN_INTERVAL, 60)),
                            MIN_TIME_BETWEEN_UPDATES),
    )

    # Fetch data (at least) once via DataUpdateCoordinator
    await coordinator.async_refresh()

    # Register our inverter device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        # connections={(dr.CONNECTION_NETWORK_MAC, config.mac)},
        identifiers={(DOMAIN, unique_device_id)},
        manufacturer="Sungrow",
        name=f'Sungrow {coordinator.data.getInverterModel()}',
        model=coordinator.data.getInverterModel()
    )

    # Register our sensor entities
    entity = []
    for description in SENSOR_TYPES:
        # Add in the owning device's unique id
        description.device_id = unique_device_id
        description.device_model = coordinator.data.getInverterModel()
        model_slug = description.device_model.replace('.', '')
        description.name = f'{model_slug} {unique_device_id} {description.name}'
        entity.append(SungrowInverterSensorEntity(coordinator, description))
    async_add_entities(entity, update_before_add=True)


class SungrowInverterSensorEntity(CoordinatorEntity, SensorEntity):
    """Implementation of a Sungrow Inverter sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, 
                 description: SungrowInverterSensorEntityDescription):
        """Initialize the sensor."""
        super().__init__(coordinator)
        # SensorEntity superclass will automatically pull sensor values from entity_description
        self.entity_description = description

    @property
    def unique_id(self) -> str:
        if self._attr_unique_id:
            return self._attr_unique_id
        else:
            self._attr_unique_id = f'sungrow_{self.entity_description.device_id}_{self.entity_description.key}'
            return self._attr_unique_id

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information about this IPP device."""
        if not self.entity_description.device_id:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, self.entity_description.device_id)},
            name = f'Sungrow {self.entity_description.device_model}',
            manufacturer = 'Sungrow',
            model = self.entity_description.device_model,
        )

    # SensorEntity methods

    @property
    def native_value(self):
        """Return the state of the sensor."""
        sensor_type = self.entity_description.key
        state = None
        try:
            if sensor_type == SUNGROW_ENERGY_GENERATION:
                state = self.coordinator.data.latest_scrape["total_dc_power"]
            elif sensor_type == SUNGROW_ARRAY1_ENERGY_GENERATION:
                state = (
                    self.coordinator.data.latest_scrape["mppt_1_voltage"]
                    * self.coordinator.data.latest_scrape["mppt_1_current"]
                )
            elif sensor_type == SUNGROW_ARRAY2_ENERGY_GENERATION:
                state = (
                    self.coordinator.data.latest_scrape["mppt_2_voltage"]
                    * self.coordinator.data.latest_scrape["mppt_2_current"]
                )
            else:
                state = self.coordinator.data.latest_scrape[sensor_type]
        except KeyError:
            logger.warn(
                "Sensor lookup value is not available in data array: %s", sensor_type)
        return state
