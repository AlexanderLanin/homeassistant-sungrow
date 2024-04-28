"""This file contains the main SungrowInverter class."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatch
from typing import cast

from custom_components.sungrow.core import connection, const
from custom_components.sungrow.core.inverter_types import Level, Sensor

from . import (
    deserialize,
    modbus_base,
    modbus_http,
    modbus_py,
    signals,
)

logger = logging.getLogger(__name__)

DatapointValueType = signals.DatapointValueType


def mark_unavailable_signals_as_disabled(
    all_signals: signals.SignalDefinitions,
    data: dict[str, DatapointValueType],
):
    """Mark signals not available within `data` as disabled in `all_signals`."""

    # mark signals as disabled if they are not supported by the inverter.
    # This currently doesn't happen without a more elaborate check, as a clear
    # not-supported value is only triggered when the signal is queried alone.
    for name, value in data.items():
        if value is None:
            signal = all_signals.get_signal_definition_by_name(name)
            assert signal  # as it's in data, it must be in all_signals
            signal.disabled.append(
                "Inverter does not support this signal (None returned)"
            )
            logger.debug(
                f"Disabling {name} as it's not supported by inverter (None returned)"
            )

    # mark_signals_disabled_based_on_groups must be called after unsupported signals
    # have been marked as disabled. It will check all remaining signals for 0 or not 0.
    # Therefore filtering by level must happen after this step.
    return all_signals.mark_signals_disabled_based_on_groups(data)


def mark_signals_not_in_this_model_as_disabled(
    signal_definitions: list[signals.SungrowSignalDefinition], model: str
):
    def has_match(value: str, patterns: list[str]) -> bool:
        return any(fnmatch(value, pattern) for pattern in patterns)

    for signal in signal_definitions:
        # Only certain models supported
        if signal.models and not has_match(model, signal.models):
            signal.disabled.append("signal not available for this model (not included)")

        # Some models explicitly excluded
        if signal.models_exclude and has_match(model, signal.models_exclude):
            signal.disabled.append("signal not available for this model (excluded)")


def _guess_connection_classes(
    connection: str | None, port: int | None
) -> list[type[modbus_base.ModbusConnectionBase]]:
    """Returns connection classes worth trying."""

    if connection == "http" or port == const.SUNGROW_DEFEAULT_HTTP_PORT:
        return [modbus_http.HttpConnection]

    if connection == "modbus" or port == const.SUNGROW_DEFEAULT_MODBUS_PORT:
        return [modbus_py.PymodbusConnection]

    elif connection is None and port is None:
        # TODO: which one do we prefer?
        return [modbus_py.PymodbusConnection, modbus_http.HttpConnection]

    else:
        # Non standard port can only mean modbus proxy
        return [modbus_py.PymodbusConnection]


class SungrowInverter:
    async def __aenter__(self):
        """Ensures the connection is established."""
        await self._client.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Ensures the connection is closed."""
        await self._client.disconnect()

    @staticmethod
    async def _establish_connection(ci: ConnectionParams):
        connection_classes = _guess_connection_classes(ci.connection, ci.port)
        for cc in connection_classes:
            port = ci.port or cc.default_port()
            modbus_obj = cc(ci.host, port)

            logger.debug(f"Trying to connect to {modbus_obj}...")
            if await modbus_obj.connect():
                connection_obj = connection.Connection(modbus_obj)
                is_http = isinstance(modbus_obj, modbus_http.HttpConnection)
                return SungrowInverter.ConnectionData(
                    cast(connection.ConnectionProto, connection_obj), is_http
                )
        logger.debug("Failed to connect to inverter")
        return None

    @dataclass
    class ConnectionParams:
        host: str
        port: int | None
        connection: str | None

    @dataclass
    class ConnectionData:
        """Mostly/only used for connection injection in tests."""

        connection: connection.ConnectionProto
        is_http: bool

    @staticmethod
    async def create(
        connection_param: ConnectionParams | ConnectionData,
        slave: int | None = None,
        level_of_detail: int = Level.ADVANCED.value,
    ) -> SungrowInverter | None:
        """Create a connection, with heuristics for port, slave and connection type."""

        if isinstance(connection_param, SungrowInverter.ConnectionData):
            connection_obj = connection_param
        else:
            temp = await SungrowInverter._establish_connection(connection_param)
            if temp is None:
                return None
            connection_obj = temp

        inv = SungrowInverter(connection_obj, direct_initialization=False)

        slaves_to_attempt = [1, 2] if slave is None else [slave]
        for slave in slaves_to_attempt:
            if await inv._set_slave_and_query_initial_data(slave):
                break
        else:
            logger.warning(
                "Failed to connect to inverter. Exotic slave ID? "
                "You'll have to enter it manually"
            )
            await inv.disconnect()
            return None

        assert inv.data, "Data should be available after initial query"

        if not inv.data["serial_number"] or not inv.data["device_type_code"]:
            logger.warning("Failed to connect to inverter. No serial number or model")
            await inv.disconnect()
            return None

        logger.debug(f"Initial data: {inv.data}")
        logger.debug(
            "Connected to inverter "
            f"{inv.data['device_type_code']} / {inv.data['serial_number']}"
        )

        await inv._disable_all_unsupported_signals(level_of_detail)

        return inv

    def __init__(
        self,
        connection_data: ConnectionData,
        signal_definitions: signals.SignalDefinitions | None = None,
        direct_initialization: bool = True,
    ):
        """Use create() factory method!!"""
        if direct_initialization:
            raise RuntimeError("Use create() factory method")

        self._client = connection_data.connection
        self._is_http = connection_data.is_http

        self.data: deserialize.DecodedSignals = {}
        """
        All data from the inverter.
        This is decoded data, and the same as in sensors.
        However, sensors does not contain data,
        which cannot be visualized in the UI (lists).
        """

        self.sensors: dict[str, Sensor] = {}
        """
        All data from the inverter.
        This is decoded data, and the same as in data.
        However, sensors does not contain data,
        which cannot be visualized in the UI (lists).
        """

        # TODO: why do we need this or? It's not used in production code!!!
        assert signal_definitions is None
        self._signal_definitions = signal_definitions or signals.load_yaml()

        # Remove disabled signals from data
        for signal in self._signal_definitions._definitions.values():
            if signal.disabled and signal.name in self.data:
                logger.warning(
                    "Disabling pre-acquired signal "
                    f"{signal.name} due to: {signal.disabled}"
                )
                self.data.pop(signal.name, None)

        self._is_modbus_winet: bool | None = None
        self._active_groups: dict[str, bool] | None = None

    async def _disable_all_unsupported_signals(self, level_of_detail: int):
        # Move to separate file, as it's quite a lot?!

        assert (
            self._signal_definitions
        ), "Must be loaded before this function is called."

        self._disable_signals_not_supported_by_model()

        await self._disable_all_meter_signals_if_no_meter_available()

        # TODO: are the same registers unsupported via pymodbus and http?
        if await self._determine_is_modbus_winet():
            logger.debug("WiNet dongle detected; Disabling all unsupported signals")
            self._signal_definitions.disable_winet_signals()

        # We now need to pull all data which belongs to a group,
        # so we can detect groups which do not apply, like "has_battery".
        query = [
            signal
            for signal in self._signal_definitions._definitions.values()
            if signal.group and not signal.disabled and signal.name not in self.data
        ]
        data = await self._client.read(query)
        if not data:
            raise RuntimeError("Failed to pull data from inverter")

        self._active_groups = mark_unavailable_signals_as_disabled(
            self._signal_definitions, data
        )

        self._signal_definitions.mark_signals_below_level_as_disabled(level_of_detail)

    async def pull_single_signal_by_name(
        self, signal_name: str
    ) -> DatapointValueType | None:
        return await self._client.read_single_signal(
            self._signal_definitions.get_signal_definition_by_name(signal_name)
        )

    async def pull_signals_by_name(
        self, signal_list: list[str]
    ) -> deserialize.DecodedSignals:
        return await self._client.read(
            self._signal_definitions.get_signal_definitions_by_name(signal_list),
        )

    async def _set_slave_and_query_initial_data(self, slave: int):
        """
        Query some initial data to test the connection.
        """

        self._client.slave = slave

        try:
            signal_list = self._signal_definitions.get_active_signals_for_level(
                Level.CONNECTION.value
            )
            self.data = await self._client.read(signal_list)
        except (modbus_base.InvalidSlaveError, modbus_base.ModbusError):
            self.data = {}
            logger.debug("Error connecting to inverter")
            return False
        else:
            return True

    @property
    def is_modbus_winet(self):
        assert (
            self._is_modbus_winet is not None
        ), "should have been determined by factory method"
        return self._is_modbus_winet

    async def _determine_is_modbus_winet(self):
        assert self._is_modbus_winet is None, "This should be called only once"

        if self._is_http:
            self._is_modbus_winet = True
        else:
            # array_insulation_resistance is not supported by WiNet dongle
            value = await self.pull_single_signal_by_name("array_insulation_resistance")

            if value is None:
                logger.debug(
                    "array_insulation_resistance is NOT supported -> WiNet dongle"
                )
                self._is_modbus_winet = True
            else:
                logger.debug(
                    "array_insulation_resistance is supported -> NOT WiNet dongle"
                )
                self._is_modbus_winet = False

        return self._is_modbus_winet

    def _disable_signals_not_supported_by_model(self):
        """Disable signals which are not supported by the inverter model."""

        assert "device_type_code" in self.data, "device_type_code must be available."
        assert (
            self._signal_definitions
        ), "Must be loaded before this function is called."

        if isinstance(self.data["device_type_code"], int):
            logger.info(
                f"Unknown inverter model detected: {self.data['device_type_code']}. "
                "Please report this to the developers."
            )
        else:
            model = self.data["device_type_code"]
            assert isinstance(model, str)
            # Now that we have the model, we can disable unsupported signals.
            # This is required, as querying a hundred unsupported signals, will result
            # in 100 queries (best case).
            mark_signals_not_in_this_model_as_disabled(
                self._signal_definitions.all_signals(), model
            )

    async def _disable_all_meter_signals_if_no_meter_available(self):
        # This is be a better distinction than simply disabling meter via a grooup,
        # because all signals are 0.
        # TODO: Introduce is_disabled / is_available flag?
        logger.debug("Checking if meter is connected...")
        if await self.pull_single_signal_by_name("meter_active_power") is None:
            for signal in self._signal_definitions.get_signal_definitions_by_name(
                [
                    "meter_active_power",
                    "meter_active_power_phase_a",
                    "meter_active_power_phase_b",
                    "meter_active_power_phase_c",
                ]
            ):
                signal.disabled.append("Meter not connected")
            logger.debug("Disabed all meter signals as meter is not connected")
        else:
            logger.debug("Meter is connected")

    async def disconnect(self):
        await self._client.disconnect()

    def update_sensors_from_raw_data(
        self,
        raw_data: dict[str, DatapointValueType],
    ):
        for k, v in raw_data.items():
            # Skip dicts, as we cannot visualize them in the UI anyway
            if isinstance(v, dict):
                assert k not in self.sensors, k
                continue

            definition = self._signal_definitions.get_signal_definition_by_name(k)
            assert definition, k

            if k in self.sensors:
                self.sensors[k].value = v
            else:
                logger.debug(f"Creating new sensor for {k}")
                self.sensors[k] = Sensor(k, v, definition.unit_of_measurement)

            # TODO: set unchanged sensors to None?!
            # TODO: set timestamp of last change? Could be different per sensor!

    def update_sensors_with_active_groups(self):
        assert self._active_groups is not None, "Must be set by factory method"

        for g in self._active_groups:
            if g in self.sensors:
                self.sensors[g].value = self._active_groups[g]
            else:
                logger.debug(
                    f"Creating new sensor for group {g} ({self._active_groups[g]})"
                )
                self.sensors[g] = Sensor(
                    name=g,
                    value=self._active_groups[g],
                    unit_of_measurement=None,
                )

    async def pull_data(self):
        assert self._active_groups is not None, "Must be set by factory method"

        logger.debug(
            "Pulling data from inverter: "
            + ",".join([s.name for s in self._signal_definitions.enabled_signals()])
        )
        new_data = await self._client.read(self._signal_definitions.enabled_signals())
        if new_data:
            self.update_sensors_from_raw_data(new_data)
            self.update_sensors_with_active_groups()  # one time activity?

            # FIXME
            # extra_signals = extra_sensors.calculate(new_data)

            return True
        else:
            await self.disconnect()
            return False

    @property
    def serial_number(self):
        return self.data["serial_number"]

    @property
    def model(self) -> str | int:
        model = self.data["device_type_code"]
        assert isinstance(model, str | int)
        return model

    def get_data_for_group(self, group: str):
        # Helpful function for debugging

        data = {}
        for signal in self._signal_definitions.get_signals_for_group(group):
            if signal in self.data:
                data[signal] = self.data[signal]
        return data

    class ConnectionMode(Enum):
        STANDALONE = "Standalone"
        MASTER = "Master"
        SLAVE = "Slave"
        SLAVE_1 = "Slave 1"
        SLAVE_2 = "Slave 2"
        SLAVE_3 = "Slave 3"
        SLAVE_4 = "Slave 4"
        ERROR = "Error"

        def __str__(self):
            return self.value

        def __repr__(self):
            return self.value

    @property
    def is_standalone(self):
        if master_slave_mode := self.data.get("master_slave_mode"):
            return master_slave_mode == "Disabled"
        else:
            return self.data["output_type"] == "2P"

    @property
    def slaves(self):
        if self.is_standalone:
            return 0
        else:
            return self.data.get("inverter_count")  # -1?

    @property
    def type(self):
        if self.is_standalone:
            return self.ConnectionMode.STANDALONE

        if master_slave_role := self.data.get("master_slave_role"):
            # Simplify "Slave 1" to "Slave" if only one slave
            if master_slave_role == "Slave 1" and self.slaves == 1:
                return self.ConnectionMode.SLAVE

            return self.ConnectionMode(master_slave_role)
        else:
            assert self._active_groups is not None, "Must be set by factory method"
            return (
                self.ConnectionMode.MASTER
                if self._active_groups.get("is_master")
                else self.ConnectionMode.SLAVE
            )

    def type_str(self):
        return str(self.type)

    @property
    def connection_mode(self):
        suffix = " WiNet" if self.is_modbus_winet else ""

        if self._is_http:
            return "http" + suffix
        else:
            return "modbus" + suffix
