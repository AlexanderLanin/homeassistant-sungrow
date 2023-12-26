#!/usr/bin/env python3

from unittest.mock import patch
from SunGather.inverter import SungrowInverter
import logging

logging.basicConfig(level=logging.DEBUG)


def inverter_with_data(data):
    with patch("SunGather.inverter.SungrowInverter.__init__", return_value=None):
        inverter = SungrowInverter()
    # Add any timestamp to data to make it valid:
    data.update({"timestamp": 1620650280})
    inverter.latest_scrape = data
    return inverter


def test_battery_detection():
    assert not inverter_with_data({}).has_battery()
    assert not inverter_with_data({"unrelated": 1}).has_battery()
    assert not inverter_with_data({"battery_capacity": 0}).has_battery()

    assert inverter_with_data({"battery_capacity": 1}).has_battery()


def test_slave_detection():
    # There is nothing here to contradict slave status:
    assert inverter_with_data({}).is_slave()
    assert inverter_with_data({"unrelated": 1}).is_slave()
    assert inverter_with_data({"battery_capacity": 0}).is_slave()
    assert inverter_with_data({"total_import_energy": 0}).is_slave()
    assert inverter_with_data({"total_export_energy": 0}).is_slave()

    # As soon as there is a battery or import/export it's not a slave:
    assert not inverter_with_data({"battery_capacity": 1}).is_slave()
    assert not inverter_with_data({"total_import_energy": 1}).is_slave()
    assert not inverter_with_data({"total_export_energy": 1}).is_slave()


# Doesn't quite work with pytest yet as homeassistant imports are not available under normal linux.
# (used by __init__.py)
# For now just run: custom_components/sungrow/test_*.py
if __name__ == "__main__":
    test_battery_detection()
    test_slave_detection()
