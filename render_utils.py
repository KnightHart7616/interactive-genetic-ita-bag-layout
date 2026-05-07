import os
from PIL import Image


def draw_layout(layout, bg_file, config):
    canvas_width = config["canvas_width"]
    canvas_height = config["canvas_height"]
    bg_folder = config["background_folder"]
    src_folder = config["src_folder"]

    if bg_file is None:
        bg = Image.new("RGB", (canvas_width, canvas_height), "white")
    else:
        bg_path = os.path.join(bg_folder, bg_file)
        bg = Image.open(bg_path).resize((canvas_width, canvas_height)).convert("RGB")

    for obj in layout:
        try:
            img = Image.open(
                os.path.join(src_folder, obj["filename"])
            ).convert("RGBA")
            img = img.resize((obj["w"], obj["h"]))
            bg.paste(img, (obj["x"], obj["y"]), img)
        except Exception as e:
            print(f"⚠️ Failed to render {obj['filename']}: {e}")

    return bg


def save_layout_png(layout, bg_file, config, save_path):
    image = draw_layout(layout, bg_file, config)
    image.save(save_path)