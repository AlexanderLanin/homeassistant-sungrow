import re

from result import Err, Ok, Result

from custom_components.sungrow.core import connection_factory


def add_host_param(parser):
    parser.add_argument(
        "host",
        metavar="host",
        type=str,
        help="Host to query. "
        "Optionally with protocol, prefixed with 'http://' or 'modbus://'. "
        "Optionally with port, separated by a colon. "
        "Optionally with slave id, separated by a slash. "
        "Example for slave 2 on port 160 and http: http://192.168.13.80:160/2",
    )


def parse_fully_qualified_host_param(
    param,
) -> Result[tuple[connection_factory.ConnectionParams, int | None], str]:
    # Regex pattern to match the fully qualified host parameter
    pattern = r"^(?:(http|modbus)://)?([^:/]+)(?::(\d+))?(?:/(\d+))?$"

    match = re.match(pattern, param)
    if match:
        protocol, host, port, slave_id = match.groups()
        port = int(port) if port else None
        slave_id = int(slave_id) if slave_id else None

        # Create a ConnectionParams object with the parsed values
        connection_params = connection_factory.ConnectionParams(
            connection=protocol, host=host, port=port
        )

        return Ok((connection_params, slave_id))
    else:
        return Err("Invalid host parameter format")
