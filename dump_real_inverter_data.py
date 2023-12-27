#!/usr/bin/env python3

import asyncio
import contextlib
import logging

import yaml

from custom_components.sungrow.core import modbus, signals

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.WARNING)


async def main():
    connection = modbus.Connection("192.168.13.80", 502, 2)
    await connection.connect()

    sungather_yaml = signals.load_sungather_yaml()

    dump_registers: dict[str, dict[int, int]] = {"read": {}, "hold": {}}
    dump_signals: dict[str, str | int | float] = {}

    for range in sungather_yaml.ranges:
        registers = await connection.read(range.type, range.start, range.length)
        if registers:
            for i, register in enumerate(registers):
                dump_registers[range.type][range.start + i] = register

            try:
                dump_signals.update(
                    signals.decode_registers(
                        registers, range.type, sungather_yaml.signals, range.start
                    )
                )
            except Exception as e:
                dump_signals[str(range)] = str(e)

    with contextlib.suppress(Exception | asyncio.exceptions.CancelledError):  # type: ignore
        await connection.disconnect()

    with open("dump.yaml", "w") as dump_file:
        yaml.dump(
            {
                "registers": dump_registers,
                "signals": dump_signals,
            },
            dump_file,
            default_flow_style=False,
            sort_keys=False,
        )


asyncio.run(main())
