
import os
import json
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont
import requests
from io import BytesIO
from config import *
from utils import reveal_file, create_tooltip

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


def load_image_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print("Image load failed:", e)
        return None


class ViewerWindow(tk.Toplevel):
    def __init__(self, master, images, title="Image Viewer"):
        super().__init__(master)
        self.title(title)
        self.configure(bg=BG_MAIN)
        self.center_window(1200, 820)

        self.master = master
        self.images = images
        self.index = 0
        self.original_image = None
        self.photo_cache = None
        self.zoom_scale = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 8.0
        self.img_pos_x = 0
        self.img_pos_y = 0

        # annotation data
        self.annotations = []
        self.selected_ann_idx = None
        self._draw_mode = tk.StringVar(value="pan")  # pan, rect, oval, text, select
        self.current_color = MARKUP_COLOR_DEFAULT
        self.current_width = MARKUP_WIDTH_DEFAULT
        self._undo_stack = []
        self._redo_stack = []
        self._drag_start = None
        self._draw_start = None
        self._tmp_draw_id = None
        self._shift_down = False

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Accent.TButton", background=ACCENT, foreground="white", font=FONT_NORMAL, padding=6)
        style.map("Accent.TButton", background=[("active", ACCENT_LIGHT)])

        # top: toolbar
        toolbar = tk.Frame(self, bg=BG_PANEL, height=56)
        toolbar.pack(fill=tk.X, side=tk.TOP, padx=8, pady=(8,0))
        toolbar.pack_propagate(False)

        def tbtn(text, cmd, tooltip=None):
            b = tk.Button(toolbar, text=text, font=FONT_NORMAL, bg="white", fg=ACCENT, relief=tk.FLAT, command=cmd)
            b.pack(side=tk.LEFT, padx=6, pady=6)
            if tooltip:
                create_tooltip(b, tooltip)
            return b

        tbtn("Pan", lambda: self._draw_mode.set("pan"), "Pan / drag the image")
        tbtn("Rect", lambda: self._draw_mode.set("rect"), "Draw rectangle markup")
        tbtn("Oval", lambda: self._draw_mode.set("oval"), "Draw circle/oval markup")
        tbtn("Text", lambda: self._draw_mode.set("text"), "Add text annotation")
        tbtn("Select", lambda: self._draw_mode.set("select"), "Select / move / resize annotations")
        ttk.Button(toolbar, text="Undo", style="Accent.TButton", command=self.undo).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Redo", style="Accent.TButton", command=self.redo).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Save", style="Accent.TButton", command=self.export_current_with_markups).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Batch Export", style="Accent.TButton", command=self.batch_export_all).pack(side=tk.LEFT, padx=6)

        # top-right style controls
        style_frame = tk.Frame(toolbar, bg=BG_PANEL)
        style_frame.pack(side=tk.RIGHT, padx=8)
        tk.Label(style_frame, text="Color:", bg=BG_PANEL, fg=TEXT_DARK, font=FONT_SMALL).pack(side=tk.LEFT, padx=(0,6))
        self.color_preview = tk.Canvas(style_frame, width=28, height=20, highlightthickness=1)
        self.color_preview.create_rectangle(0,0,28,20, fill=self.current_color, outline="#000")
        self.color_preview.pack(side=tk.LEFT, padx=(0,6))
        tk.Button(style_frame, text="Choose", bg="white", fg=ACCENT, relief=tk.FLAT, command=self.choose_color).pack(side=tk.LEFT, padx=6)
        tk.Label(style_frame, text="Width:", bg=BG_PANEL, fg=TEXT_DARK, font=FONT_SMALL).pack(side=tk.LEFT, padx=(8,6))
        self.width_var = tk.IntVar(value=self.current_width)
        ttk.Scale(style_frame, from_=1, to=20, orient=tk.HORIZONTAL, variable=self.width_var, command=self.on_width_change).pack(side=tk.LEFT, padx=(0,6))

        # center: image canvas + thumbnails
        center = tk.Frame(self, bg=BG_MAIN)
        center.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = tk.Frame(center, bg=BG_MAIN)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = tk.Frame(center, width=340, bg=BG_PANEL)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(12,0))
        right.pack_propagate(False)

        # canvas area
        self.canvas = tk.Canvas(left, bg=CANVAS_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # mouse and keyboard bindings
        self.canvas.bind("<MouseWheel>", self.on_mouse_zoom_windows)
        self.canvas.bind("<Button-4>", self.on_mouse_zoom_linux)
        self.canvas.bind("<Button-5>", self.on_mouse_zoom_linux)
        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click_show_annotation)
        self.bind_all("<KeyPress-Shift_L>", lambda e: self._set_shift(True))
        self.bind_all("<KeyRelease-Shift_L>", lambda e: self._set_shift(False))
        self.bind_all("<KeyPress-Shift_R>", lambda e: self._set_shift(True))
        self.bind_all("<KeyRelease-Shift_R>", lambda e: self._set_shift(False))
        self.bind("<Left>", lambda e: self.on_prev())
        self.bind("<Right>", lambda e: self.on_next())

        # thumbnail strip
        thumbs_frame = tk.Frame(left, bg=BG_MAIN, height=96)
        thumbs_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=(6,0))
        self.thumb_canvas = tk.Canvas(thumbs_frame, bg=BG_MAIN, height=96, highlightthickness=0)
        self.thumb_scroll = ttk.Scrollbar(thumbs_frame, orient=tk.HORIZONTAL, command=self.thumb_canvas.xview)
        self.thumb_canvas.configure(xscrollcommand=self.thumb_scroll.set)
        self.thumb_canvas.pack(fill=tk.X, side=tk.TOP, expand=True)
        self.thumb_scroll.pack(fill=tk.X, side=tk.BOTTOM)
        self.thumb_frame_inner = tk.Frame(self.thumb_canvas, bg=BG_MAIN)
        self.thumb_canvas.create_window((0,0), window=self.thumb_frame_inner, anchor="nw")
        self.thumb_frame_inner.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))

        # right panel: info + controls
        info_label = tk.Label(right, text="Image Info", font=FONT_NORMAL, bg=BG_PANEL, fg=TEXT_DARK)
        info_label.pack(anchor="nw", pady=(8,6), padx=8)
        self.info_text = tk.Text(right, width=36, height=8, wrap=tk.WORD, font=FONT_NORMAL)
        self.info_text.pack(padx=8)

        self.status_label = tk.Label(right, text="", font=FONT_NORMAL, bg=BG_PANEL, fg=MUTED)
        self.status_label.pack(pady=(8,6), anchor="nw", padx=8)

        # annotation list
        ann_label = tk.Label(right, text="Annotations", bg=BG_PANEL, fg=TEXT_DARK, font=FONT_NORMAL)
        ann_label.pack(anchor="nw", padx=8)
        self.ann_listbox = tk.Listbox(right, width=44, height=10)
        self.ann_listbox.pack(padx=8, pady=(4,8))
        self.ann_listbox.bind("<<ListboxSelect>>", self.on_annotation_select)
        self.ann_listbox.bind("<Double-Button-1>", self.on_annotation_list_double)

        # bottom controls on right
        ttk.Button(right, text="Save annotations to DB", style="Accent.TButton", command=self.save_annotations_to_db).pack(padx=8, pady=(6,6), fill=tk.X)
        ttk.Button(right, text="Export annotations (JSON/CSV)", style="Accent.TButton", command=self.export_annotations_metadata).pack(padx=8, pady=(4,6), fill=tk.X)
        ttk.Button(right, text="Close", style="Accent.TButton", command=self.destroy).pack(padx=8, pady=(12,8), fill=tk.X)

        # initial load
        self.show_image(0)

    def center_window(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        x = (sw - w) // 2; y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ---------- helper methods ----------
    def _set_shift(self, v):
        self._shift_down = v

    def push_undo(self):
        self._undo_stack.append(json.loads(json.dumps(self.annotations)))
        self._redo_stack.clear()
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def undo(self):
        if not self._undo_stack:
            return
        last = self._undo_stack.pop()
        self._redo_stack.append(json.loads(json.dumps(self.annotations)))
        self.annotations = last
        self.selected_ann_idx = None
        self.refresh_annotations_list()
        self.display_image()

    def redo(self):
        if not self._redo_stack:
            return
        nxt = self._redo_stack.pop()
        self._undo_stack.append(json.loads(json.dumps(self.annotations)))
        self.annotations = nxt
        self.selected_ann_idx = None
        self.refresh_annotations_list()
        self.display_image()

    def choose_color(self):
        c = colorchooser.askcolor(color=self.current_color, title="Choose markup color")
        if c and c[1]:
            self.current_color = c[1]
            self.color_preview.delete("all")
            self.color_preview.create_rectangle(0,0,28,20, fill=self.current_color, outline="#000")

    def on_width_change(self, _):
        try:
            self.current_width = int(self.width_var.get())
        except Exception:
            pass

    # ---------- image load / display ----------
    def show_image(self, idx):
        if not (0 <= idx < len(self.images)):
            return
        self.index = idx
        rec = self.images[idx]
        url = rec['published_path']

        img = load_image_from_url(url)

        if img is None:
            self.clear_canvas()
            self.info_text.insert(tk.END, f"Failed to load image from URL:\n{url}")
            return

        self.original_image = img

        # load annotations from notes JSON if present
        self.annotations = []
        notes = rec.get('notes')
        if notes:
            try:
                payload = json.loads(notes)
                if isinstance(payload, list):
                    for i, it in enumerate(payload):
                        a = {
                            "id": i+1,
                            "type": it.get("type","rect"),
                            "x_rel": float(it.get("x_rel",0)),
                            "y_rel": float(it.get("y_rel",0)),
                            "w_rel": float(it.get("w_rel",0)),
                            "h_rel": float(it.get("h_rel",0)),
                            "text": it.get("text",""),
                            "color": it.get("color", MARKUP_COLOR_DEFAULT),
                            "width": int(it.get("width", MARKUP_WIDTH_DEFAULT))
                        }
                        self.annotations.append(a)
            except Exception:
                pass

        self.selected_ann_idx = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.fit_image_to_canvas()

        info = (
            f"Filename: {rec.get('filename')}\n"
            f"Sequence: {rec.get('seq_num')}\n"
            f"Start: {rec.get('start_pole')}\n"
            f"End: {rec.get('end_pole')}\n"
            f"Timestamp: {rec.get('timestamp')}\n"
        )
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info)
        self.refresh_thumbnails()
        self.refresh_annotations_list()
        self.display_image()

    def fit_image_to_canvas(self):
        if not self.original_image:
            return
        canvas_w = self.canvas.winfo_width() or THUMBNAIL_SIZE[0]
        canvas_h = self.canvas.winfo_height() or THUMBNAIL_SIZE[1]
        img_w, img_h = self.original_image.size
        fit_ratio = min(canvas_w / img_w, canvas_h / img_h, 1.0)
        self.zoom_scale = fit_ratio
        disp_w = int(img_w * self.zoom_scale)
        disp_h = int(img_h * self.zoom_scale)
        self.img_pos_x = max(0, (canvas_w - disp_w)//2)
        self.img_pos_y = max(0, (canvas_h - disp_h)//2)

    def display_image(self):
        if not self.original_image:
            return
        img = self.original_image
        w, h = img.size
        zoom_w = max(1, int(w * self.zoom_scale))
        zoom_h = max(1, int(h * self.zoom_scale))
        resized = img.resize((zoom_w, zoom_h), Image.LANCZOS)
        self.photo_cache = ImageTk.PhotoImage(resized)
        self.canvas.delete("IMG")
        # fill background to avoid black flash
        canvas_w = self.canvas.winfo_width() or THUMBNAIL_SIZE[0]
        canvas_h = self.canvas.winfo_height() or THUMBNAIL_SIZE[1]
        self.canvas.delete("BG")
        self.canvas.create_rectangle(0,0,canvas_w,canvas_h, fill=CANVAS_BG, outline=CANVAS_BG, tags="BG")
        self.canvas.create_image(self.img_pos_x, self.img_pos_y, image=self.photo_cache, anchor="nw", tags="IMG")
        self.canvas.config(scrollregion=(0,0, max(canvas_w, self.img_pos_x + zoom_w), max(canvas_h, self.img_pos_y + zoom_h)))
        self.draw_annotations()
        self.update_status()

    def update_status(self):
        self.status_label.config(text=f"Image {self.index+1} / {len(self.images)}    Zoom: {int(self.zoom_scale*100)}%")

    # ---------- annotations drawing & interaction ----------
    def draw_annotations(self):
        self.canvas.delete("ANN")
        if not self.original_image:
            return
        img_w, img_h = self.original_image.size
        for i, a in enumerate(self.annotations):
            typ = a.get("type","rect")
            color = a.get("color", self.current_color)
            width = int(a.get("width", MARKUP_WIDTH_DEFAULT))
            if typ in ("rect","oval"):
                left = int(self.img_pos_x + a["x_rel"] * img_w * self.zoom_scale)
                top = int(self.img_pos_y + a["y_rel"] * img_h * self.zoom_scale)
                right = int(left + a["w_rel"] * img_w * self.zoom_scale)
                bottom = int(top + a["h_rel"] * img_h * self.zoom_scale)
                if typ == "rect":
                    self.canvas.create_rectangle(left, top, right, bottom, outline=color, width=width, tags=("ANN", f"ANN_{a['id']}"))
                else:
                    self.canvas.create_oval(left, top, right, bottom, outline=color, width=width, tags=("ANN", f"ANN_{a['id']}"))
                self.canvas.create_text(left+6, top+6, text=str(a["id"]), anchor="nw",
                                        font=("Segoe UI", 9, "bold"), fill="white", tags=("ANN",))
            else:  # text
                px = int(self.img_pos_x + a["x_rel"] * img_w * self.zoom_scale)
                py = int(self.img_pos_y + a["y_rel"] * img_h * self.zoom_scale)
                self.canvas.create_text(px, py, text=a.get("text",""), anchor="nw",
                                        font=("Segoe UI", 12, "bold"),
                                        fill=a.get("color", self.current_color),
                                        tags=("ANN", f"ANN_{a['id']}"))

    def refresh_annotations_list(self):
        self.ann_listbox.delete(0, tk.END)
        for a in self.annotations:
            if a["type"] in ("rect","oval"):
                label = f"{a['id']}: {a['type']} (w={a.get('width',MARKUP_WIDTH_DEFAULT)})"
            else:
                label = f"{a['id']}: text - {a.get('text','')}"
            self.ann_listbox.insert(tk.END, label)
        if self.selected_ann_idx is not None:
            self.ann_listbox.select_clear(0, tk.END)
            if 0 <= self.selected_ann_idx < len(self.annotations):
                self.ann_listbox.select_set(self.selected_ann_idx)
                self.ann_listbox.see(self.selected_ann_idx)

    # selection helpers
    def find_annotation_at(self, cx, cy):
        if not self.original_image:
            return None, None
        img_w, img_h = self.original_image.size
        for i in range(len(self.annotations)-1, -1, -1):
            a = self.annotations[i]
            typ = a["type"]
            if typ in ("rect","oval"):
                left = int(self.img_pos_x + a["x_rel"] * img_w * self.zoom_scale)
                top = int(self.img_pos_y + a["y_rel"] * img_h * self.zoom_scale)
                right = int(left + a["w_rel"] * img_w * self.zoom_scale)
                bottom = int(top + a["h_rel"] * img_h * self.zoom_scale)
                if left <= cx <= right and top <= cy <= bottom:
                    return i, a
            else:
                px = int(self.img_pos_x + a["x_rel"] * img_w * self.zoom_scale)
                py = int(self.img_pos_y + a["y_rel"] * img_h * self.zoom_scale)
                if abs(px - cx) <= 10 and abs(py - cy) <= 10:
                    return i, a
        return None, None

    # ---------- mouse events ----------
    def on_left_press(self, event):
        mode = self._draw_mode.get()
        if mode == "select":
            idx, a = self.find_annotation_at(event.x, event.y)
            if idx is not None:
                self.selected_ann_idx = idx
                self.push_undo()
            else:
                self.selected_ann_idx = None
            self.refresh_annotations_list()
            return

        if mode == "pan":
            self._drag_start = (event.x, event.y, self.img_pos_x, self.img_pos_y)
            return

        if mode in ("rect", "oval", "text"):
            self._draw_start = (event.x, event.y)
            # remove temp
            if self._tmp_draw_id:
                self.canvas.delete(self._tmp_draw_id)
                self._tmp_draw_id = None

    def on_left_move(self, event):
        mode = self._draw_mode.get()
        if mode == "pan" and self._drag_start:
            sx, sy, sxpos, sypos = self._drag_start
            dx = event.x - sx; dy = event.y - sy
            self.img_pos_x = sxpos + dx; self.img_pos_y = sypos + dy
            self.display_image()
            return

        if mode in ("rect", "oval"):
            if not self._draw_start:
                return
            x0,y0 = self._draw_start; x1,y1 = event.x, event.y
            if self._tmp_draw_id:
                self.canvas.delete(self._tmp_draw_id)
            if self._shift_down:
                dx = x1-x0; dy = y1-y0
                d = dx if abs(dx) < abs(dy) else dy
                x1 = x0 + d if dx>=0 else x0 + d
                y1 = y0 + d if dy>=0 else y0 + d
            if mode == "rect":
                self._tmp_draw_id = self.canvas.create_rectangle(
                    x0,y0,x1,y1, outline=self.current_color,
                    width=self.current_width, dash=(3,2), tags="TMP"
                )
            else:
                self._tmp_draw_id = self.canvas.create_oval(
                    x0,y0,x1,y1, outline=self.current_color,
                    width=self.current_width, dash=(3,2), tags="TMP"
                )
        elif mode == "text":
            if not self._draw_start:
                return
            x0,y0 = self._draw_start
            if self._tmp_draw_id:
                self.canvas.delete(self._tmp_draw_id)
            self._tmp_draw_id = self.canvas.create_text(
                x0, y0, text="Text", anchor="nw",
                fill=self.current_color, font=("Segoe UI",12,"bold"), tags="TMP"
            )

    def on_left_release(self, event):
        mode = self._draw_mode.get()
        if mode == "pan":
            self._drag_start = None
            return

        if mode in ("rect","oval"):
            if not self._draw_start:
                return
            x0,y0 = self._draw_start; x1,y1 = event.x, event.y
            if self._tmp_draw_id:
                self.canvas.delete(self._tmp_draw_id); self._tmp_draw_id = None
            self._draw_start = None
            img_w, img_h = self.original_image.size
            img_px_x0 = (x0 - self.img_pos_x) / self.zoom_scale
            img_px_y0 = (y0 - self.img_pos_y) / self.zoom_scale
            img_px_x1 = (x1 - self.img_pos_x) / self.zoom_scale
            img_px_y1 = (y1 - self.img_pos_y) / self.zoom_scale
            left_px = max(0, min(img_px_x0, img_px_x1)); top_px = max(0, min(img_px_y0, img_px_y1))
            right_px = min(img_w, max(img_px_x0, img_px_x1)); bottom_px = min(img_h, max(img_px_y0, img_px_y1))
            if abs(right_px - left_px) < 3 or abs(bottom_px - top_px) < 3:
                return
            if self._shift_down:
                size = min(right_px-left_px, bottom_px-top_px)
                right_px = left_px + size; bottom_px = top_px + size
            x_rel = left_px / img_w; y_rel = top_px / img_h
            w_rel = (right_px - left_px) / img_w; h_rel = (bottom_px - top_px) / img_h
            self.push_undo()
            new_id = (self.annotations[-1]["id"]+1) if self.annotations else 1
            ann = {
                "id": new_id,
                "type": "rect" if mode=="rect" else "oval",
                "x_rel": x_rel,
                "y_rel": y_rel,
                "w_rel": w_rel,
                "h_rel": h_rel,
                "text":"",
                "color": self.current_color,
                "width": int(self.current_width)
            }
            self.annotations.append(ann)
            self.selected_ann_idx = len(self.annotations)-1
            self.refresh_annotations_list()
            self.display_image()
        elif mode == "text":
            if not self._draw_start:
                return
            x0,y0 = self._draw_start
            if self._tmp_draw_id:
                self.canvas.delete(self._tmp_draw_id); self._tmp_draw_id = None
            self._draw_start = None
            img_w, img_h = self.original_image.size
            img_px_x = (x0 - self.img_pos_x) / self.zoom_scale
            img_px_y = (y0 - self.img_pos_y) / self.zoom_scale
            if img_px_x < 0 or img_px_y < 0 or img_px_x > img_w or img_px_y > img_h:
                messagebox.showinfo("Outside image", "Click inside image to add text.")
                return
            text = simpledialog.askstring("Text annotation", "Enter text:", parent=self)
            if text is None or text.strip()=="":
                return
            self.push_undo()
            x_rel = img_px_x / img_w; y_rel = img_px_y / img_h
            new_id = (self.annotations[-1]["id"]+1) if self.annotations else 1
            ann = {
                "id": new_id,
                "type": "text",
                "x_rel": x_rel,
                "y_rel": y_rel,
                "w_rel":0.0,
                "h_rel":0.0,
                "text": text.strip(),
                "color": self.current_color,
                "width":0
            }
            self.annotations.append(ann)
            self.selected_ann_idx = len(self.annotations)-1
            self.refresh_annotations_list()
            self.display_image()

    def on_canvas_double_click(self, event):
        idx, a = self.find_annotation_at(event.x, event.y)
        if idx is None:
            return
        if a["type"] == "text":
            new_text = simpledialog.askstring("Edit text", "Edit annotation text:",
                                              initialvalue=a.get("text",""), parent=self)
            if new_text is None:
                return
            self.push_undo()
            a["text"] = new_text.strip()
            self.refresh_annotations_list()
            self.display_image()

    def on_right_click_show_annotation(self, event):
        idx, a = self.find_annotation_at(event.x, event.y)
        if idx is None:
            return
        if a["type"] == "text":
            messagebox.showinfo("Annotation", f"{a['id']}: {a['text']}")
        else:
            messagebox.showinfo("Annotation", f"{a['id']}: {a['type']} markup")

    # ---------- mouse wheel zoom ----------
    def on_mouse_zoom_windows(self, event):
        factor = 1.25 if event.delta > 0 else 1/1.25
        self.zoom_at_point(event.x, event.y, factor)

    def on_mouse_zoom_linux(self, event):
        if event.num == 4:
            self.zoom_at_point(event.x, event.y, 1.25)
        elif event.num == 5:
            self.zoom_at_point(event.x, event.y, 1/1.25)

    def zoom_at_point(self, canvas_x, canvas_y, factor):
        if not self.original_image:
            return
        old = self.zoom_scale
        new = old * factor
        if new < self.min_zoom: new = self.min_zoom
        if new > self.max_zoom: new = self.max_zoom
        img_px_x = (canvas_x - self.img_pos_x) / old
        img_px_y = (canvas_y - self.img_pos_y) / old
        self.zoom_scale = new
        self.img_pos_x = int(canvas_x - img_px_x * new)
        self.img_pos_y = int(canvas_y - img_px_y * new)
        self.display_image()

    # ---------- annotations persistence & export ----------
    def save_annotations_to_db(self):
        if not self.images:
            return
        rec = self.images[self.index]
        payload = []
        for a in self.annotations:
            payload.append({
                "type": a.get("type","rect"),
                "x_rel": a.get("x_rel",0),
                "y_rel": a.get("y_rel",0),
                "w_rel": a.get("w_rel",0),
                "h_rel": a.get("h_rel",0),
                "text": a.get("text",""),
                "color": a.get("color", MARKUP_COLOR_DEFAULT),
                "width": a.get("width", MARKUP_WIDTH_DEFAULT)
            })
        notes_text = json.dumps(payload)
        master_db = getattr(self.master, "db", None)
        if master_db:
            master_db.update_notes(rec["id"], notes_text)
            self.images[self.index]["notes"] = notes_text
            messagebox.showinfo("Saved", "Annotations saved to DB (notes field).")
        else:
            messagebox.showinfo("No DB", "No DB available to save annotations.")

    def export_current_with_markups(self):
        if not self.original_image:
            return
        default = os.path.splitext(self.images[self.index]["filename"])[0] + "_marked.png"
        target = filedialog.asksaveasfilename(defaultextension=".png",
                                              initialfile=default,
                                              filetypes=[("PNG","*.png")])
        if not target:
            return
        self._save_burned_image(target)
        messagebox.showinfo("Saved", f"Image saved: {target}")
        try:
            reveal_file(target)
        except Exception:
            pass

    def _save_burned_image(self, out_path):
        img = self.original_image.convert("RGBA").copy()
        draw = ImageDraw.Draw(img)
        img_w, img_h = img.size
        try:
            font = ImageFont.truetype("arial.ttf", max(12, int(img_h*0.02)))
        except Exception:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", max(12, int(img_h*0.02)))
            except Exception:
                font = ImageFont.load_default()
        for a in self.annotations:
            typ = a.get("type","rect")
            color = a.get("color", MARKUP_COLOR_DEFAULT)
            width = int(a.get("width", MARKUP_WIDTH_DEFAULT))
            if typ in ("rect","oval"):
                l = int(a["x_rel"]*img_w); t = int(a["y_rel"]*img_h)
                r = int(l + a["w_rel"]*img_w); b = int(t + a["h_rel"]*img_h)
                if typ=="rect":
                    draw.rectangle([l,t,r,b], outline=color, width=width)
                else:
                    draw.ellipse([l,t,r,b], outline=color, width=width)
            else:
                x = int(a["x_rel"]*img_w); y = int(a["y_rel"]*img_h)
                text = a.get("text","")
                if text:
                    for ox in (-1,0,1):
                        for oy in (-1,0,1):
                            draw.text((x+ox,y+oy), text, font=font, fill="black")
                    draw.text((x,y), text, font=font, fill=color)
        img.save(out_path)

    def batch_export_all(self):
        if not self.images:
            messagebox.showinfo("No images", "No images loaded.")
            return
        folder = filedialog.askdirectory(title="Select folder to save batch")
        if not folder:
            return
        for rec in self.images:
            if not os.path.exists(rec["filepath"]):
                continue
            try:
                img = Image.open(rec["filepath"]).convert("RGBA")
                saved = self.original_image
                try:
                    self.original_image = img
                    out_name = os.path.splitext(rec["filename"])[0] + "_marked.png"
                    out_path = os.path.join(folder, out_name)
                    notes = rec.get("notes", "")
                    ann_list = []
                    if notes:
                        try:
                            ann_list = json.loads(notes)
                        except Exception:
                            ann_list = []
                    self.annotations = []
                    for i, a in enumerate(ann_list):
                        na = dict(a)
                        na.setdefault("id", i+1)
                        self.annotations.append(na)
                    self._save_burned_image(out_path)
                finally:
                    self.original_image = saved
            except Exception as e:
                print("Batch export error:", e)
        messagebox.showinfo("Batch Export", f"Batch exported to: {folder}")
        try:
            reveal_file(folder)
        except Exception:
            pass

    def export_annotations_metadata(self):
        if not self.images:
            messagebox.showinfo("No images", "No images loaded.")
            return
        target = filedialog.asksaveasfilename(defaultextension=".json",
                                              filetypes=[("JSON","*.json")])
        if not target:
            return
        all_meta = []
        for rec in self.images:
            notes = rec.get("notes","")
            annlist = []
            if notes:
                try:
                    annlist = json.loads(notes)
                except Exception:
                    annlist = []
            for a in annlist:
                row = {
                    "filename": rec.get("filename"),
                    "type": a.get("type",""),
                    "x_rel": a.get("x_rel",0),
                    "y_rel": a.get("y_rel",0),
                    "w_rel": a.get("w_rel",0),
                    "h_rel": a.get("h_rel",0),
                    "text": a.get("text",""),
                    "color": a.get("color",MARKUP_COLOR_DEFAULT),
                    "width": a.get("width", MARKUP_WIDTH_DEFAULT)
                }
                all_meta.append(row)
        with open(target, "w", encoding="utf-8") as jf:
            json.dump(all_meta, jf, indent=2)
        csv_target = os.path.splitext(target)[0] + ".csv"
        keys = ["filename","type","x_rel","y_rel","w_rel","h_rel","text","color","width"]
        with open(csv_target, "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(cf, fieldnames=keys)
            writer.writeheader()
            for r in all_meta:
                writer.writerow(r)
        messagebox.showinfo("Exported", f"Annotations saved:\n{target}\n{csv_target}")
        try:
            reveal_file(os.path.dirname(target))
        except Exception:
            pass

    # ---------- thumbnail strip ----------
    def refresh_thumbnails(self):
        for w in self.thumb_frame_inner.winfo_children():
            w.destroy()
        self.thumb_images = []
        for i, rec in enumerate(self.images):
            try:
                pil = load_image_from_url(rec["published_path"])

                if pil is None:
                    continue

                pil = pil.convert("RGB")
                pil.thumbnail((120, 80), Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(pil)
                self.thumb_images.append(tkimg)
                b = tk.Label(self.thumb_frame_inner, image=tkimg, bd=2, relief=tk.RIDGE, cursor="hand2")
                b.image = tkimg
                b.pack(side=tk.LEFT, padx=6, pady=6)
                b.bind("<Button-1>", lambda e, idx=i: self.show_image(idx))
            except Exception:
                pass
        self.thumb_frame_inner.update_idletasks()
        self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))

    # ---------- annotation list handlers ----------
    def on_annotation_select(self, event):
        sel = self.ann_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.annotations):
            return
        self.selected_ann_idx = idx
        a = self.annotations[idx]
        # center selected annotation
        if self.original_image:
            img_w, img_h = self.original_image.size
            if a["type"] in ("rect","oval"):
                cx_rel = a["x_rel"] + a["w_rel"]/2.0
                cy_rel = a["y_rel"] + a["h_rel"]/2.0
            else:
                cx_rel = a["x_rel"]; cy_rel = a["y_rel"]
            canvas_w = self.canvas.winfo_width() or THUMBNAIL_SIZE[0]
            canvas_h = self.canvas.winfo_height() or THUMBNAIL_SIZE[1]
            self.img_pos_x = int(canvas_w//2 - cx_rel * img_w * self.zoom_scale)
            self.img_pos_y = int(canvas_h//2 - cy_rel * img_h * self.zoom_scale)
            self.display_image()

    def on_annotation_list_double(self, event):
        sel = self.ann_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        a = self.annotations[idx]
        if a["type"] == "text":
            new = simpledialog.askstring("Edit text", "Edit annotation text:",
                                         initialvalue=a.get("text",""), parent=self)
            if new is None:
                return
            self.push_undo()
            a["text"] = new.strip()
            self.refresh_annotations_list()
            self.display_image()
        else:
            messagebox.showinfo("Only text editable", "You can edit text annotations by double-clicking.")

    # ---------- selection helpers ----------
    def clear_canvas(self):
        self.canvas.delete("all")
        self.info_text.delete(1.0, tk.END)

    def on_prev(self):
        if self.index > 0:
            self.show_image(self.index - 1)

    def on_next(self):
        if self.index < len(self.images)-1:
            self.show_image(self.index + 1)

    # ---------- utilities ----------
    # (find_annotation_at already defined above)
