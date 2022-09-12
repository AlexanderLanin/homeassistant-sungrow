"""Integration platform for Sungrow Inverters"""

from __future__ import annotations

from datetime import datetime, timedelta
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

SENSOR_TYPES = (
    SensorEntityDescription(
        key=SUNGROW_ENERGY_GENERATION,
        name="Current PV Power Generation",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_ARRAY1_ENERGY_GENERATION,
        name="Current PV Array 1 Power Generation",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_ARRAY2_ENERGY_GENERATION,
        name="Current PV Array 2 Power Generation",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_OUTPUT_ENERGY,
        name="Daily Output Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_OUTPUT_ENERGY,
        name="Total Output Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_LOAD_POWER,
        name="Current Load Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_LOAD_POWER_HYBRID,
        name="Current Load Power (Hybrid)",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_EXPORT_POWER,
        name="Current Export Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_EXPORT_POWER_HYBRID,
        name="Current Export Power (Hybrid)",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_PV_ENERGY,
        name="Daily PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_PV_ENERGY,
        name="Total PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_BATTERY_CHARGE_PV_ENERGY,
        name="Daily Battery Charge PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_BATTERY_CHARGE_PV_ENERGY,
        name="Total Battery Charge PV Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_DIRECT_ENERGY_CONSUMPTION,
        name="Daily Direct Energy Consumption",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_DIRECT_ENERGY_CONSUMPTION,
        name="Total Direct Energy Consumption",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_IMPORT_ENERGY,
        name="Daily Grid Import Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_IMPORT_ENERGY,
        name="Total Grid Import Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_BATTERY_DISCHARGE_ENERGY,
        name="Daily Battery Discharge Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_BATTERY_DISCHARGE_ENERGY,
        name="Total Battery Discharge Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_EXPORT_ENERGY_FROM_PV,
        name="Daily Export Energy From PV",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_EXPORT_ENERGY_FROM_PV,
        name="Total Export Energy From PV",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_EXPORT_ENERGY_FROM_BATTERY,
        name="Daily Export Energy From Battery",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_EXPORT_ENERGY_FROM_BATTERY,
        name="Total Export Energy From Battery",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_EXPORT_ENERGY,
        name="Daily Export Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_EXPORT_ENERGY,
        name="Total Export Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_PV_EXPORT,
        name="Daily PV Export",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_PV_EXPORT,
        name="Total Export Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_SELF_CONSUMPTION_OF_DAY,
        name="Daily Self Consumption",
        native_unit_of_measurement=PERCENTAGE,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_DAILY_POWER_YIELDS,
        name="Daily Energy Yields",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=DEVICE_CLASS_ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key=SUNGROW_METER_POWER,
        name="Current Meter Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_TOTAL_ACTIVE_POWER,
        name="Current Active Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_POWER_EXPORT_TO_GRID,
        name="Current Power Exported to Grid",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=SUNGROW_POWER_IMPORT_FROM_GRID,
        name="Current Power Imported from Grid",
        native_unit_of_measurement=POWER_WATT,
        device_class=DEVICE_CLASS_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Resets every day
    # SensorEntityDescription(
    #     key=SUNGROW_DAILY_PV_EXPORT,
    #     name="Today Energy Export to Grid",
    #     native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    #     device_class=DEVICE_CLASS_ENERGY,
    #     state_class=SensorStateClass.MEASUREMENT,
    # ),
    # # Resets every day
    # SensorEntityDescription(
    #     key=SUNGROW_DAILY_IMPORT_ENERGY,
    #     name="Today Energy Import from Grid",
    #     native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    #     device_class=DEVICE_CLASS_ENERGY,
    #     state_class=SensorStateClass.MEASUREMENT,
    # ),
    # # Resets every day
    # SensorEntityDescription(
    #     key=SUNGROW_DAILY_PV_ENERGY,
    #     name="Today PV Generated Energy",
    #     native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    #     device_class=DEVICE_CLASS_ENERGY,
    #     state_class=SensorStateClass.MEASUREMENT,
    # ),
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
        'level': config_entry.data.get('level', 3),
        # boolean
        'use_local_time': config_entry.data.get('use_local_time', False),
        'smart_meter': config_entry.data.get('smart_meter'),
        # one of: http, sungrow, modbus
        'connection': config_entry.data.get('connection', 'http')
    }
    pwd = pathlib.Path(__file__).parent.absolute()
    registersfile = yaml.safe_load(
        open(os.path.join(pwd, 'registers-sungrow.yaml'), encoding="utf-8"))

    # Async construct inverter object
    def c():
        # return construct(config_inverter, registersfile)
        inverter = SungrowInverter(config_inverter)
        if not inverter.checkConnection():
            logger.error(
                f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}")
        inverter.configure_registers(registersfile)
        if not inverter.inverter_config['connection'] == "http":
            inverter.close()
        return inverter
    inverter: SungrowInverter = await hass.async_add_executor_job(c)

    is_connected = inverter.connect()
    logger.debug(f'sensor async_setup_entry is_connected={is_connected}')

    async def f():
        return await hass.async_add_executor_job(data_updater(inverter))

    # Configure DataUpdateCoordinator
    coordinator = DataUpdateCoordinator(
        hass,
        logger,
        name=DOMAIN,
        update_method=f,
        update_interval=max(timedelta(seconds=config_entry.data.get(CONF_SCAN_INTERVAL, 60)),
                            MIN_TIME_BETWEEN_UPDATES),
    )
    await coordinator.async_refresh()

    async_add_entities([
        SungrowInverterSensorEntity(
            coordinator, description)
        for description in SENSOR_TYPES
    ],
        update_before_add=True
    )


class SungrowInverterSensorEntity(CoordinatorEntity, SensorEntity):
    """Implementation of a Sungrow Inverter sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, description: SensorEntityDescription):
        """Initialize the sensor."""
        super().__init__(coordinator)

        # SensorEntity superclass will automatically pull sensor values from entity_description
        self.entity_description = description

        # Setting device_info causes HA to add a Device to the device registry
        self._attr_device_info: DeviceInfo = {
            'manufacturer': 'Sungrow',
            'model': coordinator.data.getInverterModel(),
            "identifiers": {
                # FIXME serial_number is not set until inverter.scrape() is called
                (DOMAIN, coordinator.data.latest_scrape.get('serial_number'))
            }
        }

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
            # elif self.entity_description.state_class == SensorStateClass.MEASUREMENT:
            else:
                state = self.coordinator.data.latest_scrape[sensor_type]
        except KeyError:
            logger.warn(
                "Sensor lookup value is not available in data array: %s", sensor_type)

        return state

    # @property
    # def last_reset(self) -> datetime | None:
    #     if self._attr_device_class == DEVICE_CLASS_ENERGY and self._attr_state_class == SensorStateClass.MEASUREMENT:
    #         # We reset last midnight
    #         return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    #     else:
    #         return None
