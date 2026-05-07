import os
import json
from PIL import Image
from collections import Counter

SRC_FOLDER = "src"
BG_FOLDER = "background"

OBJECT_LIST_PATH = "object_lists/object_list_002.json"
OUTPUT_ANALYSIS_PATH = "bg_analysis/bg_analysis_002.json"


def get_dominant_color(image):
    image = image.convert("RGBA")
    pixels = [pixel[:3] for pixel in image.getdata() if pixel[3] > 128]
    if not pixels:
        return (255, 255, 255)
    return Counter(pixels).most_common(1)[0][0]


def color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def load_object_list(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_avg_object_color(objects):
    colors = []

    for obj in objects:
        fname = obj["filename"]
        path = os.path.join(SRC_FOLDER, fname)

        try:
            img = Image.open(path)
            color = get_dominant_color(img)
            colors.append(color)
            print(f"✅ {fname}: {color}")
        except Exception as e:
            print(f"⚠️ Failed to read {fname}: {e}")

    if not colors:
        return (255, 255, 255)

    return tuple(sum(c[i] for c in colors) // len(colors) for i in range(3))


def analyze_backgrounds():
    os.makedirs(os.path.dirname(OUTPUT_ANALYSIS_PATH), exist_ok=True)

    objects = load_object_list(OBJECT_LIST_PATH)
    avg_color = compute_avg_object_color(objects)

    print(f"\n🎯 Average Object Color: {avg_color}\n")

    scores = []
    bg_files = [
        f for f in os.listdir(BG_FOLDER)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    total = len(bg_files)

    for idx, fname in enumerate(bg_files, start=1):
        path = os.path.join(BG_FOLDER, fname)

        try:
            img = Image.open(path)
            bg_color = get_dominant_color(img)
            dist = color_distance(avg_color, bg_color)

            scores.append({
                "filename": fname,
                "distance": dist
            })

            print(f"[{idx}/{total}] {fname} | Color={bg_color} | Distance={dist:.2f}")

        except Exception as e:
            print(f"[{idx}/{total}] Skip {fname}: {e}")

    scores.sort(key=lambda x: x["distance"])

    result = {
        "avg_color": list(avg_color),
        "background_scores": scores
    }

    with open(OUTPUT_ANALYSIS_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved to {OUTPUT_ANALYSIS_PATH}")


if __name__ == "__main__":
    analyze_backgrounds()