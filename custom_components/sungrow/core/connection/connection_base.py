import logging

from result import Ok, Result

from custom_components.sungrow.core import signals2

from .signals import DatapointValueType

logger = logging.getLogger(__name__)

# TODO: switch str to SignalDefinition?!
DecodedSignals = dict[str, DatapointValueType]


# TODO: interfaces don't seem very pythonic?
class Connection:
    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    @property
    def is_http(self) -> bool:
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
        query: list[signals2.SignalDefinition] | signals2.SignalDefinition,
        all_signals: signals2.SignalDefinitions,
    ) -> Result[DecodedSignals, Exception]:
        # Always convert to a list to avoid different code paths
        if isinstance(query, signals2.SignalDefinition):
            query = [query]
        result = await self._read(query)

        if isinstance(result, Ok):
            self._update_supported_state_based_on_values(
                query, result.ok_value, all_signals
            )

        return result

    def _update_supported_state_based_on_values(
        self,
        query: list[signals2.SignalDefinition],
        decoded: DecodedSignals,
        all_signals: signals2.SignalDefinitions,
    ):
        single_item_query = len(query) == 1

        for name, value in decoded.items():
            signal = all_signals.get_signal_definition_by_name(name)
            assert signal, f"Signal {name} not found in all_signals"
            signal.update_supported_state_based_on_value(
                value, single_item_query, all_signals
            )

    async def _read(
        self,
        query: list[signals2.SignalDefinition],
    ) -> Result[DecodedSignals, Exception]:
        raise NotImplementedError
