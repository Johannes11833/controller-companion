from typing import Dict, List, Optional, Tuple


button_mapper = {
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
button_mapper_inv = {v: k for k, v in button_mapper.items()}

d_pad_mapper = {
    "Left": (-1, 0),
    "Right": (1, 0),
    "Up": (0, 1),
    "Down": (0, -1),
    "Left-Down": (-1, -1),
    "Left-Up": (-1, 1),
    "Right-Up": (1, 1),
    "Right-Down": (1, -1),
}
d_pad_mapper_inv = {v: k for k, v in d_pad_mapper.items()}


class ControllerState:

    def __init__(
        self,
        active_buttons: Optional[List[int]] = None,
        d_pad_state: Tuple[int, int] = (0, 0),
    ):
        self.active_buttons: List[int] = active_buttons if active_buttons else []
        self.d_pad_state: Tuple[int, int] = d_pad_state

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        self.active_buttons.sort()
        return f"<ControllerState active_buttons: {self.active_buttons}, d_pad_action: {self.d_pad_state}>"

    def describe(self) -> str:
        self.active_buttons.sort()
        s = ",".join([button_mapper_inv[button] for button in self.active_buttons])
        d_pad_action_description = d_pad_mapper_inv.get(self.d_pad_state, None)
        s += (
            "," + d_pad_action_description
            if d_pad_action_description is not None
            else ""
        )

        return f'<{s.removeprefix(",")}>'

    def to_dict(self):
        return {
            "active_buttons": self.active_buttons,
            "d_pad_state": self.d_pad_state,
        }

    @classmethod
    def from_dict(cls, dict: Dict):

        return cls(
            active_buttons=dict["active_buttons"],
            # tuples become lists during json conversion
            d_pad_state=tuple(dict["d_pad_state"]),
        )
