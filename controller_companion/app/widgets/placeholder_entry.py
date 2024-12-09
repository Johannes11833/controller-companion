import tkinter as tk


class PlaceholderEntry(tk.Entry):

    def __init__(self, master=None, placeholder: str = "", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.insert(0, self.placeholder)
        self.configure(foreground="gray")
        self.bind("<FocusIn>", self.__on_entry_click)
        self.bind("<FocusOut>", self.__on_focus_out)
        self.focused = False

    def __on_entry_click(self, _=None):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.configure(foreground="black")
        self.focused = True

    def __on_focus_out(self, _=None):
        if self.get() == "":
            self.insert(0, self.placeholder)
            self.configure(foreground="gray")
        self.focused = False

    def set_placeholder(self, placeholder: str):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.insert(0, placeholder)

        self.placeholder = placeholder

    def set_text(self, text: str):
        self.delete(0, tk.END)
        self.insert(0, text)
        self.__on_entry_click()
