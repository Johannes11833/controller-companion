from dataclasses import dataclass

from controller_companion.controller_state import ControllerState


@dataclass
class Controller:
    name: str
    guid: str
    power_level: str
    instance_id: str
    initialized: bool
    state: ControllerState
