from dataclasses import dataclass
from enum import Enum


@dataclass
class Sensor:
    name: str
    value: bool | int | float | str | None
    unit_of_measurement: str | None = None

    def __repr__(self) -> str:
        suffix = f" {self.unit_of_measurement}" if self.unit_of_measurement else ""
        return f"{self.name} = {self.value}{suffix}"


class Level(Enum):
    CONNECTION = 1
    BASIC = 2
    ADVANCED = 3
    LOTS_AND_LOTS = 4
    DEBUG = 5
