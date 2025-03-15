"""
A convinience wrapper for pymodbus.
"""

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

import modbus_connection_base
import pymodbus
import pymodbus.client
import pymodbus.exceptions
import pymodbus.framer.base
import pymodbus.pdu
from modbus_connection_base import (
    ModbusConnection_Base,
    RegisterType,
)
from modbus_types import RegisterRange
from result import Err, Ok, Result

logger = logging.getLogger(__name__)


# if pymodbus.__version__ != "3.6.8":
#     raise RuntimeError("This fix needs to be adjusted")

# # WiNet-S responds with slightly incorrect message headers in case of errors.
# # Version: M_WiNet-S_V01_V01_A
# # Pymodbus will trigger a needless TCP reconnect, and it will report "no message
# # received". While we can deal with the latter, the former is a bit more annoying.
# # The root cause is WiNet transmits 3 bytes of data, but reports to transmit 2.
# # As we know what exactly is wrong with the message, we simply need to fix the header
# # length before pymodbus tries to decode it.
# # pymodbus 3.6.6 has a function named _validate_slave_id which is called just at the
# # right time to fix the message header. We don't particularly care about what it
# # actually does, as we can simply inject our fix right before it is called:
# def inject_message_header_fix():
#     if pymodbus.__version__ != "3.6.6":
#         raise RuntimeError("This fix needs to be adjusted")

#     real_validate_slave_id = pymodbus.framer.base.ModbusFramer._validate_slave_id

#     def injected(self, a, b):
#         if self._buffer[self._hsize] & 0x80 and self._header["len"] == 2:
#             self._header["len"] = 3
#         return real_validate_slave_id(self, a, b)

#     pymodbus.framer.base.ModbusFramer._validate_slave_id = injected  # type: ignore


# inject_message_header_fix()


class ModbusConnection_Pymodbus(ModbusConnection_Base):  # noqa: N801
    """A pymodbus connection to a single slave."""

    MIN_DELAY = timedelta(seconds=2)

    def __init__(self, host: str, port: int | None):
        if not port:
            port = self.default_port()

        super().__init__(host, port)

        self._client = pymodbus.client.AsyncModbusTcpClient(
            host=host, port=port, timeout=2, retries=0, retry_on_empty=True
        )

        self._ever_succeeded = False

        self._next_allowed_call = datetime.min

    @staticmethod
    def default_port() -> int:
        return 502

    @property
    def is_http(self) -> bool:
        return False

    async def _throttle(self):
        now = datetime.now()
        if now < self._next_allowed_call:
            delay = self._next_allowed_call - now
            await asyncio.sleep(delay.total_seconds())
        # FIXME: next_allowed_call must be set AFTER the function has finished
        # executing. Use a context manager instead?!
        self._next_allowed_call = datetime.now() + self.MIN_DELAY

    async def connect(self):
        if self._client.connected:
            return True
        else:
            logger.debug("Connecting to %s:%s", self._host, self._port)
            self._stats.connections += 1
            await self._throttle()
            return await self._client.connect()

    async def disconnect(self):
        self._ever_succeeded = False

        # The _client has a 'reconnect_task' which it will cancel and delete on close().
        # But we want to wait for it to actually finish before returning,
        # so we are cleaning up properly.
        # Specifically, pytest will complain about lingering tasks if we don't wait for
        # this task to finish.
        logger.debug("Disconnecting from %s:%s", self._host, self._port)
        reconnect_task = self._client.reconnect_task
        await self._throttle()
        self._client.close()
        if reconnect_task:
            # Catch CancelledError, as this is expected.
            with contextlib.suppress(asyncio.CancelledError):
                await reconnect_task
        logger.debug("Disconnected from %s:%s", self._host, self._port)

    @property
    def connected(self) -> bool:
        return self._client.connected

    async def __call_pymodbus_read(
        self,
        register_range: RegisterRange,
    ) -> Result[pymodbus.pdu.ModbusResponse, Exception]:
        """Note: this function does not check isError() on the response."""

        assert self._slave is not None, "Slave ID not set"
        await self._throttle()

        read_registers = {
            RegisterType.READ: self._client.read_input_registers,
            RegisterType.HOLD: self._client.read_holding_registers,
        }[register_range.register_type]
        try:
            # Note: sending address = protocol address - 1.
            # This is the only line in the module that needs to know about this detail!
            rr: pymodbus.pdu.ModbusResponse = await read_registers(
                register_range.start - 1, count=register_range.length, slave=self._slave
            )
        except pymodbus.exceptions.ConnectionException as e:
            return Err(
                modbus_connection_base.CannotConnectError(f"{type(e).__name__}: {e}")
            )
        except pymodbus.exceptions.ModbusIOException as e:
            return Err(
                modbus_connection_base.ModbusError(
                    f"Unknown IO Error in pymodbus: {type(e).__name__}: {e}"
                )
            )
        except Exception as e:
            return Err(
                modbus_connection_base.ModbusError(f"Unknown error in pymodbus: {e}")
            )

        return Ok(rr)

    async def _read_range(
        self,
        register_range: RegisterRange,
        recursion=False,
    ) -> Result[list[int], Exception]:
        """
        Reads `address_count` registers of type `register_type` starting at
        `address_start`.
        Note: each register is 16 bits, so `address_count` is the number of registers,
        not bytes.
        """
        logger.debug(f"_read_range({register_range=}, {recursion=})")
        if not await self.connect():
            raise modbus_connection_base.CannotConnectError(
                "Cannot connect to inverter for reading"
            )

        rr_res = await self.__call_pymodbus_read(register_range)
        if isinstance(rr_res, Err):
            return rr_res

        rr = rr_res.ok_value
        if rr.isError() and isinstance(rr, pymodbus.pdu.ExceptionResponse):
            if rr.exception_code == pymodbus.pdu.ModbusExceptions.GatewayNoResponse:
                return Err(
                    modbus_connection_base.InvalidSlaveError(
                        f"Slave ID {self._slave} is invalid"
                    )
                )
            elif rr.exception_code == pymodbus.pdu.ModbusExceptions.IllegalAddress:
                return Err(
                    modbus_connection_base.UnsupportedRegisterQueriedError(
                        f"Inverter does not support {register_range}: {rr}"
                    )
                )
            elif rr.exception_code == pymodbus.pdu.ModbusExceptions.SlaveFailure:
                # Deprecated? Do we need this?
                if recursion:
                    logger.warning(
                        "Slave failure on %s: %s. Please inform the developer.",
                        register_range,
                        rr,
                    )
                    return Err(
                        modbus_connection_base.ModbusError(
                            f"Slave failure on {register_range}: {rr}"
                        )
                    )
                else:
                    return await self._read_range(
                        register_range,
                        recursion=True,
                    )
            else:
                return Err(
                    modbus_connection_base.ModbusError(f"Unknown error response: {rr}")
                )

        assert isinstance(rr.registers, list)  # for mypy

        if len(rr.registers) != register_range.length:
            return Err(
                modbus_connection_base.ModbusError(
                    f"Mismatched number of registers "
                    f"(requested {register_range}) and responded {len(rr.registers)})"
                )
            )

        self._ever_succeeded = True
        return Ok(rr.registers)

    def __str__(self):
        return f"modbus({self._host}:{self._port}, slave: {self._slave or 'unknown'})"
