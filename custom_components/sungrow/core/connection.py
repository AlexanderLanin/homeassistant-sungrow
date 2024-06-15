import logging

from result import Ok, Result

from custom_components.sungrow.core import (
    signals,
)

from .signals import DatapointValueType

logger = logging.getLogger(__name__)

DecodedSignals = dict[str, DatapointValueType]


class Connection:
    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    @property
    def connected(self) -> bool:
        raise NotImplementedError

    @property
    def slave(self) -> int:
        raise NotImplementedError

    @slave.setter
    def slave(self, value: int):
        raise NotImplementedError

    async def read(
        self,
        query: list[signals.SignalDefinition] | signals.SignalDefinition,
    ) -> Result[DecodedSignals, Exception]:
        # Always convert to a list to avoid different code paths
        if isinstance(query, signals.SignalDefinition):
            query = [query]
        result = await self._read(query)

        if isinstance(result, Ok):
            self._update_supported_state_based_on_values(query, result.ok_value)

        return result

    def _update_supported_state_based_on_values(
        self,
        query: list[signals.SignalDefinition],
        decoded: DecodedSignals,
    ):
        single_item_query = len(query) == 1

        def get_signal_by_name(name):
            return next((signal for signal in query if signal.name == name), None)

        for name, value in decoded.items():
            signal = get_signal_by_name(name)
            assert signal
            signal.update_supported_state_based_on_value(
                value, was_queried_individually=single_item_query
            )

    async def _read(
        self,
        query: list[signals.SignalDefinition],
    ) -> Result[DecodedSignals, Exception]:
        raise NotImplementedError
