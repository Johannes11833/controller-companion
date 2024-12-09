import tkinter as tk
from tkinter import (
    Checkbutton,
    Event,
    IntVar,
    Radiobutton,
    StringVar,
    ttk,
)
from tkinter import messagebox
from controller_companion import logger

from controller_companion.mapping import Mapping, ActionType
from controller_companion.app import resources
from controller_companion.app.widgets.placeholder_entry import PlaceholderEntry
from controller_companion.controller_state import (
    ControllerState,
    button_mapper,
    d_pad_mapper,
)


class CreateActionPopup(tk.Toplevel):
    """modal window requires a master"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.iconbitmap(resources.APP_ICON_ICO)

        self.var_buttons = {}
        self.var_d_pad = IntVar()
        self.var_action_type = StringVar()
        self.var_command = StringVar()
        self.result = None

        frame_inputs = ttk.LabelFrame(
            master=self, height=50, text="Controller Shortcut"
        )
        frame_inputs.pack(fill=tk.X, side=tk.TOP, expand=True, padx=10, pady=(10, 5))

        frame_buttons = tk.Frame(master=frame_inputs, height=50, padx=5)
        frame_buttons.pack(fill=tk.X, side=tk.TOP, expand=True)

        frame_d_pad = tk.Frame(master=frame_inputs, height=50, padx=5)
        frame_d_pad.pack(fill=tk.X, side=tk.TOP, expand=True)

        frame_action = ttk.LabelFrame(
            master=self, height=50, text="Action", padding=(0, 5, 5, 5)
        )
        frame_action.pack(fill=tk.X, side=tk.TOP, expand=True, padx=10, pady=5)

        frame_save = ttk.LabelFrame(
            master=self, height=50, text="Save", padding=(0, 5, 0, 5)
        )
        frame_save.pack(fill=tk.X, side=tk.TOP, expand=True, padx=10, pady=(5, 10))

        tk.Label(frame_buttons, text="Buttons", anchor="w").grid(
            row=0, column=0, sticky="W"
        )
        for column, button in enumerate(button_mapper.keys()):
            self.var_buttons[button] = IntVar()
            check = Checkbutton(
                frame_buttons,
                text=button,
                variable=self.var_buttons[button],
                anchor="w",
            )
            check.grid(row=1, column=column)

        tk.Label(frame_d_pad, text="D-Pad", anchor="w").grid(
            row=0, column=0, sticky="W"
        )
        self.var_d_pad.set(-1)
        for column, d_pad_state in enumerate(d_pad_mapper.keys()):
            check = Radiobutton(
                frame_d_pad,
                text=d_pad_state,
                variable=self.var_d_pad,
                value=column,
                anchor="w",
            )
            check.grid(row=1, column=column)

        tk.Label(
            frame_action,
            text="Type:",
            padx=5,
        ).grid(row=1, column=0)
        combo = ttk.Combobox(
            frame_action,
            values=[e.value for e in ActionType],
            state="readonly",
            textvariable=self.var_action_type,
        )
        combo.bind("<<ComboboxSelected>>", self.action_type_changed)
        self.var_action_type.set(ActionType.TASK_KILL_BY_NAME.value)
        combo.grid(row=1, column=1)

        tk.Label(
            frame_action,
            text="Target:",
            padx=5,
        ).grid(row=1, column=2)
        self.entry_target_command = PlaceholderEntry(
            frame_action,
            textvariable=self.var_command,
        )
        frame_action.columnconfigure(3, weight=1)
        self.entry_target_command.grid(row=1, column=3, sticky="nsew")

        save_label = tk.Label(frame_save, text="Name:", padx=5)
        save_label.grid(row=0, column=0, padx=5)
        self.entry_name = PlaceholderEntry(
            frame_save,
            placeholder="name of the shortcut",
            width=30,
        )
        self.entry_name.grid(row=0, column=1, padx=5)
        tk.Button(frame_save, text="Save", command=self.on_save).grid(
            row=0, column=2, padx=5
        )
        self.action_type_changed()

        self.pressed_keys = set()
        self.bind("<KeyPress>", self.on_key_press)

        # The following commands keep the popup on top.
        # Remove these if you want a program with 2 responding windows.
        # These commands must be at the end of __init__
        self.transient(master)  # set to be on top of the main window
        self.grab_set()  # hijack all commands from the master (clicks on the main window are ignored)
        master.wait_window(
            self
        )  # pause anything on the main window until this one closes

    def on_save(self):

        selected_buttons = []
        target = self.var_command.get()
        name = self.entry_name.get()

        for btn, var in self.var_buttons.items():
            if var.get() == 1:
                selected_buttons.append(button_mapper[btn])

        selected_d_pad_index = self.var_d_pad.get()
        if selected_d_pad_index == -1:
            d_pad_action = (0, 0)
        else:
            d_pad_action = list(d_pad_mapper.values())[selected_d_pad_index]

        error = None
        if len(selected_buttons) == 0 and d_pad_action == (0, 0):
            error = "No controller shortcut was selected!"
        elif target == "" or target == self.entry_target_command.placeholder:
            error = "No target command was specified!"
        elif name == "" or name == self.entry_name.placeholder:
            error = "The name of the shortcut was not set!"
        if error:
            messagebox.showerror("Error", error)
            return

        state = ControllerState(
            active_buttons=selected_buttons, d_pad_state=d_pad_action
        )  # save the return value to an instance variable.
        self.result = Mapping(
            action_type=ActionType(self.var_action_type.get()),
            target=target,
            controller_state=state,
            name=name,
        )

        self.destroy()

    def action_type_changed(self, _=None):
        self.action_type = ActionType(self.var_action_type.get())

        if self.action_type == ActionType.TASK_KILL_BY_NAME:
            self.entry_target_command.set_placeholder(
                "name of task to kill (e.g. explorer.exe)"
            )
        elif self.action_type == ActionType.KEYBOARD_SHORTCUT:
            self.pressed_keys.clear()
            self.entry_target_command.set_placeholder("click here, then enter shortcut")
        else:
            self.entry_target_command.set_placeholder(
                "custom arbitrary console command"
            )

    def on_key_press(self, event: Event):
        valid_keys = Mapping.get_valid_keyboard_keys()
        if self.action_type == ActionType.KEYBOARD_SHORTCUT:
            key = event.char if event.char in valid_keys else event.keysym
            key = (
                key.lower()
                .replace("_l", "")
                .replace("_r", "")
                .replace("control", "ctrl")
                .replace("prior", "pageup")
                .replace("next", "pagedown")
            )
            # XF86AudioLowerVolume
            if "audiolower" in key:
                key = "volumedown"
            # XF86AudioRaiseVolume
            elif "audioraise" in key:
                key = "volumeup"
            # XF86AudioMute
            elif "audiomute" in key:
                key = "volumemute"
            elif key == "\t":
                key = "tab"

            if not key in valid_keys:
                logger.warning(f"Unknown key event {event}")
                return

            if self.entry_target_command.focused:
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

                self.entry_target_command.set_text("+".join(sorted_keys))
                return "break"
