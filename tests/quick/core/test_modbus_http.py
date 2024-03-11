import pytest

from custom_components.sungrow.core import modbus_base, modbus_http


def call_parse_modbus_data(param: str):
    # Inverter adds a null byte to the end of the response, so we need to add it here.
    param += " 00" if param else "00"
    return modbus_http._parse_modbus_data({"param_value": param}, param.count(" ") // 2)


def test_modbus_http_parse_modbus_data():
    assert call_parse_modbus_data("") == []
    assert call_parse_modbus_data("00 42") == [0x0042]
    assert call_parse_modbus_data("42 00") == [0x4200]
    assert call_parse_modbus_data("11 22 33 44") == [0x1122, 0x3344]


def test_modbus_http_parse_ws_response():
    # success
    assert modbus_http.HttpConnection._parse_ws_response(
        {
            "result_code": 1,
            "result_msg": "success",
            "result_data": {"my_key": "my_value"},
        }
    ) == {"my_key": "my_value"}

    # Error: result_msg is not "success"
    with pytest.raises(modbus_base.ModbusError):
        modbus_http.HttpConnection._parse_ws_response(
            {
                "result_code": 1,
                "result_msg": "error",
                "result_data": {"my_key": "my_value"},
            }
        )

    # Error: result_code is not 1
    with pytest.raises(modbus_base.ModbusError):
        modbus_http.HttpConnection._parse_ws_response(
            {
                "result_code": 0,
                "result_msg": "success",
                "result_data": {"my_key": "my_value"},
            }
        )

    # Error: result_data is not set
    with pytest.raises(modbus_base.ModbusError):
        modbus_http.HttpConnection._parse_ws_response(
            {
                "result_code": 1,
                "result_msg": "success",
                "result_data": None,
            }
        )

    # Error: wrong format
    with pytest.raises(modbus_base.ModbusError):
        modbus_http.HttpConnection._parse_ws_response({"key": "value"})
