#!/usr/bin/env python3
import asyncio
import contextlib
import logging

import fix_path  # type: ignore  # noqa: F401

# logging.basicConfig(level=logging.DEBUG)
import pymodbus

from custom_components.sungrow.core import inverter, modbus_base, modbus_py, signals

pymodbus.pymodbus_apply_logging_config("DEBUG")


async def main():
    with open(".analysis.txt", "w") as f:
        f.write("Seach for ! to see problems.\n\n")
        await analyse("192.168.13.58", f)
        # await analyse("192.168.13.74", f)


async def analyse(host: str, output) -> None:
    output.write(f"Analyzing {host}...\n")
    output.flush()

    is_winet = await inverter.is_WiNet(host)
    assert is_winet, "This script only works with WiNet dongles"

    signal_definitions = signals.load_yaml()

    signal1 = signal_definitions.get_signal_definition_by_name("total_apparent_power")
    signal2 = signal_definitions.get_signal_definition_by_name("mppt_1_voltage")

    async with modbus_py.PymodbusConnection(host, port=502, slave=1) as connection:
        with contextlib.suppress(modbus_base.ModbusError):
            r = await connection._read_range(
                signal2.register_type,
                signal2.address,
                signal2.length,
            )
            print(r)

        with contextlib.suppress(modbus_base.ModbusError):
            r = await connection._read_range(
                signal2.register_type,
                signal2.address,
                signal2.length,
            )
            print(r)

        with contextlib.suppress(modbus_base.ModbusError):
            r = await connection._read_range(
                signal1.register_type,
                signal1.address,
                signal1.length,
            )
            print(r)

        with contextlib.suppress(modbus_base.ModbusError):
            r = await connection._read_range(
                signal2.register_type,
                signal2.address,
                signal2.length,
            )
            print(r)

        return

        problematic = await connection.detect_signals_causing_problems(
            signal_definitions.all_modbus_signals()
        )

        for signal_name in problematic:
            signal = signal_definitions.get_signal_definition_by_name(signal_name)
            if signal.models_exclude and "WiNet" in signal.models_exclude:
                print(
                    f"sync - {signal_name}: ok "
                    "(disabled for WiNet + failure to retrieve)",
                    file=output,
                )
            else:
                print(f"sync - {signal_name}: unexpected problem!", file=output)

        for signal in signal_definitions._definitions.values():
            if (
                signal.models_exclude
                and "WiNet" in signal.models_exclude
                and signal_name not in problematic
            ):
                print(f"sync - {signal_name}: unexpected ok!", file=output)

    print("Done. See .analysis.txt for results.")


asyncio.run(main())
