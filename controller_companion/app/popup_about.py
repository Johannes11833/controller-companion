import tkinter as tk
from tkinter import ttk
import webbrowser
from PIL import Image, ImageTk

import controller_companion
from controller_companion.app import resources
from controller_companion.app.utils import set_window_icon


class AboutScreen(tk.Toplevel):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("About")
        set_window_icon(self)
        self.resizable(False, False)

        frame1 = tk.Frame(master=self, width=50, padx=10, pady=10)
        frame1.pack(fill=tk.Y, side=tk.LEFT)
        frame2 = tk.Frame(master=self, padx=10, pady=10)
        frame2.pack(fill=tk.Y, side=tk.LEFT)

        # Display it within a label.
        image = ImageTk.PhotoImage(
            Image.open(resources.APP_ICON_PNG).resize(
                (50, 50),
            )
        )
        label = ttk.Label(frame1, image=image, width=50)
        label.pack(side=tk.LEFT)

        tk.Label(
            frame2,
            text=f"{controller_companion.APP_NAME} {controller_companion.VERSION}",
            font=("Helvetica", 12, "bold"),
        ).pack(side=tk.TOP, anchor="w")
        tk.Label(frame2, text=f"Made by Johannes Gundlach").pack(
            side=tk.TOP, anchor="w"
        )
        link = tk.Label(
            frame2,
            text="https://github.com/Johannes11833/controller-companion",
            fg="blue",
            cursor="hand2",
        )
        link.pack(side=tk.TOP, anchor="w")
        link.bind("<Button-1>", lambda _: self.callback(link.cget("text")))

        self.mainloop()

    def callback(self, url):
        webbrowser.open_new_tab(
            url,
        )
