import argparse
import json
import os
import subprocess
from pathlib import Path
import sys
import tkinter as tk
from tkinter import Menu, messagebox
from typing import List
import webbrowser
import requests
import platform
import pystray
from PIL import Image
import controller_companion
from controller_companion.app.utils import OperatingSystem, get_os, set_window_icon
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
        self.geometry("550x280")
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
        self.var_settings_minimize_on_close = tk.IntVar()
        self.var_settings_auto_start = tk.IntVar()
        self.var_settings_minimize_on_close.set(self.settings["minimize_on_exit"])
        self.var_settings_auto_start.set(self.settings["auto_start"])
        menu.add_cascade(label="Settings", menu=settings_)
        settings_.add_checkbutton(
            label="Minimize to system tray",
            onvalue=1,
            offvalue=0,
            variable=self.var_settings_minimize_on_close,
            command=self.save_settings,
        )

        if resources.is_frozen() and get_os() == OperatingSystem.WINDOWS:
            # only display auto start option if this is an executable
            settings_.add_checkbutton(
                label="Auto Start",
                onvalue=1,
                offvalue=0,
                variable=self.var_settings_auto_start,
                command=self.toggle_autostart,
            )

        # Help Menu
        help_ = Menu(menu, tearoff=0)
        menu.add_cascade(label="Help", menu=help_)
        help_.add_command(label="Check for Updates", command=self.check_for_updates)
        help_.add_command(label="About", command=lambda: AboutScreen(self))

        # ---------------------------------------------------------------------------- #

        tk.Label(self, text="Defined Mappings").pack(fill=tk.X)
        self.treeview = PopupMenuTreeview(
            self,
            columns=("shortcut", "target"),
            height=7,
            menu_actions={
                "delete mapping(s)": lambda: self.delete_action(),
            },
        )
        self.treeview.heading("#0", text="Name")
        self.treeview.heading("shortcut", text="Shortcut")
        self.treeview.heading("target", text="Target")
        for mapping in self.defined_actions:
            self.treeview.insert(
                "",
                tk.END,
                text=mapping.name,
                values=(
                    mapping.get_shortcut_string(),
                    mapping.target,
                ),
            )
        self.treeview.pack(expand=True, fill=tk.BOTH)

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
            debug=self.settings.get("debug", 0) == 1,
            controller_callback=self.update_controller_ui,
            disabled_controllers=self.settings["disabled_controllers"],
        )
        # ---------------------------------------------------------------------------- #

        if launch_minimized:
            # use after to make initial controller connected callback work
            # otherwise, we would get a RuntimeError: main thread is not in main loop
            # when executing the controller_callback above.
            self.after(100, self.minimize_to_tray, [True])

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
            self.treeview.insert(
                "",
                tk.END,
                text=result.name,
                values=(
                    result.active_controller_buttons,
                    result.target,
                ),
                image=tk.PhotoImage(file=resources.APP_ICON_PNG),
            )
            self.save_settings()

    def delete_action(self, _=None):
        selection = self.treeview.selection()
        for item in selection:
            delete_idx = self.treeview.index(item)
            self.treeview.delete(item)
            self.defined_actions.pop(delete_idx)

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
            "minimize_on_exit": 1,
            "auto_start": 0,
            "debug": 0,
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
                "auto_start": self.var_settings_auto_start.get(),
                "actions": [item.to_dict() for item in self.defined_actions],
            }
        )
        self.settings_file.parent.mkdir(exist_ok=True, parents=True)
        self.settings_file.write_text(json.dumps(self.settings, indent=4))

        logger.debug(f"Saved settings to: {self.settings_file}")

    def toggle_autostart(self):
        executable = resources.get_executable_path()
        autostart = self.var_settings_auto_start.get() == 1

        if platform.system() == "Windows":
            bat_file = Path(
                Path.home(),
                "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/controller_companion.bat",
            )
            if autostart:
                bat_file.write_text(f'start "" "{executable.absolute()}" "-m"')
            else:
                bat_file.unlink(missing_ok=True)

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
    app = ControllerCompanion(launch_minimized=minimized)
    app.mainloop()


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
