import os
import platform
import subprocess

def reveal_file(path):
    folder = os.path.abspath(path) if os.path.isdir(path) else os.path.dirname(path)
    try:
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.call(["open", folder])
        else:
            subprocess.call(["xdg-open", folder])
    except Exception:
        try:
            import webbrowser
            webbrowser.open(f"file://{folder}")
        except Exception:
            pass
