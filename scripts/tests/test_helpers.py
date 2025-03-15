import pytest

from custom_components.sungrow.core.inverter import SungrowInverter
from scripts.common import helpers

parse = helpers.parse_fully_qualified_host_param


def test_parse_fully_qualified_host_param():
    assert parse("example.com") == parsed(None, "example.com")
    assert parse("http://example.com") == parsed("http", "example.com")
    assert parse("http://example.com:80") == parsed("http", "example.com", 80)
    assert parse("http://example.com:80/2") == parsed("http", "example.com", 80, 2)
    assert parse("modbus://example.com") == parsed("modbus", "example.com")
    assert parse("modbus://example.com:502") == parsed("modbus", "example.com", 502)
    assert parse("modbus://127.0.0.1:502/2") == parsed("modbus", "127.0.0.1", 502, 2)

    assert parse_error("http://example.com:80/")  # trailing slash
    assert parse_error("http://example.com:80/2/")  # trailing slash
    assert parse_error("http://example.com:80/2/3")  # two slave ids
    assert parse_error("http://example.com:80:80")  # two ports


# -- test helper functions --


def parsed(connection=None, host=None, port=None, slave_id=None):
    # Validate the parameters to avoid mistakes based on the function signature
    assert connection in (None, "http", "modbus")
    assert host is not None
    assert port is None or isinstance(port, int)
    assert slave_id is None or isinstance(slave_id, int)

    params = SungrowInverter.ConnectionParams(
        connection=connection, host=host, port=port
    )
    return (params, slave_id)


def parse_error(param):
    with pytest.raises(ValueError):  # noqa: PT011
        parse(param)
    return True
