"""This file contains the main SungrowInverter class."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from . import modbus, signals

logger = logging.getLogger(__name__)


# def are_all_values_zero(my_dict, keys):
#     """Return True if all values in the dictionary are zero or missing."""
#     return all(my_dict.get(key, 0) == 0 for key in keys)


# async def load_and_decode_single_signal(
#     connection: modbus.Connection, signal_definition: signals.ModbusSignalDefinition
# ):
#     """
#     Warning: this is highly inefficient,
#     as it loads only a single register from the inverter.
#     """

#     registers = await connection.read(
#         signal_definition.register_type,
#         signal_definition.address,
#         signal_definition.register_count,
#     )

#     value = None
#     if registers:
#         value = signals.decode_signal(
#             registers, signal_definition.address, signal_definition
#         )

#     logger.debug(f"Loaded {signal_definition}: {registers} => {value}")

#     return value


async def pull_raw_signals(
    client: modbus.Connection,
    register_ranges: list[signals.RegisterRange],
    signal_definitions: signals.SignalDefinitions,
) -> dict[str, str | int | float] | None:
    """Pull data from inverter. Return None on failure."""

    data: dict[str, str | int | float] = {}

    pull_start = datetime.now()

    # Load all registers from inverer
    try:
        for range in register_ranges:
            registers = await client.read(range.type, range.start, range.length)
            data.update(
                signals.decode_registers(
                    registers, range.type, signal_definitions, range.start
                )
            )

    except modbus.ModbusError as e:
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


def _mark_signals_not_in_this_model_as_disabled(all_signals, model):
    unknown_model = isinstance(model, int)
    if not unknown_model:
        for signal in all_signals._definitions.values():
            if (signal.models and model not in signal.models) or (
                signal.models_exclude and model in signal.models_exclude
            ):
                signal.disabled.append("signal not available for this model")


def _mark_signals_disabled_based_on_groups(all_signals, data):
    extra_data = {}

    # now filter groups where all signals are inactive
    for group, group_signals in all_signals.get_groups().items():
        all_zero = True
        for signal in group_signals.values():
            if data.get(signal.name) != 0:
                logger.debug(f"Group {group}: Signal {signal.name} is not zero")
                all_zero = False
                # break
        if all_zero:
            logger.debug(f"Group {group}: all signals are zero")
            for signal in group_signals.values():
                signal.disabled.append(f"all signals in {group} are zero")
            extra_data[group] = False
        else:
            extra_data[group] = True

    return extra_data


def mark_unavailable_signals_as_disabled(all_signals, data, model):
    _mark_signals_not_in_this_model_as_disabled(all_signals, model)
    return _mark_signals_disabled_based_on_groups(all_signals, data)


