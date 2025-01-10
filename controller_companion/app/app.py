import argparse
import json
import os
import signal
import subprocess
from pathlib import Path
import sys
import tkinter as tk
from tkinter import Menu, messagebox
from tkinter import ttk
from typing import List
import webbrowser
import requests
import pystray
from PIL import Image, ImageTk
import controller_companion
from controller_companion.app.autostart import (
    autostart_supported,
    get_autostart_enabled,
    set_auto_start,
)
from controller_companion.app.controller_layouts import ControllerType, get_layout
from controller_companion.app.utils import (
    OperatingSystem,
    combine_images_horizontally,
    get_os,
    set_window_icon,
)
from controller_companion.app.widgets.controller_listbox import (
    PopupMenuListbox,
    PopupMenuTreeview,
)
from controller_companion.controller import Controller
from controller_companion.logs import logger
from controller_companion.mapping import Mapping
from controller_companion.app import resources
from controller_companion.app.popup_about import AboutScreen
from controller_companion.app.popup_create_action import CreateActionPopup
import controller_companion.controller_observer as controller_observer


class ControllerCompanion(tk.Tk):
    def __init__(self, launch_minimized=False):
        super().__init__(className=controller_companion.APP_NAME)
        self.title(controller_companion.APP_NAME)

        set_window_icon(self)
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.settings_file = controller_companion.CONFIG_PATH

        # load settings
        self.settings = self.load_settings()

        self.controllers: List[Controller] = []

        # --------------------------------- add menu --------------------------------- #
        menu = Menu(self)
        self.config(menu=menu)

        # File Menu
        filemenu_ = Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=filemenu_)
        filemenu_.add_command(
            label="Add mapping", command=self.open_add_actions, accelerator="Ctrl+N"
        )
        filemenu_.add_command(
            label="Delete mapping",
            command=self.delete_action,
            accelerator="Del",
        )
        filemenu_.add_command(
            label="Open config file",
            command=self.open_config,
            accelerator="Ctrl+C",
        )
        self.bind_all("<Delete>", self.delete_action)
        self.bind_all("<Control-n>", self.open_add_actions)
        self.bind_all("<Control-q>", self.quit_window)
        self.bind_all("<Control-c>", lambda _: self.open_config())
        filemenu_.add_separator()
        filemenu_.add_command(
            label="Quit",
            command=self.quit_window,
            accelerator="Ctrl+Q",
        )

        # Settings Menu
        settings_ = Menu(menu, tearoff=0)
        self.var_settings_minimize_on_close = tk.BooleanVar(
            value=self.settings["minimize_on_exit"]
        )
        self.var_settings_auto_start = tk.BooleanVar(value=get_autostart_enabled())
        menu.add_cascade(label="Settings", menu=settings_)
        settings_.add_checkbutton(
            label="Minimize to system tray",
            variable=self.var_settings_minimize_on_close,
            command=self.save_settings,
        )

        if (
            resources.is_frozen() and autostart_supported()
        ):  # only display auto start option if this is an executable
            settings_.add_checkbutton(
                label="Auto Start",
                variable=self.var_settings_auto_start,
                command=self.toggle_autostart,
            )

        # Help Menu
        help_ = Menu(menu, tearoff=0)
        menu.add_cascade(label="Help", menu=help_)
        help_.add_command(label="Check for Updates", command=self.check_for_updates)
        help_.add_command(label="About", command=lambda: AboutScreen(self))

        # ---------------------------------------------------------------------------- #
        self.rowheight = 30
        tk.Label(self, text="Defined Mappings").pack(fill=tk.X)
        s = ttk.Style()
        s.configure("Treeview", rowheight=self.rowheight)
        self.treeview = PopupMenuTreeview(
            self,
            columns=("name", "target"),
            height=7,
            menu_actions={
                "delete mapping(s)": lambda: self.delete_action(),
            },
        )
        self.treeview.pack(expand=True, fill=tk.BOTH)
        self.treeview.heading("#0", text="Shortcut")
        self.treeview.heading("name", text="Name")
        self.treeview.heading("target", text="Target")
        self.update_mappings_ui()

        # --------------------------- connected controllers -------------------------- #

        tk.Label(self, text="Connected Controllers").pack(fill=tk.X)
        self.var_connected_controllers = tk.Variable()
        self.listbox_controllers = PopupMenuListbox(
            self,
            listvariable=self.var_connected_controllers,
            selectmode=tk.EXTENDED,
            menu_actions={"toggle on/off": self.toggle_controller},
        )
        self.listbox_controllers.pack(expand=True, fill=tk.BOTH)

        # -------------------- start the joystick observer thread -------------------- #
        self.observer = controller_observer.ControllerObserver()
        self.observer.start_detached(
            defined_actions=self.defined_actions,
            debug=self.settings.get("debug", False),
            controller_callback=self.update_controller_ui,
            disabled_controllers=self.settings["disabled_controllers"],
        )
        # ---------------------------------------------------------------------------- #

        if launch_minimized:
            # use after to make initial controller connected callback work
            # otherwise, we would get a RuntimeError: main thread is not in main loop
            # when executing the controller_callback above.
            self.after(100, self.minimize_to_tray, [True])

    def update_mappings_ui(self):
        self.treeview.delete(*self.treeview.get_children())
        icon_size = (self.rowheight - 5, self.rowheight - 5)
        self.mapping_treeview_icons = []
        layout_icons = {
            controller: get_layout(controller).get_button_icons(icon_size=icon_size)
            for controller in ControllerType
        }
        max_width_shortcut = 0
        for mapping in self.defined_actions:
            plus_icon = Image.open(resources.PLUS_ICON).resize(
                (self.rowheight // 3, self.rowheight // 3)
            )
            icons = []
            for btn in mapping.active_controller_buttons:
                icons.append(layout_icons[mapping.controller_type][btn])
                icons.append(plus_icon)
            icons.pop()
            shortcut_icon = ImageTk.PhotoImage(
                combine_images_horizontally(images=icons, height=self.rowheight)
            )
            max_width_shortcut = max(max_width_shortcut, shortcut_icon.width())
            self.treeview.insert(
                "",
                tk.END,
                text="",
                values=(
                    mapping.name,
                    mapping.target,
                ),
                image=shortcut_icon,
            )
            self.mapping_treeview_icons.append(shortcut_icon)
        # make sure the width of the first column is large enough to fit the shortcut image
        # an offset is added to account for the treeview's indicator at the very left
        self.treeview.column("#0", minwidth=max_width_shortcut + 30)

    def minimize_to_tray(self, is_launch: bool = False):
        if self.var_settings_minimize_on_close.get() == 0 and not is_launch:
            # exit the app instead as minimize to system tray is disabled
            self.quit_window()
            return

        self.withdraw()
        if get_os() == OperatingSystem.LINUX:
            # on linux this will look very distorted on resolutions >16x16
            image = Image.open(resources.APP_ICON_PNG_TRAY_16)
        else:
            image = Image.open(resources.APP_ICON_PNG_TRAY_32)
        menu = (
            pystray.MenuItem("Show", self.show_window, default=True),
            pystray.MenuItem("Quit", self.quit_window_from_icon),
        )
        icon = pystray.Icon(
            "name",
            image,
            controller_companion.APP_NAME,
            menu,
        )
        icon.run()

    def quit_window_from_icon(self, icon=None):
        if icon is not None:
            icon.stop()
        self.quit_window()

    def quit_window(self, _=None):
        self.observer.stop()
        self.destroy()

    def show_window(self, icon):
        icon.stop()
        self.after(0, self.deiconify)

    def open_add_actions(self, _=None):
        p = CreateActionPopup(self)
        result = p.result
        if result is not None:
            self.defined_actions.append(result)
            self.update_mappings_ui()
            self.save_settings()

    def delete_action(self, _=None):
        selection = self.treeview.selection()
        for item in selection:
            delete_idx = self.treeview.index(item)
            self.defined_actions.pop(delete_idx)
        self.update_mappings_ui()

        if len(selection) > 0:
            self.save_settings()

    def update_controller_ui(self, controllers: List[Controller]):
        self.controllers = controllers

        controllers_str = []
        for i, c in enumerate(controllers):
            item = f"       Controller {i+1}: {c.name}"

            if c.guid in self.settings["disabled_controllers"]:
                item += "  [disabled]"

            controllers_str.append(item)
        self.var_connected_controllers.set(controllers_str)

    def toggle_controller(self, _=None):
        disabled_controllers = self.settings["disabled_controllers"]
        selected_idcs = self.listbox_controllers.curselection()
        selected_guids = set([self.controllers[i].guid for i in selected_idcs])

        # selected controllers that are currently enabled/ disabled
        selected_disabled_guids = set(disabled_controllers) & selected_guids
        selected_enabled_guids = selected_guids - selected_disabled_guids

        # toggle: disabled controllers ---> enabled and vice versa
        new_disabled = list(
            (set(disabled_controllers) | selected_enabled_guids)
            - selected_disabled_guids
        )
        disabled_controllers.clear()
        disabled_controllers.extend(new_disabled)

        self.update_controller_ui(self.controllers)
        self.save_settings()

    def load_settings(self):
        settings = {
            "minimize_on_exit": True,
            "debug": False,
            "disabled_controllers": [],
        }

        if self.settings_file.is_file():
            try:
                settings.update(json.loads(self.settings_file.read_text()))
                self.defined_actions = [
                    Mapping.from_dict(d) for d in settings["actions"]
                ]
            except Exception as e:
                messagebox.showerror(
                    "Config File Error",
                    f"Failed to load the config file.\nError message: {str(e)}",
                )
                self.open_config()
                self.quit_window()
        else:
            self.defined_actions = []

        return settings

    def open_config(self):
        if not self.settings_file.is_file():
            self.save_settings()

        if sys.platform == "win32":
            os.startfile(self.settings_file)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, self.settings_file])

    def save_settings(self):
        # update the settings dict
        self.settings.update(
            {
                "minimize_on_exit": self.var_settings_minimize_on_close.get(),
                "actions": [item.to_dict() for item in self.defined_actions],
            }
        )
        self.settings_file.parent.mkdir(exist_ok=True, parents=True)
        self.settings_file.write_text(json.dumps(self.settings, indent=4))

        logger.debug(f"Saved settings to: {self.settings_file}")

    def toggle_autostart(self):
        set_auto_start(enable=self.var_settings_auto_start.get())
        self.save_settings()

    def check_for_updates(self):
        response = requests.get(
            "https://api.github.com/repos/Johannes11833/controller-companion/releases/latest"
        )
        latest_version = response.json()["name"]
        installed_version = controller_companion.VERSION

        if latest_version == installed_version:
            messagebox.showinfo(
                "Up to date",
                f"The latest version of {controller_companion.APP_NAME} is installed.",
                parent=self,
            )
        else:
            url = (
                "https://github.com/Johannes11833/controller-companion/releases/latest"
            )
            logger.info(
                f"A new update is available: {installed_version} -> {latest_version}. URL: {url}"
            )
            open_website = messagebox.askyesno(
                f"Update available: {latest_version}",
                f"A new update is available for {controller_companion.APP_NAME}. Go to download page now?",
                parent=self,
            )
            if open_website:
                webbrowser.open_new_tab(
                    url,
                )


def launch_app(minimized: bool = False):
    pid_file = Path(controller_companion.PID_PATH)
    if pid_file.is_file():
        pid_running = int(pid_file.read_text())
        try:
            # kill the running instance
            # (might fail if it is not running but .pid file exists)
            os.kill(pid_running, signal.SIGKILL)
        except OSError:
            logger.warning("Failed to kill running instance!")
    pid_current = os.getpid()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid_current))

    # launch the app
    app = ControllerCompanion(launch_minimized=minimized)
    app.mainloop()

    # remove the pid file if the app is exited by the user
    pid_file.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Lauch the {controller_companion.APP_NAME} UI App."
    )
    parser.add_argument(
        "-m",
        "--minimized",
        help="Launch minimized.",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()

    launch_app(minimized=args.minimized)
