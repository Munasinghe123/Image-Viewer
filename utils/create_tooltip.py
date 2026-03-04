import tkinter as tk

def create_tooltip(widget, text):
    tip = None
    def enter(e):
        nonlocal tip
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(tip, text=text, bg="#FFFFE0", relief=tk.SOLID, borderwidth=1, font=FONT_SMALL)
        lbl.pack()
    def leave(e):
        nonlocal tip
        if tip:
            tip.destroy()
            tip = None
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)