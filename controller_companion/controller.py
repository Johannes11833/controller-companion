from dataclasses import dataclass
import os
from typing import List, Optional, Tuple

from controller_companion.app.controller_layouts import (
    ControllerType,
    get_layout,
)

from controller_companion.logs import logger

# import pygame, hide welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "yes"
import pygame


from controller_companion.controller_state import ControllerState


class Controller:

    def __init__(
        self,
        name: str,
        guid: str,
        power_level: str,
        initialized: bool,
        controller_type: ControllerType,
        active_controller_inputs: Optional[List[str]] = None,
        __controller_state: Optional[ControllerState] = None,
    ):
        self.name = name
        self.guid = guid
        self.power_level = power_level
        self.initialized = initialized
        self.layout = get_layout(controller_type)
        self.active_controller_inputs = (
            active_controller_inputs if active_controller_inputs else []
        )
        self.__controller_state = (
            __controller_state if __controller_state else ControllerState()
        )

    @classmethod
    def from_pygame(cls, joystick: pygame.joystick.JoystickType):
        name = joystick.get_name().removeprefix("Controller (").removesuffix(")")
        controller_type = ControllerType.XBOX
        if "xbox" in name.lower():
            controller_type = ControllerType.XBOX
        elif any([n in name.lower() for n in ["ps3", "ps4", "ps5", "playstation"]]):
            controller_type = ControllerType.PLAYSTATION
        else:
            logger.warning(
                f'Failed to find out the type of controller for "{name}" so the {controller_type.name} layout will be used.'
            )

        return cls(
            # on windows the controller name is wrapped inside "Controller()" when connected via USB (XBOX)
            name,
            guid=joystick.get_guid(),
            power_level=joystick.get_power_level(),
            initialized=joystick.get_init(),
            active_controller_inputs=[],
            controller_type=controller_type,
        )

    def matches(
        self,
        active_controller_inputs: List[str],
        controller_type: ControllerType,
    ) -> bool:
        other = Controller(
            None,
            None,
            None,
            False,
            controller_type=controller_type,
            active_controller_inputs=active_controller_inputs,
        )

        return (
            self.get_active_xbox_button_names() == other.get_active_xbox_button_names()
        )

    def update_controller_state(
        self,
        button: Optional[int] = None,
        d_pad_state: Optional[Tuple[int, int]] = None,
        add_button: bool = True,
    ):
        if button is not None:
            if add_button:
                self.__controller_state.active_buttons.append(button)
            else:
                self.__controller_state.active_buttons.remove(button)

        if d_pad_state is not None:
            self.__controller_state.d_pad_state = d_pad_state

        self.active_controller_inputs = self.layout.button_numbers_to_names(
            buttons=self.__controller_state.active_buttons,
            d_pad=self.__controller_state.d_pad_state,
        )
        self.active_controller_inputs.sort()

    def get_active_xbox_button_names(self):
        return self.layout.convert_button_names_to_xbox(
            self.active_controller_inputs, sort=True
        )

    def __repr__(self):
        content = ", ".join(
            f'{key}: "{value}"'
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        )
        return f"Controller({content})"
