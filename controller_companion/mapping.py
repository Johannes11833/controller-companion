from enum import Enum
import subprocess
from typing import Dict, List
import pyautogui
from controller_companion.controller_state import ControllerState


class ActionType(Enum):
    TASK_KILL_BY_NAME = "Kill by Name"
    CONSOLE_COMMAND = "Console Command"
    KEYBOARD_SHORTCUT = "Keyboard Shortcut"


class Mapping:

    def __init__(
        self,
        action_type: ActionType,
        target: str,
        controller_state: ControllerState,
        name: str,
    ):
        self.name = name
        self.action_type = action_type
        self.target = target
        self.controller_state = controller_state

    def execute(self):
        if self.action_type == ActionType.TASK_KILL_BY_NAME:
            subprocess.run(["taskkill", "/im", self.target])
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

    def __str__(self):
        return f"Controller{self.controller_state.describe()} --> Action<name: {self.name}, target: {self.target}, type: {self.action_type.name}>"

    def to_dict(self):
        return {
            "name": self.name,
            "action_type": self.action_type.name,
            "target": self.target,
            "controller_state": self.controller_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, dict: Dict):

        return cls(
            name=dict["name"],
            target=dict["target"],
            action_type=ActionType[dict["action_type"]],
            controller_state=ControllerState.from_dict(dict["controller_state"]),
        )

    def get_valid_keyboard_keys() -> List[str]:
        return pyautogui.KEYBOARD_KEYS
