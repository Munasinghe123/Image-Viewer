import os
import glob


def find_logo():
    folder = os.path.dirname(__file__) or "."
    patterns = ["leco*.png", "leco*.jpg", "logo*.png", "logo*.jpg"]

    for p in patterns:
        for f in glob.glob(os.path.join(folder, p)):
            name = os.path.basename(f).lower()
            if "leco" in name or "logo" in name:
                return f

    # fallback to any image
    for p in ("*.png", "*.jpg", "*.jpeg"):
        res = glob.glob(os.path.join(folder, p))
        if res:
            return res[0]

    return None