class SungrowInverter:
    @dataclass
    class Datapoint:
        name: str  # do we need the name here?
        value: str | int | float
        unit: str | None = None

        def __repr__(self) -> str:
            if self.unit:
                return f"{self.name} = {self.value} {self.unit}"
            else:
                return f"{self.name} = {self.value}"

    @staticmethod
    async def create(config: dict[str, Any]):
        """
        Create a SungrowInverter instance

        Will raise ModbusException on errors
        """

        if slave := config.get("unit"):
            # ToDo: The 'unit' config option is deprecated. Please use 'slave' instead.
            config["slave"] = slave

        async with modbus.Connection(
            host=config["host"],
            port=config["port"],
            slave=config["slave"],
        ) as connection:
            sungather_yaml = signals.load_sungather_yaml()

            data = await pull_raw_signals(
                connection, sungather_yaml.ranges, sungather_yaml.signals
            )
            if not data:
                logger.warning("Failed to pull any data from inverter")
                # return none or raise? FIXME TODO
                return None

            print(data)
            model = data.get("device_type_code", None)
            if not model:
                logger.warning(
                    "Failed to get device_type_code from inverter. "
                    "This is a temporary error. Retry later."
                )
                return None

            if isinstance(model, int):
                logger.info(
                    f"Unknown inverter type code detected: {model}. "
                    "Please report this to the developers."
                )
            else:
                # As defined in the yaml file, the model is a string.
                # (This is for mypy)
                assert isinstance(model, str)

            extra_data = mark_unavailable_signals_as_disabled(
                sungather_yaml.signals, data, model
            )

            return SungrowInverter(
                connection.detach(), sungather_yaml, model, extra_data, config
            )

    def __init__(
        self,
        client: modbus.Connection,
        sungather_yaml: signals.SunGatherYamlContent,
        model: int | str,
        extra_data: dict[str, str | int | float],
        config: dict[str, Any],
    ):
        """Note: you should use create_sungrow_inverter instead!"""

        self._client = client
        self._config: Final = config
        self._signals: Final = sungather_yaml.signals
        # Note: technically we can compute ranges, but this is far down the road.
        self._register_ranges: Final = sungather_yaml.ranges
        self.model: Final = model

        # ToDo: Let's get rid of levels...
        self._config["level"] = 2

        self.data: dict[str, SungrowInverter.Datapoint] = {}

        self._extra_data = extra_data

    async def disconnect(self):
        await self._client.disconnect()

    # async def _load_and_decode_single_signal(self, signal_name: str):
    #     return await load_and_decode_single_signal(
    #         self._client,
    #         self._signals.get_signal_definitions_by_name(signal_name),
    #     )

    async def pull_data(self, on_error=None):
        """Pull data from inverter and update self.data"""

        new_data = await pull_raw_signals(
            self._client, self._register_ranges, self._signals
        )
        if new_data:
            new_data = self.post_process_raw_data(new_data)
            assert new_data  # ToDo: what's going on?? mypy??
            new_data.update(self._extra_data)

            temp: dict[str, SungrowInverter.Datapoint] = {}
            for k, v in new_data.items():
                definition = self._signals.get_signal_definitions_by_name(k)
                unit = definition.unit if definition else None
                temp[k] = SungrowInverter.Datapoint(name=k, value=v, unit=unit)
            self.data = temp
            return self.data
        else:
            self.disconnect()

            if isinstance(on_error, Exception):
                raise on_error
            else:
                return on_error

    def post_process_raw_data(self, new_data: dict[str, str | int | float]):
        # --------- timestamps --------
        def convert_signals_to_timestamp(prefix: str = ""):
            try:
                # format: YYYY-MM-DD HH:MM:SS
                timestamp = "%04d-%02d-%02d %02d:%02d:%02d" % (
                    int(new_data[prefix + "year"]),
                    int(new_data[prefix + "month"]),
                    int(new_data[prefix + "day"]),
                    int(new_data[prefix + "hour"]),
                    int(new_data[prefix + "minute"]),
                    int(new_data[prefix + "second"]),
                )
            except KeyError:
                timestamp = None

            for key in ["year", "month", "day", "hour", "minute", "second"]:
                new_data.pop(prefix + key, None)

            return timestamp

        new_data["timestamp"] = convert_signals_to_timestamp()
        if self._config["use_local_time"]:
            new_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(f'Using Local Computer Time: {new_data.get("timestamp")}')
        else:
            logger.debug(f'Using Inverter Time: {new_data.get("timestamp")}')

        # If alarm state exists then convert to timestamp, otherwise remove it
        alarm_time = convert_signals_to_timestamp("alarm_time_")
        if new_data.get("pid_alarm_code"):
            new_data["alarm_timestamp"] = alarm_time

        # Add
        for i in range(1, 12):
            if f"mppt_{i}_current" in new_data or f"mppt_{i}_voltage" in new_data:
                current = float(new_data.get(f"mppt_{i}_current", 0))
                voltage = float(new_data.get(f"mppt_{i}_voltage", 0))
                new_data[f"mppt_{i}_power"] = current * voltage
        return new_data

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
