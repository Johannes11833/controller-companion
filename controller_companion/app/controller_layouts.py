from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image

from controller_companion.app import resources
from controller_companion.app.utils import is_dark_appearance


class ControllerType(Enum):
    XBOX = "Xbox"
    PLAYSTATION = "PlayStation"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class ControllerLayout(ABC):
    @abstractmethod
    def get_button_icon_dir(self) -> Path:
        """The artwork folder matching the current light/dark appearance."""

    @abstractmethod
    def get_chip_icon_path(self) -> Optional[Path]:
        """The controller family glyph shown as an icon on the chips."""

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

    def get_button_icons(
        self,
        icon_size: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Image.Image]:
        icons = {}
        # the dark artwork is invisible on dark backgrounds, so a light
        # variant of every button is used while the app is in dark mode
        dir = self.get_button_icon_dir()
        for button in list(self.get_button_layout().keys()) + list(
            self.get_d_pad_layout().keys()
        ):
            path = dir / f"{button.replace(' ','_')}.png"
            if path.is_file():
                image = Image.open(path)
                if icon_size:
                    image = image.resize(icon_size)
            else:
                image = None

            icons[button] = image

        return icons


class XboxControllerLayout(ControllerLayout):
    def __repr__(self):
        return "XboxControllerLayout"

    def get_button_icon_dir(self) -> Path:
        if is_dark_appearance():
            return resources.XBOX_BUTTONS_LIGHT_DIR
        return resources.XBOX_BUTTONS_DEFAULT_DIR

    def get_chip_icon_path(self) -> Optional[Path]:
        return resources.XBOX_BUTTONS_DEFAULT_DIR / "X-Box.png"

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
            "Share": 11,
        }

    def get_d_pad_layout(self) -> Dict[str, Tuple[int, int]]:
        return {
            "Left": (-1, 0),
            "Right": (1, 0),
            "Up": (0, 1),
            "Down": (0, -1),
            # "Left-Down": (-1, -1),
            # "Left-Up": (-1, 1),
            # "Right-Up": (1, 1),g
            # "Right-Down": (1, -1),
        }

    def button_aliases_to_xbox(self) -> Dict[str, str]:
        return {v: v for v in self.get_button_layout().keys()}


class PlayStationControllerLayout(ControllerLayout):

    def __repr__(self):
        return "PlayStationControllerLayout"

    def get_button_icon_dir(self) -> Path:
        if is_dark_appearance():
            return resources.PLAYSTATION_BUTTONS_LIGHT_DIR
        return resources.PLAYSTATION_BUTTONS_DEFAULT_DIR

    def get_chip_icon_path(self) -> Optional[Path]:
        return resources.PLAYSTATION_BUTTONS_DEFAULT_DIR / "PS.png"

    def get_button_layout(self) -> Dict[str, int]:
        return {
            "Cross": 0,
            "Circle": 1,
            "Square": 2,
            "Triangle": 3,
            "Share": 4,
            "PS": 5,
            "Options": 6,
            "L-Stick": 7,
            "R-Stick": 8,
            "L1": 9,
            "R1": 10,
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
            "Cross": "A",
            "Circle": "B",
            "Square": "X",
            "Triangle": "Y",
            "Share": "Back",
            "PS": "X-Box",
            "Options": "Start",
            "L1": "LB",
            "R1": "RB",
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
