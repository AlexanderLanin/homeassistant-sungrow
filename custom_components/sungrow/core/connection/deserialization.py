"""
Provides deserialization of raw signals.
The deserialization is done based on the signal definition.

Provided functions:
* decode_signal: Converts a single raw signal to a decoded signal.
* decode_signals: Converts a list of raw signals to a list of decoded signals.
"""

from modbus_types import (
    MappedData,
)
from signal_def import (
    DatapointBaseValueType,
    DatapointValueType,
    SignalDefinition,
)

DecodedSignalValues = dict[SignalDefinition, DatapointValueType]


def __deserialize(registers: list[int], signal: SignalDefinition):
    # TODO: use signal.something instead of len. It's faster. Add an assert for length?
    if len(registers) == 1:
        int_value = registers[0]
        na = 0xFFFF
    elif len(registers) == 2:
        int_value = registers[0] + registers[1] << 16
        na = 0xFFFFFFFF
    else:
        raise RuntimeError("registers not in 1,2")

    if int_value == na:
        return None
    else:
        # Wrap around for signed values
        if signal.base_datatype == "S16" and int_value > 0x7FFF:
            int_value -= 0x10000
        elif signal.base_datatype == "S32" and int_value > 0x7FFFFFFF:
            int_value -= 0x100000000

        return int_value


def _deserialize_and_decode_int_signal(
    signal: SignalDefinition,
    registers: list[int],
) -> DatapointBaseValueType:
    """
    Error cases:
    * returns None when signal is N/A
    * returns original int when signal cannot be decoded
    TODO: consider using `result`
    """
    int_value = __deserialize(registers, signal)
    if int_value is None:
        return None

    if signal.bitmask:
        # They cannot be combined, as currently only bool signals use bitmask.
        assert not signal.scale
        assert not signal.decoding_table
        return bool(int_value & signal.bitmask)

    elif signal.scale:
        assert not signal.decoding_table
        return int_value * signal.scale

    # "decoded" is used to decode values like "1" to "ON" or "0" to "OFF"
    elif signal.decoding_table:
        # ToDo: better error handling.
        # Exception is not an option, as it would be nice to e.g. support
        # unknown inverters.
        if value := signal.decoding_table.get(int_value, None):
            return value

        return int_value

    else:
        return int_value


def _decode_utf8_signal(raw: list[int]) -> str:
    return "".join([chr(c >> 8) + chr(c & 0xFF) for c in raw]).strip("\x00")


def decode_signal(
    signal: SignalDefinition,
    raw_value: list[int],
) -> DatapointValueType:
    assert signal.array_length

    if signal.base_datatype == "UTF-8":
        # raw_value is a list of registers (ints)
        return _decode_utf8_signal(raw_value)
    elif signal.array_length == 1:
        return _deserialize_and_decode_int_signal(signal, raw_value)
    else:
        data: list[DatapointBaseValueType] = [
            _deserialize_and_decode_int_signal(
                signal,
                raw_value[i : i + signal.element_length],
            )
            for i in range(0, signal.registers.length, signal.element_length)
        ]
        return data


def decode_signals(
    signal_list: list[SignalDefinition],
    raw_signals: MappedData,
) -> DecodedSignalValues:
    decoded: DecodedSignalValues = {}
    for signal in signal_list:
        value = raw_signals[signal.name]
        decoded[signal] = decode_signal(signal, value) if value else None
    return decoded
