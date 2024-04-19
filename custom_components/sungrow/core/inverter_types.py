from dataclasses import dataclass


@dataclass
class Sensor:
    name: str
    value: bool | int | float | str | None
    unit_of_measurement: str | None = None

    def __repr__(self) -> str:
        suffix = f" {self.unit_of_measurement}" if self.unit_of_measurement else ""
        return f"{self.name} = {self.value}{suffix}"
