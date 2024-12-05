import tkinter as tk
from tkinter import (
    Checkbutton,
    IntVar,
    Radiobutton,
    StringVar,
    ttk,
)

from controller_companion.action import Action, ActionType
from controller_companion.app import resources
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
        self.var_action_name = StringVar()
        self.result = None

        frame1 = tk.Frame(master=self, height=50, padx=10, pady=10)
        frame1.pack(fill=tk.X, side=tk.TOP, expand=True)

        frame2 = tk.Frame(master=self, height=50, padx=10, pady=10)
        frame2.pack(fill=tk.X, side=tk.TOP, expand=True)

        frame3 = tk.Frame(master=self, height=50, padx=10, pady=10)
        frame3.pack(fill=tk.X, side=tk.TOP, expand=True)

        frame4 = tk.Frame(master=self, height=50, bg="gray", padx=10, pady=10)
        frame4.pack(fill=tk.X, side=tk.TOP, expand=True)

        tk.Label(frame1, text="Buttons", anchor="w").grid(row=0, column=0, sticky="W")
        for column, button in enumerate(button_mapper.keys()):
            self.var_buttons[button] = IntVar()
            check = Checkbutton(frame1, text=button, variable=self.var_buttons[button])
            check.grid(row=1, column=column)

        tk.Label(frame2, text="D-Pad", anchor="w").grid(row=0, column=0, sticky="W")
        self.var_d_pad.set(-1)
        for column, d_pad_state in enumerate(d_pad_mapper.keys()):
            check = Radiobutton(
                frame2,
                text=d_pad_state,
                variable=self.var_d_pad,
                value=column,
                anchor="w",
            )
            check.grid(row=1, column=column)

        tk.Label(frame3, text="Action").grid(row=0, column=0, sticky="W")
        tk.Label(
            frame3,
            text="Type",
            padx=5,
        ).grid(row=1, column=0)
        combo = ttk.Combobox(
            frame3,
            values=[e.value for e in ActionType],
            state="readonly",
            textvariable=self.var_action_type,
        )
        self.var_action_type.set(ActionType.TASK_KILL_BY_NAME.value)
        combo.grid(row=1, column=1)

        tk.Label(
            frame3,
            text="Command to execute",
            padx=5,
        ).grid(row=1, column=2)
        tk.Entry(frame3, width=30, textvariable=self.var_command).grid(row=1, column=3)
        self.var_command.set("explorer.exe")

        tk.Label(frame4, text="Action Name", padx=5).grid(row=0, column=0, padx=5)
        self.var_action_name.set("Hello world")
        tk.Entry(frame4, width=30, textvariable=self.var_action_name).grid(
            row=0, column=1, padx=5
        )
        tk.Button(frame4, text="Save Mapping", command=self.on_save).grid(
            row=0, column=2, padx=5
        )

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

        for btn, var in self.var_buttons.items():
            if var.get() == 1:
                selected_buttons.append(button_mapper[btn])

        selected_d_pad_index = self.var_d_pad.get()
        if selected_d_pad_index == -1:
            d_pad_action = (0, 0)
        else:
            d_pad_action = list(d_pad_mapper.values())[selected_d_pad_index]

        state = ControllerState(
            active_buttons=selected_buttons, d_pad_state=d_pad_action
        )  # save the return value to an instance variable.
        self.result = Action(
            action_type=ActionType(self.var_action_type.get()),
            target=self.var_command.get(),
            controller_state=state,
            name=self.var_action_name.get(),
        )

        self.destroy()
