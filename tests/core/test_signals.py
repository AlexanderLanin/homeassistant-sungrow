from custom_components.sungrow.core.signals import load_sungather_yaml


def test_parsing_yaml():
    sungather_data = load_sungather_yaml()

    assert len(sungather_data.signals._definitions) > 200
    assert (
        sungather_data.signals.get_signal_definitions_by_name(
            "device_type_code"
        ).address
        == 5000
    )

    assert len(sungather_data.ranges) > 10
    assert sungather_data.ranges[0].start == 4950
