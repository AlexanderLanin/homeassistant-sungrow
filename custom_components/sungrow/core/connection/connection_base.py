import logging
from typing import Protocol

from deserialization import DecodedSignalValues
from result import Result
from signal_def import DatapointValueType, SignalDefinition, SignalDefinitions

logger = logging.getLogger(__name__)


class Connection(Protocol):
    async def connect(self): ...

    async def disconnect(self): ...

    @property
    def is_http(self) -> bool: ...

    @property
    def connected(self) -> bool: ...

    @property
    def slave(self) -> int: ...

    @slave.setter
    def slave(self, value: int): ...

    async def read(
        self,
        query: list[SignalDefinition],
    ) -> Result[DecodedSignalValues, Exception]: ...


# def _update_supported_state_based_on_values(
#     self,
#     query: list[SignalDefinition],
#     decoded: DecodedSignalValues,
#     all_signals: SignalDefinitions,
# ):
#     single_item_query = len(query) == 1

#     for signal, value in decoded.items():
#         todo = get_new_supported_state_based_on_value(signal, value, single_item_query)
#         # TODO todo
