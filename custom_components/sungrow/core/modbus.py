"""
A more convinien wrapper for pymodbus.
Lowest level of communication.
Does not know home assistant.
Does not know about Sungrow or inverters.
"""

import asyncio
import contextlib
import logging
from enum import StrEnum

import pymodbus
import pymodbus.client
import pymodbus.exceptions
import pymodbus.pdu

logger = logging.getLogger(__name__)


class RegisterType(StrEnum):
    READ = "read"
    HOLD = "hold"


class ModbusError(Exception):
    pass


class InvalidSlaveError(ModbusError):
    """
    This almost never happens, but it's good to know when it does.
    Usually invalid slave = no response from device.
    """

    pass


class CannotConnectError(ModbusError):
    pass


class Connection:
    """
    Low level wrapper around pymodbus.
    Unrelated to home assistant, sungrow or solar.

    Main difference: this will assume there is only one valid 'unit' per connection.
    """

    def __init__(self, host: str, port: int, slave: int):
        self._slave = slave
        self._client = pymodbus.client.AsyncModbusTcpClient(
            host=host, port=port, timeout=2, retries=1, retry_on_empty=True
        )
        self._detached = False

    async def __aenter__(self):
        if not await self.connect():
            raise CannotConnectError()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if not self._detached:
            await self.disconnect()

    def detach(self):
        """Detach from the context manager."""
        self._detached = True
        return self

    async def connect(self):
        if self._client.connected:
            return True
        else:
            return await self._client.connect()

    async def disconnect(self):
        print("modbus disconnecting...")
        print(f"reconnect task: {self._client.reconnect_task}")

        # The client has a 'reconnect_task' which it will cancel and delete on close().
        # But we wait to wait for it to actually finish, so we are cleaning up properly.
        # Specifically, pytest will complain about lingering tasks if we don't wait for
        # this task to finish.
        reconnect_task = self._client.reconnect_task
        self._client.close()
        if reconnect_task:
            with contextlib.suppress(asyncio.CancelledError):
                await reconnect_task

    async def read(
        self,
        register_type: RegisterType,
        start: int,
        count: int,
    ) -> list[int]:
        if not await self.connect():
            raise CannotConnectError()

        try:
            func = {
                RegisterType.READ: self._client.read_input_registers,
                RegisterType.HOLD: self._client.read_holding_registers,
            }[register_type]
            # sending address = protocol address - 1.
            # This is the only line in the module that needs to know about this detail!
            rr = await func(start - 1, count=count, slave=self._slave)  # type: ignore
        except pymodbus.ModbusException as e:
            # e.g. no response from device
            raise ModbusError(
                f"connection error (for {register_type}, {start}-{start+count})"
            ) from e

        if rr.isError():
            logger.info(f"device error for {register_type}, {start}-{start+count}")

            if isinstance(rr, pymodbus.pdu.ExceptionResponse):
                if rr.exception_code == pymodbus.pdu.ModbusExceptions.GatewayNoResponse:
                    raise InvalidSlaveError(f"Slave ID {self._slave} is invalid")
                else:
                    raise ModbusError(f"Unknown exception response: {rr}")
            else:
                raise ModbusError(f"Unknown error response: {rr}")

        if len(rr.registers) != count:
            raise ModbusError(
                f"Mismatched number of registers requested({count}) "
                f"and responded {len(rr.registers)}"
            )

        assert isinstance(rr.registers, list)
        return rr.registers
