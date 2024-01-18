import tests.core.fix_test_path as fix_test_path  # type: ignore  # noqa: F401
from custom_components.sungrow.core.modbus_py import RegisterType
from custom_components.sungrow.core.signals import load_yaml


def test_parsing_yaml():
    sungather_data = load_yaml()

    assert len(sungather_data._definitions) > 200

    dtc = sungather_data.get_signal_definition_by_name("device_type_code")
    assert dtc.address == 5000
    assert dtc.length == 1
    assert dtc.register_type == RegisterType.READ
