import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from config import *
from database import ImageDB
from utils.find_logo import find_logo
from views.search_window import LineSearchWindow, PoleSearchWindow
import subprocess

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
    
    def sync_images(self):

        try:
            subprocess.run(["python", "sync_images.py"], check=True)
            print("sync images function fired")
            messagebox.showinfo("Sync Complete", "Images synced from PostgreSQL.")
        except Exception as e:
            messagebox.showerror("Sync Error", str(e))
    
    def __init__(self):
        super().__init__()
        self.title("LECO — Drone Image Viewer")
        self.configure(bg=BG_MAIN)
        self.center_window(940, 420)
        self.db = ImageDB()
        print(find_logo)
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

        ttk.Button(leftb, text="Sync Images", style="Accent.TButton",  command=self.sync_images).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(leftb, text="Load DB", style="Accent.TButton", command=self.on_load_db).pack(side=tk.LEFT, padx=6, pady=6)
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

    def open_line_search(self):
        LineSearchWindow(self, self.db)

    def open_pole_search(self):
        PoleSearchWindow(self, self.db)

    def on_load_db(self):
        new = filedialog.askopenfilename(title="Select images.db file",
                                         filetypes=[("SQLite DB","*.db;*.sqlite;*.sqlite3"),("All files","*.*")])
        if new:
            self.db.db_path = new
            self.db.ensure_table()
            messagebox.showinfo("DB Loaded", f"Database set to:\n{new}")
            self.status_var.set(f"DB: {os.path.basename(new)}")

    def on_import_folder(self):
       
        if self._import_lock:
            messagebox.showinfo("Import in progress", "An import is already running. Please wait.")
            return

        root = filedialog.askdirectory(title="Select root folder containing pole / line folders")
        if not root:
            return

        self._last_import_folder = root
        self._import_lock = True
        self.status_var.set("Scanning folders...")

        # collect target folders: either subfolders or root itself
        subfolders = []
        for name in sorted(os.listdir(root)):
            full = os.path.join(root, name)
            if os.path.isdir(full):
                subfolders.append(full)

        # if no subfolders, treat root as a single folder (old behaviour)
        if not subfolders:
            subfolders = [root]

        # build list of (folder_path, start_pole, end_pole)
        targets = []
        for folder in subfolders:
            foldername = os.path.basename(folder).strip()
            if "_" in foldername:
                parts = foldername.split("_", 1)
                start = parts[0].strip()
                end = parts[1].strip()
                if not start or not end:
                    # skip invalid folder name
                    continue
            else:
                start = foldername
                end = None
            targets.append((folder, start, end))

        if not targets:
            self._import_lock = False
            self.status_var.set("Ready")
            messagebox.showwarning("Import", "No valid pole or line folders found.")
            return

        # count total image files for progress
        all_files = []
        for folder, start, end in targets:
            imgs = sorted([f for f in os.listdir(folder)
                           if f.lower().endswith((".jpg", ".jpeg", ".png"))])
            for f in imgs:
                all_files.append((folder, start, end, f))

        if not all_files:
            self._import_lock = False
            self.status_var.set("Ready")
            messagebox.showinfo("Import", "No image files found in selected folder.")
            return

        # progress dialog
        progress = tk.Toplevel(self)
        progress.title("Importing...")
        progress.geometry("420x90")
        progress.transient(self)
        ttk.Label(progress, text=f"Importing {len(all_files)} files from {len(targets)} folders...").pack(pady=(10,4))
        pb = ttk.Progressbar(progress, length=360, mode="determinate", maximum=len(all_files))
        pb.pack(pady=(4,8))
        progress.update()

        conn = self.db.connect()
        cur = conn.cursor()
        inserted = 0
        skipped = 0

        # we need seq_num per folder; keep counters
        seq_counters = {}
        for i, (folder, start, end, fname) in enumerate(all_files, start=1):
            key = (folder, start, end)
            seq_counters.setdefault(key, 0)
            seq_counters[key] += 1
            seq_num = seq_counters[key]

            path = os.path.join(folder, fname)
            # skip if this file_hash already exists
            cur.execute("SELECT COUNT(1) FROM images WHERE file_hash = ?", (path,))
            if cur.fetchone()[0] > 0:
                skipped += 1
            else:
                cur.execute("""
                    INSERT INTO images (filename, file_hash, start_pole, end_pole, seq_num, timestamp, notes)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
                """, (fname, path, start, end, seq_num, None))
                inserted += 1

            pb["value"] = i
            progress.update()

        conn.commit()
        conn.close()
        progress.destroy()
        self._import_lock = False

        self.status_var.set(f"Imported {inserted} files (skipped {skipped}).")
        messagebox.showinfo(
            "Import Complete",
            f"Imported {inserted} images from {len(targets)} folders.\nSkipped (existing): {skipped}"
        )

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
