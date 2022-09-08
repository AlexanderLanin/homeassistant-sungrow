import asyncio
import logging
import pathlib
from contextlib import asynccontextmanager, suppress

import pymodbus.datastore
import pymodbus.framer
import pymodbus.server
import pytest
import yaml

from custom_components.sungrow.core import inverter

TEST_DATA = pathlib.Path(__file__).parent / "test_data"

pytest_plugins = ("pytest_asyncio",)

pytestmark = [pytest.mark.asyncio, pytest.mark.enable_socket]


@asynccontextmanager
async def simulated_inverter(yaml_file):
    response_data = pymodbus.datastore.ModbusSlaveContext()

    pymodbus_stores = {
        "read": "i",
        "hold": "h",
    }

    if yaml_file:
        with open(yaml_file) as f:
            yaml_data = yaml.safe_load(f)
            for register_type, registers in yaml_data.items():
                store = response_data.store[pymodbus_stores[register_type]]
                for address, value in registers.items():
                    store.setValues(address, [value])

    context = pymodbus.datastore.ModbusServerContext(
        slaves={1: response_data}, single=False
    )
    server = pymodbus.server.ModbusTcpServer(context=context, address=("localhost", 0))

    # Run server in background task.
    server_task = asyncio.create_task(server.serve_forever())

    # Wait for server to actually start.
    while not server.transport:
        await asyncio.sleep(0.1)
    port = server.transport.sockets[0].getsockname()[1]  # type: ignore
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
