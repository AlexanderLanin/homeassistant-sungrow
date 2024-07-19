"""This file contains the main SungrowInverter class."""

from __future__ import annotations

import logging
from enum import Enum
from fnmatch import fnmatch

from result import Ok

from custom_components.sungrow.core import (
    connection_base,
    connection_factory,
    modbus_types,
)
from custom_components.sungrow.core.inverter_types import Level, Sensor

from . import signals

logger = logging.getLogger(__name__)

DatapointValueType = signals.DatapointValueType


def mark_signals_not_in_this_model_as_disabled(
    signal_definitions: list[signals.SignalDefinition], model: str
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


class SungrowInverter:
    async def __aenter__(self):
        """Ensures the connection is established."""
        await self._client.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Ensures the connection is closed."""
        await self._client.disconnect()

    @staticmethod
    async def create(
        connection: connection_base.Connection,
        slave: int | None = None,
        level_of_detail: Level = Level.ADVANCED,
    ) -> SungrowInverter | None:
        assert type(connection) != connection_base.Connection, "Cannot use base class"

        inv = SungrowInverter(connection, direct_initialization=False)

        slaves_to_attempt = [1, 2] if slave is None else [slave]
        logger.debug(f"Attempting slaves: {slaves_to_attempt}")
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

        # TODO: in case nothing of an entire group is requested, we should not query it
        if not await inv._disable_all_unsupported_signals(level_of_detail.value):
            logger.warning(
                "Connection lost while reading first few values from inverter"
            )
            logger.warning(
                "Do you have some other device that is querying the inverter?"
            )
            await inv.disconnect()
            return None

        inv._signal_definitions.mark_signals_below_level_as_disabled(level_of_detail)

        return inv

    def __init__(
        self,
        client: connection_base.Connection,
        signal_definitions: signals.SignalDefinitions | None = None,
        direct_initialization: bool = True,
    ):
        """Use create() factory method!!"""
        assert not direct_initialization, "Use create() factory method!"
        assert type(client) != connection_base.Connection, "Cannot use base class"
        print("client: ", client)

        assert client.connected

        self._client = client

        self.data: connection_base.DecodedSignals = {}
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

        # If we have a http connection, there is no reason to perform a check
        # (performance reasons only)
        # TODO: are the same registers unsupported via pymodbus and http?
        if self._client.is_http:
            self._signal_definitions.disable_group("not_supported_by_winet")

        # TODO: ignore groups where not a single member is requested.
        # Query all group indicators, to quickly determine which groups are supported
        query = list(self._signal_definitions.get_group_indiators().values())

        if res := await self.pull_data(query):  # noqa: SIM103
            # self._active_groups = (
            #     self._signal_definitions.mark_signals_disabled_based_on_groups(
            #         self.data
            #     )
            # )

            return True  # success
        else:
            return False  # error

    async def pull_single_signal_by_name(
        self, signal_name: str
    ) -> DatapointValueType | None:
        # Wrap and unwrap into a list, and call the other function
        res = await self.pull_signals_by_name([signal_name])
        return res[signal_name]

    async def pull_signals_by_name(
        self, signal_list: list[str]
    ) -> connection_base.DecodedSignals:
        """Note: this will simply return self.data for now!"""
        res = await self.pull_data(
            self._signal_definitions.get_signal_definitions_by_name(signal_list)
        )
        # ToDo: what about partial data?
        if res:
            return self.data
        else:
            return {}

    async def _set_slave_and_query_initial_data(self, slave: int):
        """
        Query some initial data to test the connection.
        """

        self._client.slave = slave

        signal_list = self._signal_definitions.get_active_signals_for_level(
            Level.MINIMAL.value
        )
        return await self.pull_data(signal_list)

    @property
    def is_modbus_winet(self):
        s = self._signal_definitions.get_group_indicator("not_supported_by_winet")
        assert s, "Invalid yaml (no indicator for 'not_supported_by_winet')"

        assert s.is_supported in (
            modbus_types.ModbusSignal.Supported.NO,
            modbus_types.ModbusSignal.Supported.YES,
            modbus_types.ModbusSignal.Supported.CONFIRMED_UNKNOWN,
        ), "must have been set by object construction"

        return s.is_supported == modbus_types.ModbusSignal.Supported.NO

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

    async def disconnect(self):
        await self._client.disconnect()

    def update_sensors_from_raw_data(
        self,
        raw_data: dict[str, DatapointValueType],
    ):
        for k, v in raw_data.items():
            # Skip dicts, as we cannot visualize them in the UI anyway
            if isinstance(v, list):
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

    async def pull_data(
        self, signal_list: list[signals.SignalDefinition] | None = None
    ):
        assert self._active_groups is not None, "Must be set by factory method"

        if signal_list is None:
            signal_list = self._signal_definitions.enabled_signals()

        logger.debug(
            "Pulling data from inverter: " + ",".join([s.name for s in signal_list])
        )
        new_data_result = await self._client.read(signal_list, self._signal_definitions)
        if isinstance(new_data_result, Ok):
            self.update_sensors_from_raw_data(new_data_result.ok_value)
            self.update_sensors_with_active_groups()  # one time activity?

            # FIXME
            # extra_signals = extra_sensors.calculate(new_data)

            self.data.update(new_data_result.ok_value)
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
        for signal in self._signal_definitions.get_group_member(group):
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
            logger.debug("Standalone inverter -> 0 slaves")
            return 0
        else:
            x = self.data.get("inverter_count", 0)
            assert isinstance(x, int)
            # inverter_count includes master
            slaves = int(x) - 1
            logger.debug(f"Detected {slaves} slaves")
            return slaves

    @property
    def type(self):
        logger.debug(f"Data: {self.data}")
        logger.debug(f"Active Groups: {self._active_groups}")

        if self.is_standalone:
            return self.ConnectionMode.STANDALONE

        if master_slave_role := self.data.get("master_slave_role"):
            logger.debug(f"Master Slave Role: {master_slave_role}")

            # Simplify "Slave 1" to "Slave" if only one slave
            if master_slave_role == "Slave 1" and self.slaves == 1:
                return self.ConnectionMode.SLAVE

            return self.ConnectionMode(master_slave_role)
        else:
            assert self._active_groups is not None, "Must be set by factory method"

            if self._active_groups.get("is_master"):
                return self.ConnectionMode.MASTER
            else:
                return self.ConnectionMode.SLAVE

    def type_str(self):
        return str(self.type)

    @property
    def readable_connection_mode(self):
        suffix = " WiNet" if self.is_modbus_winet else ""

        if self._client.is_http:
            return "http" + suffix
        else:
            return "modbus" + suffix
