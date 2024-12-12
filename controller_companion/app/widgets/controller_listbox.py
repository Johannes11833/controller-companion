import tkinter
from tkinter import ttk
from typing import Callable, Dict


class PopupMenuListbox(tkinter.Listbox):

    def __init__(
        self,
        parent,
        menu_actions: Dict[str, Callable[[None], None]] = None,
        *args,
        **kwargs
    ):
        tkinter.Listbox.__init__(self, parent, *args, **kwargs)

        if not menu_actions:
            menu_actions = {}

        self.popup_menu = tkinter.Menu(self, tearoff=0)
        for action_name, callback in menu_actions.items():
            self.popup_menu.add_command(label=action_name, command=callback)
        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()


class PopupMenuTreeview(ttk.Treeview):

    def __init__(
        self,
        parent,
        menu_actions: Dict[str, Callable[[None], None]] = None,
        *args,
        **kwargs
    ):
        ttk.Treeview.__init__(self, parent, *args, **kwargs)

        if not menu_actions:
            menu_actions = {}

        self.popup_menu = tkinter.Menu(self, tearoff=0)
        for action_name, callback in menu_actions.items():
            self.popup_menu.add_command(label=action_name, command=callback)
        self.bind("<Button-3>", self.popup)  # Button-2 on Aqua

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()
