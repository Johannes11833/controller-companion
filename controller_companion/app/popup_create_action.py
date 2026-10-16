from typing import Optional

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QIcon, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from controller_companion.app import resources
from controller_companion.app.controller_layouts import (
    ControllerType,
    get_layout,
)
from controller_companion.app.utils import (
    OperatingSystem,
    get_os,
    pil_to_qpixmap,
    set_window_icon,
)
from controller_companion.logs import logger

from controller_companion.mapping import Mapping, ActionType


class CreateActionPopup(QDialog):
    def __init__(
        self,
        master=None,
        mapping: Optional[Mapping] = None,
        title: str = "Create Action",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.setWindowTitle(title)
        set_window_icon(self)

        self.result: Optional[Mapping] = None
        self.initial_mapping = mapping
        self.pressed_keys = set()
        self.var_buttons = {}
        self.button_group: Optional[QButtonGroup] = None
        self.gamepad_input_icons = {}

        # init controller layout
        self.controller_type = ControllerType.XBOX
        self.layout = get_layout(self.controller_type)
        self.button_mapper = self.layout.get_button_layout()
        self.d_pad_mapper = self.layout.get_d_pad_layout()

        main_layout = QVBoxLayout(self)

        # ------------------------- controller shortcut input ------------------------- #
        frame_inputs = QGroupBox("Controller Shortcut", self)
        frame_inputs_layout = QHBoxLayout(frame_inputs)

        frame_inputs_top = QVBoxLayout()
        frame_inputs_top.addWidget(QLabel("Layout:", frame_inputs))
        self.label_layout = QLabel(frame_inputs)
        frame_inputs_top.addWidget(self.label_layout)
        self.combobox_layout = QComboBox(frame_inputs)
        self.combobox_layout.addItems(
            [e.value + " Controller" for e in ControllerType]
        )
        self.combobox_layout.currentIndexChanged.connect(self.update_layout)
        frame_inputs_top.addWidget(self.combobox_layout)
        frame_inputs_top.addStretch()
        frame_inputs_layout.addLayout(frame_inputs_top)

        self.frame_buttons = QWidget(frame_inputs)
        self.frame_buttons_layout = QGridLayout(self.frame_buttons)
        frame_inputs_layout.addWidget(self.frame_buttons)

        main_layout.addWidget(frame_inputs)

        # ----------------------------------- action ----------------------------------- #
        frame_action = QGroupBox("Action", self)
        frame_action_layout = QGridLayout(frame_action)
        frame_action_layout.addWidget(QLabel("Type:", frame_action), 0, 0)
        self.combobox_action_type = QComboBox(frame_action)
        self.combobox_action_type.addItems([e.value for e in ActionType])
        self.combobox_action_type.currentIndexChanged.connect(
            self.action_type_changed
        )
        frame_action_layout.addWidget(self.combobox_action_type, 0, 1)
        frame_action_layout.addWidget(QLabel("Target:", frame_action), 0, 2)
        self.entry_target_command = QLineEdit(frame_action)
        frame_action_layout.setColumnStretch(3, 1)
        frame_action_layout.addWidget(self.entry_target_command, 0, 3)
        main_layout.addWidget(frame_action)

        # ------------------------------------ save ------------------------------------ #
        frame_save = QGroupBox("Save", self)
        frame_save_layout = QHBoxLayout(frame_save)
        frame_save_layout.addWidget(QLabel("Name:", frame_save))
        self.entry_name = QLineEdit(frame_save)
        self.entry_name.setPlaceholderText("name of the shortcut")
        frame_save_layout.addWidget(self.entry_name)
        save_button = QPushButton("Save", frame_save)
        save_button.setDefault(True)
        save_button.clicked.connect(self.on_save)
        frame_save_layout.addWidget(save_button)
        main_layout.addWidget(frame_save)

        self.action_type = ActionType.TASK_KILL_BY_NAME

        # capture keyboard shortcut input in the target entry
        self.entry_target_command.installEventFilter(self)

        self.update_layout()
        self.action_type_changed()
        self.apply_initial_mapping()

    def apply_initial_mapping(self):
        """Prefill the inputs when editing or duplicating an existing mapping."""
        if self.initial_mapping is None:
            return

        mapping = self.initial_mapping

        # switch to the controller layout of the mapping (rebuilds the button inputs)
        self.combobox_layout.setCurrentIndex(
            list(ControllerType).index(mapping.controller_type)
        )
        self.combobox_action_type.setCurrentIndex(
            list(ActionType).index(mapping.action_type)
        )
        self.entry_target_command.setText(mapping.target)
        self.entry_name.setText(mapping.name)

        for button in mapping.active_controller_buttons:
            if button in self.var_buttons:
                self.var_buttons[button].setChecked(True)
            elif button in self.d_pad_mapper:
                d_pad_index = list(self.d_pad_mapper.keys()).index(button)
                self.button_group.button(d_pad_index).setChecked(True)

    def on_save(self):
        active_controller_buttons = [
            button
            for button, check in self.var_buttons.items()
            if check.isChecked()
        ]

        selected_d_pad_index = self.button_group.checkedId()
        if selected_d_pad_index != -1:
            active_controller_buttons.append(
                list(self.d_pad_mapper.keys())[selected_d_pad_index]
            )

        target = self.entry_target_command.text()
        name = self.entry_name.text()

        error = None
        if len(active_controller_buttons) == 0:
            error = "No controller shortcut was selected!"
        elif target.strip() == "":
            error = "No target command was specified!"
        elif name.strip() == "":
            error = "The name of the shortcut was not set!"
        if error:
            QMessageBox.critical(self, "Error", error)
            return

        self.result = Mapping(
            action_type=self.action_type,
            target=target,
            active_controller_buttons=active_controller_buttons,
            name=name,
            controller_type=self.controller_type,
        )

        self.accept()

    def action_type_changed(self, _=None):
        self.action_type = ActionType(self.combobox_action_type.currentText())

        if self.action_type == ActionType.TASK_KILL_BY_NAME:
            self.entry_target_command.setPlaceholderText(
                "name of task to kill (e.g. explorer.exe)"
            )
        elif self.action_type == ActionType.KEYBOARD_SHORTCUT:
            self.pressed_keys.clear()
            self.entry_target_command.setPlaceholderText(
                "click here, then enter shortcut"
            )
        else:
            self.entry_target_command.setPlaceholderText(
                "custom arbitrary console command"
            )

    def eventFilter(self, watched, event):
        if (
            watched is self.entry_target_command
            and event.type() == QEvent.Type.KeyPress
            and self.action_type == ActionType.KEYBOARD_SHORTCUT
        ):
            self.capture_key(event)
            return True

        return super().eventFilter(watched, event)

    def capture_key(self, event: QKeyEvent):
        valid_keys = Mapping.get_valid_keyboard_keys()
        key = self.__key_event_to_name(event)

        if key is None or key not in valid_keys:
            logger.warning(f"Unknown key event {event}")
            return

        if key in ["escape", "backspace"]:
            self.pressed_keys.clear()
        elif key != "+":
            self.pressed_keys.add(key)

        # sort keys
        sorted_keys = list(self.pressed_keys)
        ranks = ["ctrl", "win", "command", "alt", "shift"]
        # 24 f keys supported by PyAutoGUI
        f_keys = [f"f{i}" for i in range(1, 25)]
        ranks.extend(f_keys)
        sorted_keys.sort(
            key=lambda k: (
                str(ranks.index(k))
                if k in ranks
                else f"_{list(self.pressed_keys).index(k)}"
            )
        )

        self.entry_target_command.setText("+".join(sorted_keys))

    def update_layout(self, _=None):
        width = 320

        # update layout
        idx = self.combobox_layout.currentIndex()
        self.controller_type = list(ControllerType)[idx]
        self.layout = get_layout(self.controller_type)
        self.button_mapper = self.layout.get_button_layout()
        self.d_pad_mapper = self.layout.get_d_pad_layout()

        if self.controller_type == ControllerType.XBOX:
            path = resources.XBOX_CONTROLLER_LAYOUT
        else:
            path = resources.PLAYSTATION_CONTROLLER_LAYOUT

        self.label_layout.setPixmap(
            QPixmap(str(path)).scaledToWidth(
                width, Qt.TransformationMode.SmoothTransformation
            )
        )

        # remove the input widgets of the previously selected layout
        while self.frame_buttons_layout.count() > 0:
            item = self.frame_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.var_buttons.clear()
        if self.button_group is not None:
            self.button_group.deleteLater()
        self.button_group = QButtonGroup(self)

        icon_size = (24, 24)
        self.gamepad_input_icons = {
            button: pil_to_qpixmap(image) if image is not None else None
            for button, image in self.layout.get_button_icons(
                icon_size=icon_size
            ).items()
        }

        self.frame_buttons_layout.addWidget(
            QLabel("Buttons:", self.frame_buttons), 0, 0
        )
        counter = 0
        buttons_per_column = 8
        for button in self.button_mapper.keys():
            check = QCheckBox(button, self.frame_buttons)
            icon = self.gamepad_input_icons.get(button)
            if icon is not None:
                check.setIcon(QIcon(icon))
                # checkboxes draw their icon at the small standard size unless
                # an explicit size is set
                check.setIconSize(QSize(*icon_size))
            self.frame_buttons_layout.addWidget(
                check,
                1 + counter % buttons_per_column,
                counter // buttons_per_column,
            )
            self.var_buttons[button] = check
            counter += 1

        for d_pad_index, d_pad_state in enumerate(self.d_pad_mapper.keys()):
            check = QRadioButton(d_pad_state, self.frame_buttons)
            icon = self.gamepad_input_icons.get(d_pad_state)
            if icon is not None:
                check.setIcon(QIcon(icon))
                check.setIconSize(QSize(*icon_size))
            self.button_group.addButton(check, d_pad_index)
            self.frame_buttons_layout.addWidget(
                check,
                1 + counter % buttons_per_column,
                counter // buttons_per_column,
            )
            counter += 1

    @staticmethod
    def __key_event_to_name(event: QKeyEvent) -> Optional[str]:
        special_keys = {
            Qt.Key.Key_Control: "ctrl",
            Qt.Key.Key_Alt: "alt",
            Qt.Key.Key_Shift: "shift",
            Qt.Key.Key_Meta: (
                "command" if get_os() == OperatingSystem.MAC else "win"
            ),
            Qt.Key.Key_Return: "return",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Escape: "escape",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_CapsLock: "capslock",
            Qt.Key.Key_NumLock: "numlock",
            Qt.Key.Key_ScrollLock: "scrolllock",
            Qt.Key.Key_Pause: "pause",
            Qt.Key.Key_Print: "print",
            Qt.Key.Key_VolumeDown: "volumedown",
            Qt.Key.Key_VolumeUp: "volumeup",
            Qt.Key.Key_VolumeMute: "volumemute",
        }
        key = event.key()
        if key in special_keys:
            return special_keys[key]
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
            return f"f{key - Qt.Key.Key_F1 + 1}"

        # fall back to the text of the key event (letters, digits, punctuation)
        text = event.text().lower()
        if text and ord(text[0]) >= 32:
            return text

        # e.g. when a modifier is held, the text can be a control character,
        # so fall back to the letter/digit of the key code
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z or Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(key).lower()
        return None
