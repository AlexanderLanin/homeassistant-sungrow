from custom_components.sungrow.core.inverter_types import Datapoint
from custom_components.sungrow.core.signals import DatapointValueType


def calculate(new_data: dict[str, DatapointValueType]) -> dict[str, Datapoint]:
    extra_data: dict[str, Datapoint] = {}
    for subclass in _subclasses:
        extra = subclass()(new_data)
        for datapoint in extra or []:
            extra_data[datapoint.name] = datapoint
    return extra_data


_subclasses: list[type["_ExtraSensor"]] = []


class _ExtraSensor:
    def __init_subclass__(cls) -> None:
        _subclasses.append(cls)

    @staticmethod
    def __call__(new_data: dict[str, DatapointValueType]) -> list[Datapoint]:
        raise NotImplementedError


def _convert_signals_to_timestamp(
    data: dict[str, DatapointValueType], prefix: str = ""
):
    try:
        # format: YYYY-MM-DD HH:MM:SS
        timestamp = "%04d-%02d-%02d %02d:%02d:%02d" % (
            int(data[prefix + "year"]),  # type: ignore
            int(data[prefix + "month"]),  # type: ignore
            int(data[prefix + "day"]),  # type: ignore
            int(data[prefix + "hour"]),  # type: ignore
            int(data[prefix + "minute"]),  # type: ignore
            int(data[prefix + "second"]),  # type: ignore
        )
    except KeyError:
        timestamp = None

    return timestamp


def _drop_timestamp_info(data: dict[str, DatapointValueType], prefix: str = ""):
    for key in ["year", "month", "day", "hour", "minute", "second"]:
        data.pop(prefix + key, None)


class Timestamp(_ExtraSensor):
    @staticmethod
    def __call__(new_data: dict[str, DatapointValueType]):
        # If it's enabled, convert the timestamp to a string
        if new_data.get("year"):
            v = _convert_signals_to_timestamp(new_data)
            _drop_timestamp_info(new_data)
            return [Datapoint("timestamp", v, None)]


class AlarmTimestamp(_ExtraSensor):
    @staticmethod
    def __call__(new_data: dict[str, DatapointValueType]):
        if new_data.get("pid_alarm_code"):
            v = _convert_signals_to_timestamp(new_data, "alarm_time_")
            _drop_timestamp_info(new_data, "alarm_time_")
            return [Datapoint("alarm_timestamp", v, None)]


class Mppt(_ExtraSensor):
    @staticmethod
    def __call__(new_data: dict[str, DatapointValueType]):
        extras: list[Datapoint] = []

        # Add '_power' for every mppt
        # (P = U * I; Watts = Volts * Amps)
        for i in range(1, 12):
            # current is not available => unsupported signal
            # current is None => no data
            if f"mppt_{i}_current" in new_data and f"mppt_{i}_voltage" in new_data:
                I = new_data[f"mppt_{i}_current"]  # noqa: N806, E741
                U = new_data[f"mppt_{i}_voltage"]  # noqa: N806
                if U is None or I is None:
                    value = None
                else:
                    assert isinstance(U, float | int), U
                    assert isinstance(I, float | int), I
                    value = U * I

                extras.append(Datapoint(f"mppt_{i}_power", value, "W"))
        return extras
