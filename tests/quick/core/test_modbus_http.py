from custom_components.sungrow.core import modbus_http


def call_parse_modbus_data(param: str):
    # Inverter adds a null byte to the end of the response, so we need to add it here.
    param += " 00" if param else "00"
    return modbus_http._parse_modbus_data({"param_value": param}, param.count(" ") // 2)


def test_modbus_http_parse_modbus_data():
    assert call_parse_modbus_data("") == []
    assert call_parse_modbus_data("00 42") == [0x0042]
    assert call_parse_modbus_data("42 00") == [0x4200]
    assert call_parse_modbus_data("11 22 33 44") == [0x1122, 0x3344]
