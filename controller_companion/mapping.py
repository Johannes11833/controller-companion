from enum import Enum
import subprocess
from typing import Dict, List
import pyautogui
from controller_companion.app.controller_layouts import (
    ControllerType,
)
from controller_companion.app.utils import OperatingSystem, get_os
from controller_companion.controller_state import (
    button_mapper,
    d_pad_mapper,
)


class ActionType(Enum):
    TASK_KILL_BY_NAME = "Kill by Name"
    CONSOLE_COMMAND = "Console Command"
    KEYBOARD_SHORTCUT = "Keyboard Shortcut"


class Mapping:

    def __init__(
        self,
        action_type: ActionType,
        target: str,
        active_controller_buttons: List[str],
        name: str,
        controller_type: ControllerType = ControllerType.XBOX,
    ):
        self.name = name
        self.action_type = action_type
        self.target = target
        self.active_controller_buttons = active_controller_buttons
        self.controller_type = controller_type

    def execute(self):
        if self.action_type == ActionType.TASK_KILL_BY_NAME:
            os = get_os()
            if os == OperatingSystem.WINDOWS:
                subprocess.run(["taskkill", "/im", self.target])
            elif os == OperatingSystem.LINUX:
                subprocess.run(["pkill", self.target])
            else:
                subprocess.run(["killall", self.target])

        elif self.action_type == ActionType.KEYBOARD_SHORTCUT:
            keys = self.target.split("+")

            invalid_keys = [k for k in keys if not pyautogui.isValidKey(k)]
            if invalid_keys:
                print(
                    f"Invalid keys provided as keyboard shortcuts! The following keys are invalid: {invalid_keys}"
                )
                return

            pyautogui.hotkey(keys)
        else:
            subprocess.run(self.target)

    def to_dict(self):
        return {
            "name": self.name,
            "action_type": self.action_type.name,
            "target": self.target,
            "active_controller_buttons": self.active_controller_buttons,
            "controller_type": self.controller_type.name,
        }

    @classmethod
    def from_dict(cls, dict: Dict):

        return cls(
            name=dict["name"],
            target=dict["target"],
            action_type=ActionType[dict["action_type"]],
            active_controller_buttons=dict["active_controller_buttons"],
            controller_type=ControllerType[dict["controller_type"]],
        )

    def get_valid_keyboard_keys() -> List[str]:
        return pyautogui.KEYBOARD_KEYS

    def get_valid_controller_inputs() -> List[str]:
        return list(button_mapper.keys()) + list(d_pad_mapper.keys())

    def get_shortcut_string(self) -> str:
        return "+".join(self.active_controller_buttons)

    def __repr__(self):
        content = ", ".join(f'{key}: "{value}"' for key, value in self.__dict__.items())
        return f"Controller({content})"
