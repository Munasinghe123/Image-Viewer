import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from config import *
from dbOperations.database import ImageDB
from utils.find_logo import find_logo
from views.search_window import LineSearchWindow, PoleSearchWindow
import subprocess
from dbOperations.sync_images import sync_images as run_sync

BG_MAIN = "#FFFFFF" 
THUMBNAIL_SIZE = (1000, 640)

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

# ---------------- Main Window ----------------
class MainWindow(tk.Tk):
    
    # ui action button's functions
    def on_clean_duplicates(self):
        ans = messagebox.askyesno(
            "Clean duplicates",
            "This will remove duplicate DB rows having the same file_hash (keeps first). Continue?"
        )
        if not ans:
            return
        removed = self.db.clean_duplicate_file_hashs()
        messagebox.showinfo("Clean Duplicates", f"Removed {removed} duplicate rows (if any).")
        self.status_var.set(f"Removed {removed} duplicates.")

    # ui action button's functions
    def sync_images(self):

        try:
            run_sync()
            print("sync images function fired")
            messagebox.showinfo("Sync Complete", "Images synced from PostgreSQL.")
        except Exception as e:
            messagebox.showerror("Sync Error", str(e))
            
    
    def open_line_search(self):
        LineSearchWindow(self, self.db)

    def open_pole_search(self):
        PoleSearchWindow(self, self.db)
    
    def __init__(self):
        super().__init__()
        self.title("LECO — Drone Image Viewer")
        self.configure(bg=BG_MAIN)
        self.center_window(940, 420)
        self.db = ImageDB()
        self.logo_path = find_logo()

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Accent.TButton", background=ACCENT, foreground="white", font=FONT_NORMAL, padding=8)
        style.map("Accent.TButton", background=[("active", ACCENT_LIGHT)])

        # Header
        header = tk.Frame(self, bg=ACCENT, height=110)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        left_h = tk.Frame(header, bg=ACCENT)
        left_h.pack(side=tk.LEFT, padx=14, pady=6)
        if self.logo_path:
            try:
                logo_img = Image.open(self.logo_path)
                logo_img.thumbnail((96,96), Image.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_lbl = tk.Label(left_h, image=self.logo_photo, bg=ACCENT)
                logo_lbl.pack(side=tk.LEFT)
            except Exception:
                pass
        title_lbl = tk.Label(header, text="LECO DRONE IMAGE VIEWER", font=FONT_TITLE, bg=ACCENT, fg="white")
        title_lbl.pack(side=tk.LEFT, padx=(8,0))
        sub_lbl = tk.Label(header, text="Visual Inspection — Line & Pole Images", font=FONT_SMALL, bg=ACCENT, fg="#EBDFFF")
        sub_lbl.pack(side=tk.LEFT, padx=(12,0))

        # Main content area
        content = tk.Frame(self, bg=BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=18, pady=12)

        # Cards container
        cards = tk.Frame(content, bg=BG_MAIN)
        cards.pack(fill=tk.X, pady=(10,20))

        # Wide card buttons
        btn_line = tk.Button(cards, text="➤ View Line Section", font=FONT_CARD, bg=ACCENT, fg="white", activebackground=ACCENT_LIGHT,
                             relief=tk.FLAT, command=self.open_line_search)
        btn_line.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=8, ipadx=8, ipady=22)

        btn_pole = tk.Button(cards, text="➤ View Around Pole", font=FONT_CARD, bg=ACCENT, fg="white", activebackground=ACCENT_LIGHT,
                             relief=tk.FLAT, command=self.open_pole_search)
        btn_pole.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=8, ipadx=8, ipady=22)

        # Bottom controls row
        bottom = tk.Frame(content, bg=BG_MAIN)
        bottom.pack(fill=tk.X, pady=(6,0))
        leftb = tk.Frame(bottom, bg=BG_MAIN)
        leftb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        rightb = tk.Frame(bottom, bg=BG_MAIN)
        rightb.pack(side=tk.RIGHT)
        
        # ui action buttons
        ttk.Button(leftb, text="Sync Images", style="Accent.TButton",  command=self.sync_images).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(leftb, text="Clean Duplicates", style="Accent.TButton", command=self.on_clean_duplicates).pack(side=tk.LEFT, padx=6, pady=6)

        ttk.Button(rightb, text="Exit", style="Accent.TButton", command=self.destroy).pack(side=tk.RIGHT, padx=6, pady=6)

        # status bar
        self.status_var = tk.StringVar(value="Ready")
        status = tk.Label(self, textvariable=self.status_var, bg="#F7F2FF", fg=MUTED, font=FONT_SMALL, anchor="w")
        status.pack(fill=tk.X, side=tk.BOTTOM)

        self._last_import_folder = None
        self._import_lock = False

    def center_window(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        x = (sw - w) // 2; y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    

   