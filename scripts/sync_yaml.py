#!/usr/bin/env python3
"""Compare our signal definitions with those from mkaiser and bohdans."""

from pathlib import Path

import requests
import yaml
from beartype.claw import beartype_all
from tabulate import tabulate

if __package__ is None:
    # Script was executed from the command line
    import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core.modbus_py import RegisterType
from custom_components.sungrow.core.signals import (
    SignalDefinitions,
    SungrowSignalDefinition,
    get,
    load_yaml,
    type_or_none,
)

beartype_all()


def read_or_download(filename: Path, url):
    # ToDo check age of file and only download if older than 1 day
    if filename.exists():
        with open(filename) as file:
            return file.read()
    else:
        response = requests.get(url)

        if response.status_code == 200:
            with open(filename, "w") as file:
                file.write(response.text)
        else:
            raise RuntimeError(f"Failed to download the file: {response}")

    return response.text


def load_mkaiser() -> SignalDefinitions:
    content = read_or_download(
        Path(".mkaiser_modbus_sungrow.yaml"),
        "https://raw.githubusercontent.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/main/modbus_sungrow.yaml",
    )
    parsed = yaml.load(content, Loader=yaml.BaseLoader)

    signals = {}

    for entry in parsed["modbus"][0]["sensors"]:
        if "input_type" not in entry:
            print(f"{entry['name']}: no register_type")
            continue

        data_type = {"int16": "S16", "uint16": "U16", "int32": "S32", "uint32": "U32"}[
            entry["data_type"]
        ]
        register_type = {"holding": RegisterType.HOLD, "input": RegisterType.READ}[
            entry["input_type"]
        ]
        scale = type_or_none(float, entry.get("scale"))
        if scale and float(scale) == 1.0:
            scale = None

        signals[entry["unique_id"]] = SungrowSignalDefinition(
            name=f"{entry['name']} ({entry['unique_id']})",
            address=int(entry["address"]) + 1,
            register_type=register_type,
            base_datatype=data_type,
            unit_of_measurement=entry.get("unit_of_measurement", None),
            disabled=[],
            group=None,
            accuracy=scale,
            mask=None,
            decoded=None,
            models=None,
            models_exclude=None,
            level=None,
            array_length=1,
            element_length=0,  # will be set in post_init
        )

    return SignalDefinitions(signals)


def load_bohdans() -> SignalDefinitions:
    content = read_or_download(
        Path(".bohdans_modbus_sungrow.yaml"),
        "https://raw.githubusercontent.com/bohdan-s/SunGather/main/SunGather/registers-sungrow.yaml",
    )

    parsed = yaml.load(content, Loader=yaml.BaseLoader)

    signals = {}

    for entry in parsed["registers"][0]["read"]:
        signals[entry["name"]] = SungrowSignalDefinition(
            name=entry["name"],
            address=int(entry["address"]),
            base_datatype=entry["datatype"],
            register_type=RegisterType.READ,
            unit_of_measurement=entry.get("unit", None),
            disabled=[],
            group=None,
            accuracy=get(entry, float, "accuracy"),
            mask=get(entry, int, "mask"),
            decoded=None,  # todo
            models=entry.get("models", None),
            models_exclude=None,
            level=get(entry, int, "level"),
            element_length=1,
            array_length=0,  # will be set in post_init
        )

    # todo hold

    return SignalDefinitions(signals)


def compare_signal(other: SungrowSignalDefinition, ours: SungrowSignalDefinition):
    diff = []

    def attr(signal: SungrowSignalDefinition, attribute: str):
        value = getattr(signal, attribute)
        return value if value is not None else "(None)"

    def compare(attribute: str):
        if getattr(other, attribute) != getattr(ours, attribute):
            diff.append(
                [
                    other.name,
                    ours.name,
                    attribute,
                    attr(other, attribute),
                    attr(ours, attribute),
                ]
            )

    # Stuff that should match exactly:
    if ours.array_length == 1:
        compare("address")
    compare("pure_datatype")
    compare("unit_of_measurement")
    compare("accuracy")

    return diff


def remove_signals_with_a_mask(signals: list[SungrowSignalDefinition]):
    for signal in list(signals):
        if signal.mask:
            signals.remove(signal)


def compare_yamls(other_name: str, other: SignalDefinitions, ours: SignalDefinitions):
    diff = []

    for other_signal in other._definitions.values():
        our_signals = ours.get_signal_definitions_by_address_overlaps(
            other_signal.register_type, other_signal.address, 1
        )
        if not our_signals:
            diff.append([other_signal.name, "no match", "-", "-", "-"])
        elif len(our_signals) > 1:
            # Let's not report those with a mask for now, as it's simply SPAM.
            remove_signals_with_a_mask(our_signals)
            for s in our_signals:
                diff.append([other_signal.name, s.name, "multiple matches", "-", "-"])
            for s in our_signals:
                diff.extend(compare_signal(other_signal, s))
        else:
            our_signal = our_signals[0]
            diff.extend(compare_signal(other_signal, our_signal))

    if diff:
        print(
            tabulate(
                diff, headers=[other_name, "ours", "attribute", other_name, "ours"]
            )
        )


def main():
    mkaiser = load_mkaiser()
    bohdans = load_bohdans()
    ours = load_yaml()

    # Stuff that's in theirs, but not in ours:
    compare_yamls("mkaiser", mkaiser, ours)
    compare_yamls("bohdans", bohdans, ours)

    print("Note: some of the messages above are 'intented'. Have fun comparing!")
