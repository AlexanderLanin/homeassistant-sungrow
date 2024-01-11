#!/usr/bin/env python3

"""
This script will query an inverter via:
* modbus
* WiNet modbus
* via WiNet http
and compare the results.
"""

import asyncio
import copy

import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core import deserialize, http, inverter, modbus, signals

# Move to parameters? To .env?
m = True
if m:
    direct_ip = "192.168.13.79"  # master
    direct_slave = 1
    winet_ip = "192.168.13.58"  # master
else:
    # Move to parameters? To .env?
    direct_ip = "192.168.13.80"  # slave
    direct_slave = 2
    winet_ip = "192.168.13.74"  # slave


async def collect_data_via_direct_modbus(
    signal_definitions: signals.SignalDefinitions, host: str
):
    if await inverter.is_WiNet(host):
        print(f"{host} is a WiNet dongle, please fix ip")
        return None

    async with modbus.Connection(host, port=502, slave=direct_slave) as connection:
        signal_raw_data = await connection.read(signal_definitions.all_modbus_signals())

    values = deserialize.decode_signals(signal_definitions, signal_raw_data)

    return values


async def collect_data_via_winet_modbus(
    signal_definitions: signals.SignalDefinitions, host: str
):
    if not await inverter.is_WiNet(host):
        print(f"{host} is not a WiNet dongle, please fix ip")
        return None

    async with modbus.Connection(host, port=502, slave=direct_slave) as connection:
        signal_raw_data = await connection.read(
            signal_definitions.enabled_modbus_signals()
        )

    values = deserialize.decode_signals(signal_definitions, signal_raw_data)

    return values


async def collect_data_via_winet_http(
    signal_definitions: signals.SignalDefinitions, host: str
):
    if not await inverter.is_WiNet(host):
        print(f"{host} is not a WiNet dongle, please fix ip")
        return None

    async with http.Connection(host) as connection:
        signal_raw_data = await connection.read(signal_definitions.all_modbus_signals())

    values = deserialize.decode_signals(signal_definitions, signal_raw_data)

    return values


async def main():
    print(
        "Warning: this script assumes that you have run "
        "scripts/sync_unsupported_winet_registers!"
    )
    signal_definitions = signals.load_yaml()

    # Small hack: only winet modbus will use the disabled flag.
    signal_definitions.disable_winet_signals()

    print("Collecting data via direct modbus connection...")
    direct_modbus_data = await collect_data_via_direct_modbus(
        signal_definitions, direct_ip
    )
    print(f"Got {len(direct_modbus_data)} signals")

    print("Collecting data via WiNet modbus connection...")
    winet_modbus_data = await collect_data_via_winet_modbus(
        signal_definitions, winet_ip
    )
    print(f"Got {len(winet_modbus_data)} signals")

    print("Collecting data via WiNet http connection...")
    winet_http_data = await collect_data_via_winet_http(signal_definitions, winet_ip)
    print(f"Got {len(winet_http_data)} signals")

    # print the results as markdown table
    print("| Signal | Direct | WiNet HTTP | WiNet Modbus |")
    print("| ------ | ------ | ---------- | ------------ |")
    for signal in signal_definitions._definitions.values():
        direct_modbus = direct_modbus_data[signal.name]
        winet_http = winet_http_data[signal.name]
        winet_modbus = "disabled" if signal.disabled else winet_modbus_data[signal.name]

        if direct_modbus == winet_http == winet_modbus:
            name = signal.name
        else:
            name = f"**{signal.name}**"

        print(f"| {name} | {direct_modbus} | {winet_http} | {winet_modbus} |")


asyncio.run(main())
