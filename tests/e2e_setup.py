import asyncio
import logging
import pathlib
from contextlib import asynccontextmanager, suppress

import pymodbus.datastore
import pymodbus.framer
import pymodbus.server
import pytest
import pytest_socket
import yaml

from custom_components.sungrow.core import inverter

TEST_DATA = pathlib.Path(__file__).parent / "test_data"

pytest_plugins = ("pytest_asyncio",)

pytestmark = [pytest.mark.asyncio, pytest.mark.enable_socket]
logger = logging.getLogger(__name__)


def real_socket():
    pytest_socket.enable_socket()
    yield
    pytest_socket.disable_socket()


def use_yaml_for_responses(
    response_data: pymodbus.datastore.ModbusSlaveContext,
    yaml_file: str | pathlib.Path | None,
):
    if not yaml_file:
        return

    pymodbus_stores = {
        "read": "i",
        "hold": "h",
    }

    if isinstance(yaml_file, str):
        yaml_file = TEST_DATA / yaml_file

    with open(yaml_file) as f:
        yaml_data = yaml.safe_load(f)
        # some old yaml recordings don't have the "registers" key
        if "registers" in yaml_data:
            yaml_data = yaml_data["registers"]
        for register_type, registers in yaml_data.items():
            store = response_data.store[pymodbus_stores[register_type]]
            for address, value in registers.items():
                store.setValues(address, [value])


@asynccontextmanager
async def simulated_inverter(yaml_file: str | pathlib.Path | None):
    """
    Simulate a Sungrow inverter by running a Modbus server with a response context
    based on the given yaml file.

    Note: this will enable sockets for the duration of the test case.
    """

    if yaml_file:
        response_data = pymodbus.datastore.ModbusSlaveContext()
        use_yaml_for_responses(response_data, yaml_file)

        context = pymodbus.datastore.ModbusServerContext(
            slaves={1: response_data}, single=False
        )
    else:
        # no response
        context = pymodbus.datastore.ModbusServerContext(single=False)

    server = pymodbus.server.ModbusTcpServer(context=context, address=("localhost", 0))

    # Block connect() to all hosts except localhost
    pytest_socket.socket_allow_hosts("localhost")
    # Restore sockets in general
    pytest_socket.enable_socket()

    # Run server in background task.
    server_task = asyncio.create_task(server.serve_forever())

    # Wait for server to actually start.
    for _attempt in range(20):
        if server.transport:
            break
        await asyncio.sleep(0.1)
    if not server.transport:
        raise Exception("Server failed to start.")
    if _attempt > 1:
        logger.warning(f"Server start took {_attempt/10} seconds.")
    port = server.transport.sockets[0].getsockname()[1]  # type: ignore
    logger.debug(f"Server started on port {port}")
    assert port

    try:
        yield port
    finally:
        await server.server_close()
        await server.serving
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task


@asynccontextmanager
async def sungrow_inverter_client(port, params):
    params.update({"host": "localhost", "port": port, "unit": 1})
    inv = await inverter.SungrowInverter.create(params)
    if not inv:
        raise Exception("Failed to start SungrowInverter.")
    async with inv:
        yield inv


@asynccontextmanager
async def e2e_setup(yaml_file, inverter_params):
    logging.getLogger("pymodbus").setLevel(logging.INFO)
    async with (
        simulated_inverter(TEST_DATA / yaml_file) as port,
        sungrow_inverter_client(port, inverter_params) as inv,
    ):
        yield inv
