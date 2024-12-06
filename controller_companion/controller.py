from dataclasses import dataclass


@dataclass
class Controller:
    name: str
    guid: str
    power_level: str
    instance_id: str
    initialized: bool
