from dataclasses import dataclass

from custom_components.sungrow.core.signals import DatapointValueType


@dataclass
class Datapoint:
    name: str  # do we need the name here?
    value: DatapointValueType
    unit_of_measurement: str | None = None

    def __repr__(self) -> str:
        if self.unit_of_measurement:
            return f"{self.name} = {self.value} {self.unit_of_measurement}"
        else:
            return f"{self.name} = {self.value}"
