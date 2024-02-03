"""This file contains the main SungrowInverter class."""

import logging
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatch
from typing import Final, cast

from custom_components.sungrow.core.inverter_types import Datapoint

from . import (
    deserialize,
    extra_sensors,
    modbus_base,
    modbus_http,
    modbus_py,
    signals,
)

logger = logging.getLogger(__name__)

DatapointValueType = signals.DatapointValueType


async def pull_single_signal(
    client: modbus_py.ModbusConnectionBase,
    signal: signals.SungrowSignalDefinition,
) -> DatapointValueType | None:
    """pull_raw_signals is more efficient than pull_raw_signal for multiple signals!!"""

    pull_start = datetime.now()

    raw = (await client.read([signal]))[signal.name]

    data = deserialize.decode_signal(signal, raw) if raw is not None else None

    elapsed = datetime.now() - pull_start

    logger.debug(
        "Inverter: Successfully pulled data in "
        f"{elapsed.seconds}.{elapsed.microseconds} secs"
    )

    return data


async def pull_signals(
    client: modbus_py.ModbusConnectionBase,
    signal_definitions: list[signals.SungrowSignalDefinition],
) -> dict[str, DatapointValueType | None]:
    """Pull data from inverter"""

    data: dict[str, DatapointValueType] = {}

    pull_start = datetime.now()

    # Downcast to base class to make mypy happy
    signal_definitions_base = cast(list[modbus_base.Signal], signal_definitions)

    # Load all registers from inverer
    data = deserialize.decode_signals(
        signal_definitions,
        await client.read(signal_definitions_base),
    )

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


def has_match(value: str, patterns: list[str]) -> bool:
    return any(fnmatch(value, pattern) for pattern in patterns)


def mark_signals_not_in_this_model_as_disabled(
    signal_definitions: list[signals.SungrowSignalDefinition], model: str
):
    for signal in signal_definitions:
        # Only certain models supported
        if signal.models and not has_match(model, signal.models):
            logger.debug(
                f"Signal {signal.name} with filter {signal.models} "
                f"is NOT available for model {model}"
            )
            signal.disabled.append("signal not available for this model")

        # Some models explicitly excluded
        if signal.models_exclude and has_match(model, signal.models_exclude):
            logger.debug(
                f"Signal {signal.name} with filter {signal.models_exclude} "
                f"is explicitly NOT available for model {model}"
            )
            signal.disabled.append("signal not available for this model")


@dataclass
class InitialConnection:
    connection: modbus_py.ModbusConnectionBase
    signal_definitions: signals.SignalDefinitions
    data: dict[str, DatapointValueType]

    _is_modbus_winet: bool | None = None

    async def __aenter__(self):
        await self.connection.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.connection.__aexit__(exc_type, exc_value, traceback)

    async def is_modbus_winet(self):
        """Lazy cached evaluation."""
        # TODO: move this to __init__ and remove the lazy evaluation

        if self._is_modbus_winet is None:
            # FIXME: are the same registers unsupported via pymodbus and http?
            if isinstance(self.connection, modbus_http.HttpConnection):
                self._is_modbus_winet = True
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

    async def disable_winet_signals_in_case_of_winet_dongle(self):
        if await self.is_modbus_winet():
            logger.debug("Disabling all WiNet unsupported signals")
            self.signal_definitions.disable_winet_signals()
        else:
            logger.debug("Not a WiNet dongle; all signals are supported")

    def disable_signals_not_supported_by_model(self):
        """Disable signals which are not supported by the inverter model."""

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
                self.signal_definitions.all_signals(), model
            )


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


async def try_slave(con: modbus_base.ModbusConnectionBase, slave: int, query):
    con._slave = slave
    try:
        data = await pull_signals(con, query)
    except modbus_base.InvalidSlaveError:
        return False
    else:
        return data


async def connect_and_get_basic_data(  # (TODO: redesign)
    host: str,
    port: int | None,
    slave: int | None,
    connection: str | None,
) -> InitialConnection | None:
    """
    Create a connection and retrieve some initial data to test the connection.
    This will return a connected or unconnected InitialConnection object.

    Will raise CannotConnectException when connection fails and generic ModbusError on
    other problems.
    This is to make error handling easier for the caller, otherwise we would have to
    check for not connected and for exceptions.
    """

    logger.debug(f"Connecting to {host}:{port} (slave {slave}) with {connection}")

    # TODO: try http first, then fall back to modbus
    # TODO: improve guess from port, if port is given
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
        slave_guessed = True
        logger.debug(f"Using default slave {slave}")
    else:
        slave_guessed = False

    signal_definitions = signals.load_yaml()

    # FIXME: meter_active_power readable? This determines if a meter is connected.
    # disable phase a, b, c accordingly.

    # TODO: maybe add all static signals to the query?
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
    if not await connection_obj.connect():
        # TCP error
        return None

    else:
        try:
            data = await try_slave(connection_obj, slave, query)
            if not data and slave_guessed:
                data = await try_slave(connection_obj, 2, query)
            if not data:
                await connection_obj.disconnect()
                return None
        except (modbus_base.InvalidSlaveError, modbus_base.ModbusError):
            logger.warning("Error connecting to inverter")
            await connection_obj.disconnect()
            return None

        logger.debug(
            "Connected to inverter "
            f"{data['device_type_code']} / {data['serial_number']}"
        )

        ic = InitialConnection(connection_obj, signal_definitions, data)
        ic.disable_signals_not_supported_by_model()
        await ic.disable_winet_signals_in_case_of_winet_dongle()
        return ic


class SungrowInverter:
    # FIXME: SungrowInverter:
    # * is it one connection to one inverter?
    # * is it one inverter with multiple connections? (http, WiNet, modbus-proxy, ...)

    @staticmethod
    async def create(ic: InitialConnection):
        if not ic.connection:
            raise RuntimeError("Not connected")

        # We now need to pull all data which belongs to a group,
        # so we can detect groups which do not apply, like "has_battery".
        query = [
            signal
            for signal in ic.signal_definitions._definitions.values()
            if signal.group and not signal.disabled and signal.name not in ic.data
        ]
        data = await pull_signals(ic.connection, query)
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

        new_data = await pull_signals(
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
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.disconnect()

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
