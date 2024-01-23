"""
A convinience wrapper for pymodbus.

The abstraction level is chosen at the lowest point which does not need to know how
signals are queried. This is where all signals are read() at once, so this class
can perform a clever optimization to reduce the number of queries.
"""

import asyncio
import contextlib
import logging
import sys

import pymodbus
import pymodbus.client
import pymodbus.exceptions
import pymodbus.pdu

import custom_components.sungrow.core.modbus_base as modbus_base
from custom_components.sungrow.core.modbus_base import (
    ModbusConnectionBase,
    RegisterType,
)

logger = logging.getLogger(__name__)

if pymodbus.__version__ <= "3.6.3":
    print("pymodbus had a bug in <= 3.6.3 which would lead to many reconnects.")
    print("As our inverters don't like that, this script requires > 3.6.3.")
    print("Please run 'pip install --upgrade -r requirements.txt' to upgrade.")
    sys.exit(1)


class PymodbusConnection(ModbusConnectionBase):
    """A pymodbus connection to a single slave."""

    def __init__(self, host: str, port: int, slave: int):
        super().__init__(host, port, slave)

        self._client = pymodbus.client.AsyncModbusTcpClient(
            host=host, port=port, timeout=2, retries=1, retry_on_empty=True
        )

    async def connect(self):
        if self._client.connected:
            return True
        else:
            logger.debug("Connecting to %s:%s", self._host, self._port)
            self._stats.connections += 1
            return await self._client.connect()

    async def disconnect(self):
        # The _client has a 'reconnect_task' which it will cancel and delete on close().
        # But we want to wait for it to actually finish before returning,
        # so we are cleaning up properly.
        # Specifically, pytest will complain about lingering tasks if we don't wait for
        # this task to finish.
        logger.debug("Disconnecting from %s:%s", self._host, self._port)
        reconnect_task = self._client.reconnect_task
        self._client.close()
        if reconnect_task:
            # Catch CancelledError, as this is expected.
            with contextlib.suppress(asyncio.CancelledError):
                await reconnect_task
        logger.debug("Disconnected from %s:%s", self._host, self._port)

    async def _read_range(  # noqa: C901 (Error handling here is complex, nothing we can do about it)
        self,
        register_type: RegisterType,
        address_start: int,
        address_count: int,
        recursion=False,
    ) -> list[int]:
        """
        Reads `address_count` registers of type `register_type` starting at
        `address_start`.
        Note: each register is 16 bits, so `address_count` is the number of registers,
        not bytes.
        """
        logger.debug(f"_read_range({register_type}, {address_start}, {address_count})")
        if not await self.connect():
            raise modbus_base.CannotConnectError(
                "Cannot connect to inverter for reading"
            )

        await asyncio.sleep(0.5)  # Server doesn't like it if we query too fast.

        try:
            func = {
                RegisterType.READ: self._client.read_input_registers,
                RegisterType.HOLD: self._client.read_holding_registers,
            }[register_type]
            # Note: sending address = protocol address - 1.
            # This is the only line in the module that needs to know about this detail!
            rr = await func(address_start - 1, count=address_count, slave=self._slave)  # type: ignore
        except pymodbus.ModbusException as e:
            # e.g. no response from device
            raise modbus_base.ModbusError(
                f"connection error (for {register_type}, "
                f"{address_start}-{address_start+address_count})"
            ) from e

        if rr.isError():
            if isinstance(rr, pymodbus.pdu.ExceptionResponse):
                if rr.exception_code == pymodbus.pdu.ModbusExceptions.GatewayNoResponse:
                    raise modbus_base.InvalidSlaveError(
                        f"Slave ID {self._slave} is invalid"
                    )
                elif rr.exception_code == pymodbus.pdu.ModbusExceptions.IllegalAddress:
                    if pymodbus.__version__ == "3.6.3":
                        # pymodbus bug, see https://github.com/pymodbus-dev/pymodbus/pull/1931
                        await self.disconnect()
                    # ToDo: consider returning None instead of raising an error
                    raise modbus_base.UnsupportedRegisterQueriedError(
                        f"Inverter does not support {address_start}-"
                        f"{address_start+address_count}: {rr}"
                    )
                elif rr.exception_code == pymodbus.pdu.ModbusExceptions.SlaveFailure:
                    # This may self-heal, so we don't raise an error on the first attempt.
                    if recursion:
                        raise modbus_base.ModbusError(
                            f"Slave failure on {register_type} "
                            f"{address_start}-{address_start+address_count}: {rr}"
                        )
                    else:
                        return await self._read_range(
                            register_type=register_type,
                            address_start=address_start,
                            address_count=address_count,
                            recursion=True,
                        )
                else:
                    raise modbus_base.ModbusError(f"Unknown exception response: {rr}")
            else:
                raise modbus_base.ModbusError(f"Unknown error response: {rr}")

        if len(rr.registers) != address_count:
            raise modbus_base.ModbusError(
                f"Mismatched number of registers "
                f"(requested {address_count}) and responded {len(rr.registers)})"
            )

        assert isinstance(rr.registers, list)
        return rr.registers
