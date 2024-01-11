#!/usr/bin/env python3
import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core import inverter, modbus, signals


async def main():
    with open(".analysis.txt", "w") as f:
        f.write("Seach for ! to see problems.\n\n")
        await analyse("192.168.13.58", f)
        await analyse("192.168.13.74", f)


async def analyse(host: str, output) -> None:
    output.write(f"Analyzing {host}...\n")
    output.flush()

    is_winet = await inverter.is_WiNet(host)
    assert is_winet, "This script only works with WiNet dongles"

    signal_definitions = signals.load_yaml()

    async with modbus.Connection(host, port=502, slave=1) as connection:
        problematic = await connection.detect_signals_causing_problems(
            signal_definitions.enabled_modbus_signals()
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
