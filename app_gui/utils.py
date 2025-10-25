import ctypes
import platform
import tkinter as tk

def enable_windows_dpi_awareness():
    if platform.system() == "Windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

def autoscale_fonts_by_screen(root, scale_factor=1.0):
    try:
        width = root.winfo_screenwidth()
        if width >= 1920:
            scale_factor = 1.2
        elif width >= 2560:
            scale_factor = 1.4
        elif width <= 1366:
            scale_factor = 1.0

        default_font = tk.font.nametofont("TkDefaultFont")
        size = int(default_font.cget("size") * scale_factor)
        default_font.configure(size=size)

        text_font = tk.font.nametofont("TkTextFont")
        text_font.configure(size=size)

        fixed_font = tk.font.nametofont("TkFixedFont")
        fixed_font.configure(size=size)
    except Exception:
        pass
