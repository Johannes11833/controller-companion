from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Tuple


class ControllerType(Enum):
    XBOX = "Xbox"
    PLAYSTATION = "PlayStation"
    CUSTOM = "Custom"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class ControllerLayout(ABC):
    @abstractmethod
    def get_button_layout(self) -> Dict[str, int]:
        pass

    @abstractmethod
    def get_d_pad_layout(self) -> Dict[str, Tuple[int, int]]:
        pass

    @abstractmethod
    def button_aliases_to_xbox(self) -> Dict[str, str]:
        pass

    def convert_button_names_to_xbox(
        self, buttons: List[str], sort: bool = True
    ) -> List[str]:
        aliases = self.button_aliases_to_xbox()
        out = [aliases.get(button, button) for button in buttons]

        if sort:
            out.sort()

        return out

    def button_numbers_to_names(
        self, buttons: List[int], d_pad=Tuple[int, int]
    ) -> List[str]:
        names = []
        button_mapper_inv = {v: k for k, v in self.get_button_layout().items()}
        d_pad_mapper_inv = {v: k for k, v in self.get_d_pad_layout().items()}

        for b in buttons:
            names.append(button_mapper_inv.get(b, f"Button {b}"))

        if d_pad_mapper_inv.get(d_pad, None) is not None:
            names.append(d_pad_mapper_inv[d_pad])

        return names

    def get_valid_input_names(self):
        return list(self.get_button_layout().keys()) + list(
            self.get_d_pad_layout().keys()
        )


class XboxControllerLayout(ControllerLayout):
    def __repr__(self):
        return "XboxControllerLayout"

    def get_button_layout(self) -> Dict[str, int]:
        return {
            "A": 0,
            "B": 1,
            "X": 2,
            "Y": 3,
            "LB": 4,
            "RB": 5,
            "Back": 6,
            "Start": 7,
            "L-Stick": 8,
            "R-Stick": 9,
            "X-Box": 10,
        }

    def get_d_pad_layout(self) -> Dict[str, Tuple[int, int]]:
        return {
            "Left": (-1, 0),
            "Right": (1, 0),
            "Up": (0, 1),
            "Down": (0, -1),
            "Left-Down": (-1, -1),
            "Left-Up": (-1, 1),
            "Right-Up": (1, 1),
            "Right-Down": (1, -1),
        }

    def button_aliases_to_xbox(self) -> Dict[str, str]:
        return {v: v for v in self.get_button_layout().keys()}


class PlayStationControllerLayout(ControllerLayout):

    def __repr__(self):
        return "PlayStationControllerLayout"

    def get_button_layout(self) -> Dict[str, int]:
        return {
            "X": 0,
            "O": 1,
            "□": 2,
            "△": 3,
            "Share": 4,
            "PS": 5,
            "Options": 6,
            "L-Stick": 7,
            "R-Stick": 8,
            "L1": 9,
            "L2": 10,
            "Up": 11,
            "Down": 12,
            "Left": 13,
            "Right": 14,
            "Touch Pad": 15,
        }

    def get_d_pad_layout(self) -> Dict[str, Tuple[int, int]]:
        # on the PS4 controller, all buttons on the D-Pad are treated as normal buttons by pygame.
        return {}

    def button_aliases_to_xbox(self) -> Dict[str, str]:
        return {
            "X": "A",
            "O": "B",
            "□": "X",
            "△": "Y",
            "Share": "Back",
            "PS": "X-Box",
            "Options": "Start",
            "L1": "LB",
            "L2": "RB",
        }


def get_layout(controller_type: ControllerType) -> ControllerLayout:
    layout = None
    if controller_type == ControllerType.XBOX:
        layout = XboxControllerLayout()
    elif controller_type == ControllerType.PLAYSTATION:
        layout = PlayStationControllerLayout()
    else:
        raise Exception(f"Layout for {controller_type} not yet implemented!")

    return layout
