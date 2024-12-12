from dataclasses import dataclass
import os

# import pygame, hide welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "yes"
import pygame


from controller_companion.controller_state import ControllerState
from controller_companion.logs import logger


@dataclass
class Controller:
    name: str
    guid: str
    power_level: str
    instance_id: str
    initialized: bool
    state: ControllerState

    @classmethod
    def from_pygame(cls, joystick: pygame.joystick.JoystickType):
        return cls(
            # on windows the controller name is wrapped inside "Controller()" when connected via USB (XBOX)
            name=joystick.get_name().removeprefix("Controller (").removesuffix(")"),
            guid=joystick.get_guid(),
            power_level=joystick.get_power_level(),
            instance_id=joystick.get_instance_id(),
            initialized=joystick.get_init(),
            state=ControllerState(),
        )
