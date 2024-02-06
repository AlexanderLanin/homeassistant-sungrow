import asyncio
import logging
import time

from beartype.claw import beartype_all

from custom_components.sungrow.core.modbus_http import HttpConnection

if __package__ is None:
    # Script was executed from the command line
    import fix_path  # type: ignore  # noqa: F401


beartype_all()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    connection = HttpConnection("192.168.13.58", 1, 8082)
    connected = await connection.connect()
    if not connected:
        logger.error("Could not connect to inverter")
        return

    assert connection._inverter
    assert connection._token

    response = await connection._ws_query(
        {
            "dev_id": connection._inverter["dev_id"],
            "dev_type": connection._inverter["dev_type"],
            "dev_code": connection._inverter["dev_code"],
            "type": "3",  # todo: Why 3?
            "param_addr": 4950,
            "param_num": 100,
            "param_type": 0,  # read = 0
            "token": connection._token,
            "lang": "en_us",
            "time123456": int(time.time()),
        }
    )
    print(response)

    await connection.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
