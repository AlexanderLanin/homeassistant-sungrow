"""This file contains the main SungrowInverter class."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final, cast

from custom_components.sungrow.core.inverter_types import Datapoint

from . import deserialize, extra_sensors, modbus_base, modbus_http, modbus_py, signals

logger = logging.getLogger(__name__)

DatapointValueType = signals.DatapointValueType


async def pull_raw_signals(
    client: modbus_py.ModbusConnectionBase,
    signal_definitions: list[signals.SungrowSignalDefinition],
) -> dict[str, DatapointValueType] | None:
    """Pull data from inverter. Return None on failure."""

    data: dict[str, DatapointValueType] = {}

    pull_start = datetime.now()

    # Downcast to base class to make mypy happy
    signal_definitions_base = cast(list[modbus_base.Signal], signal_definitions)

    # Load all registers from inverer
    try:
        data = deserialize.decode_signals(
            signal_definitions,
            await client.read(signal_definitions_base),
        )

    except modbus_base.ModbusError as e:
        logger.info(f"Pulling data from inverter failed: {e}")
        # return none or throw exception?
        return None

    elapsed = datetime.now() - pull_start
    # data["pull_time"] = f"{elapsed.seconds}.{elapsed.microseconds}"
    logger.debug(
        "Inverter: Successfully pulled data in "
        f"{elapsed.seconds}.{elapsed.microseconds} secs"
    )

    return data


def mark_unavailable_signals_as_disabled(
    all_signals: signals.SignalDefinitions,
    data: dict[str, DatapointValueType],
):
    # mark signals as disabled if they are not supported by the inverter
    for name, value in data.items():
        if value is None:
            all_signals.get_signal_definition_by_name(name).disabled.append(
                "Inverter does not support this signal (None returned)"
            )
            logger.debug(
                f"Disabling {name} as it's not supported by inverter (None returned)"
            )

    # mark_signals_disabled_based_on_groups must be called after unsupported signals
    # have been marked as disabled. It will check all remaining signals for 0 or not 0.
    # Therefore filtering by level must happen after this step.
    extra_data = all_signals.mark_signals_disabled_based_on_groups(data)

    return extra_data


@dataclass
class InitialConnection:
    connection: modbus_py.ModbusConnectionBase | None
    signal_definitions: signals.SignalDefinitions
    data: dict[str, DatapointValueType]

    _is_modbus_winet: bool | None = None
    _is_context_managed = 0

    async def __aenter__(self):
        self._is_context_managed += 1
        if self.connection:
            await self.connection.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._is_context_managed -= 1

        # TODO: in case we need nested context managing, remove this assert and
        # consider implications.
        assert self._is_context_managed == 0

        if self.connection:
            await self.connection.__aexit__(exc_type, exc_value, traceback)

    @property
    def is_context_managed(self):
        return self._is_context_managed > 0

    async def is_modbus_winet(self):
        """Lazy cached evaluation."""
        if not self.connection:
            raise RuntimeError("Not connected")

        if self._is_modbus_winet is None:
            if isinstance(self.connection, modbus_http.HttpConnection):
                self._is_modbus_winet = False
            else:
                # array_insulation_resistance is not supported by WiNet dongle
                signal = self.signal_definitions.get_signal_definition_by_name(
                    "array_insulation_resistance"
                )
                assert signal

                value = await self.connection.read([signal])

                if value["array_insulation_resistance"] is None:
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


def convert_raw_data_to_datapoints(
    raw_data: dict[str, DatapointValueType],
    signal_list: signals.SignalDefinitions,
):
    data: dict[str, Datapoint] = {}

    for k, v in raw_data.items():
        definition = signal_list.get_signal_definition_by_name(k)
        assert definition, k

        data[k] = Datapoint(k, v, definition.unit_of_measurement)

    return data


async def connect_and_get_basic_data(  # noqa: C901 (TODO: redesign)
    host: str,
    port: int | None,
    slave: int | None,
    connection: str | None,
) -> InitialConnection:
    """
    Create a connection and retrieve some initial data to test the connection.

    Will raise ModbusException on errors
    """

    # TODO: try http first, then fall back to modbus
    connection_class: type[modbus_base.ModbusConnectionBase]
    if connection is None:
        connection_class = modbus_http.HttpConnection
        logger.debug("Using default connection HTTP")
    if connection == "http":
        connection_class = modbus_http.HttpConnection
    else:
        connection_class = modbus_py.PymodbusConnection

    # Try default modbus port
    if port is None:
        port = 8082 if connection_class is modbus_http.HttpConnection else 502
        logger.debug(f"Using default port {port}")

    if slave is None or slave == 0:
        # TODO actually detect slave.
        # e.g. try 1-3 and see if we get a response.
        slave = 1
        logger.debug(f"Using default slave {slave}")

    signal_definitions = signals.load_yaml()

    query = signal_definitions.get_signal_definitions_by_name(
        [
            # basic infos:
            "serial_number",  # 4950
            "device_type_code",  # 5000
            # for correct naming of master/slave:
            "master_slave_mode",  # 33500
            "master_slave_role",  # 33501
            "output_type",  # 5002
        ]
    )

    connection_obj = connection_class(host=host, port=port, slave=slave)
    if not connection_obj.connect():
        # Don't even return the connection object, as it's not connected.
        # This should reduce consequent bugs of handling an unconnected object.
        return InitialConnection(None, signal_definitions, {})

    try:
        data = await pull_raw_signals(connection_obj, query)
        if not data:
            # TODO does this happen when the connected to a non modbus port?
            raise modbus_base.CannotConnectError("Failed to pull data from inverter")

        ic = InitialConnection(connection_obj, signal_definitions, data)

        logger.debug(
            "Connected to inverter "
            f"{data['device_type_code']} / {data['serial_number']}"
        )
        logger.debug(f"Data: {data}")

        if isinstance(data["device_type_code"], int):
            logger.info(
                f"Unknown inverter type code detected: {data['device_type_code']}. "
                "Please report this to the developers."
            )
        else:
            # Now that we have the model, we can disable unsupported signals.
            # This is required, as querying a hundred unsupported signals, will result
            # in 100 queries (best case).
            signal_definitions.mark_signals_not_in_this_model_as_disabled(
                data["device_type_code"]
            )

        if await ic.is_modbus_winet():
            logger.debug("Disabling all WiNet unsupported signals")
            ic.signal_definitions.disable_winet_signals()
        else:
            logger.debug("Not a WiNet dongle; all signals are supported")

        return ic
    except Exception:
        await connection_obj.disconnect()
        raise


class SungrowInverter:
    # FIXME: SungrowInverter:
    # * is it one connection to one inverter?
    # * is it one inverter with multiple connections? (http, WiNet, modbus-proxy, ...)

    @staticmethod
    async def create(ic: InitialConnection):
        # TODO: move all of this to __init__!!

        # We now need to pull all data which belongs to a group,
        # so we can detect groups which do not apply, like "has_battery".
        query = [
            signal
            for signal in ic.signal_definitions._definitions.values()
            if signal.group and not signal.disabled and signal.name not in ic.data
        ]
        data = await pull_raw_signals(ic.connection, query)
        if not data:
            raise RuntimeError("Failed to pull data from inverter")

        extra_data = mark_unavailable_signals_as_disabled(ic.signal_definitions, data)

        # TODO config.get("level", 1)
        ic.signal_definitions.mark_signals_below_level_as_disabled(1)

        for signal in ic.signal_definitions._definitions.values():
            if signal.disabled:
                data.pop(signal.name, None)

        # Let's keep both
        data.update(ic.data)

        my_config = SungrowInverter.Config(
            initial_data=data,
            active_groups=extra_data,
            signals=ic.signal_definitions,
        )

        return SungrowInverter(ic.connection, my_config)

    @dataclass
    class Config:
        initial_data: dict[str, DatapointValueType]
        active_groups: dict[str, bool]
        signals: signals.SignalDefinitions

    def __init__(
        self,
        client: modbus_base.ModbusConnectionBase,
        config: Config,
    ):
        """Note: you should use create() instead!"""

        logger.debug(f"Creating SungrowInverter({config})")

        self._client = client
        self._config: Final = config

        self.data: dict[str, Datapoint] = {}

    async def disconnect(self):
        await self._client.disconnect()

    async def pull_data(self, on_error=None):
        """Pull data from inverter and update self.data"""
        # ToDo: drop on_error

        new_data = await pull_raw_signals(
            self._client, self._config.signals.enabled_signals()
        )
        if new_data:
            temp = convert_raw_data_to_datapoints(new_data, self._config.signals)

            for g in self._config.active_groups:
                temp[g] = Datapoint(
                    name=g,
                    value=self._config.active_groups[g],
                    unit_of_measurement=None,
                )

            extra_signals = extra_sensors.calculate(new_data)
            temp.update(extra_signals)

            self.data = temp
            return self.data
        else:
            self.data = {}
            self.disconnect()

            if isinstance(on_error, Exception):
                raise on_error
            else:
                return on_error

    async def __aenter__(self):
        self._detached = False
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if not self._detached:
            await self.disconnect()

    def detach(self):
        """Detach from the context manager."""
        self._detached = True
        return self

    @property
    def serial_number(self):
        return self._config.initial_data["serial_number"]

    @property
    def model(self) -> str | int:
        model = self._config.initial_data["device_type_code"]
        assert isinstance(model, str | int)
        return model

    def get_data_for_group(self, group: str):
        # Helpful function for debugging

        data = {}
        for signal in self._config.signals.get_signals_for_group(group):
            if signal in self.data:
                data[signal] = self.data[signal]
        return data

    @property
    def slave_master_standalone(self):
        """
        Simple heuristic to determine if this is a master or slave inverter.
        """

        return slave_master_standalone_str(
            self._config.initial_data, self._config.active_groups
        )


def slave_master_standalone_str(initial_data, active_groups=None):
    if initial_data.get("master_slave_mode") == "Disabled":
        return "Standalone"
    elif initial_data.get("master_slave_mode") == "Enabled":
        if initial_data.get("master_slave_role") == "Master":
            return "Master"
        else:
            # ToDo: mulitple slaves
            return "Slave"
    elif active_groups is not None:
        # Data not available. Fall back to heuristic.
        # TODO This should somehow be reported back with a registers dump...
        if active_groups.get("is_master"):
            if initial_data.get("output_type", "2P") == "2P":
                return "Standalone"
            else:
                return "Master"
        else:
            return "Slave"
    else:
        return initial_data["serial_number"]
