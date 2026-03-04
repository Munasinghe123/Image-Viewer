import tkinter as tk
from tkinter import ttk, messagebox

from config import *
from database import ImageDB
from .viewer_window import ViewerWindow

BG_MAIN = "#FFFFFF" 
# Fonts
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_CARD = ("Segoe UI", 14, "bold")
FONT_NORMAL = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)

# Colors (white + purple scheme)
BG_MAIN = "#FFFFFF"            # overall background (white)
BG_PANEL = "#F1E8FF"           # soft lavender panel
ACCENT = "#5A2E9D"             # deep purple (primary accent)
ACCENT_LIGHT = "#7F4FC3"       # lighter purple
TEXT_DARK = "#222222"          # dark text
MUTED = "#777777"              # muted text
CANVAS_BG = "#FBF9FF"          # canvas background (very light lavender)
MARKUP_COLOR_DEFAULT = "#FF2E63"
MARKUP_WIDTH_DEFAULT = 4

# ---------------- Line / Pole Search Windows ----------------
class LineSearchWindow(tk.Toplevel):
    def __init__(self, master, db: ImageDB):
        super().__init__(master)
        self.title("View Line Section")
        self.configure(bg=BG_MAIN)
        self.center_window(520, 220)
        self.db = db
        frame = tk.Frame(self, bg=BG_MAIN, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Start Pole:", font=FONT_NORMAL, bg=BG_PANEL, fg=TEXT_DARK).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.start_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.start_var, width=20).grid(row=0, column=1, padx=6, pady=6)

        tk.Label(frame, text="End Pole:", font=FONT_NORMAL, bg=BG_PANEL, fg=TEXT_DARK).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.end_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.end_var, width=20).grid(row=1, column=1, padx=6, pady=6)

        btn_frame = tk.Frame(frame, bg=BG_MAIN)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(12,0))
        ttk.Button(btn_frame, text="Search", style="Accent.TButton", command=self.do_search).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Close", style="Accent.TButton", command=self.destroy).pack(side=tk.LEFT, padx=6)

    def center_window(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        x = (sw - w) // 2; y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def do_search(self):
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        if not start or not end:
            messagebox.showerror("Input Error", "Please enter both Start Pole and End Pole.")
            return
        images = self.db.get_images_between(start, end)
        if not images:
            messagebox.showinfo("No Results", f"No images found for {start} → {end}.")
            return
        ViewerWindow(self, images, title=f"LECO Viewer — {start} → {end}")

class PoleSearchWindow(tk.Toplevel):
    def __init__(self, master, db: ImageDB):
        super().__init__(master)
        self.title("View Around Pole")
        self.configure(bg=BG_MAIN)
        self.center_window(520, 180)
        self.db = db
        frame = tk.Frame(self, bg=BG_MAIN, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Pole ID:", font=FONT_NORMAL, bg=BG_PANEL, fg=TEXT_DARK).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.pole_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.pole_var, width=20).grid(row=0, column=1, padx=6, pady=6)

        btn_frame = tk.Frame(frame, bg=BG_MAIN)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(12,0))
        ttk.Button(btn_frame, text="Search", style="Accent.TButton", command=self.do_search).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Close", style="Accent.TButton", command=self.destroy).pack(side=tk.LEFT, padx=6)

    def center_window(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        x = (sw - w) // 2; y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def do_search(self):
        pole = self.pole_var.get().strip()
        if not pole:
            messagebox.showerror("Input Error", "Please enter a Pole ID.")
            return
        images = self.db.get_images_around_pole(pole)
        if not images:
            messagebox.showinfo("No Results", f"No images found around pole: {pole}")
            return
        ViewerWindow(self, images, title=f"LECO Viewer — Around Pole {pole}")
