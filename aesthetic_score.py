import math


def center_of(obj):
    return obj["x"] + obj["w"] / 2, obj["y"] + obj["h"] / 2


def edge_distance(a, b):
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]

    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]

    dx = max(0, max(ax1 - bx2, bx1 - ax2))
    dy = max(0, max(ay1 - by2, by1 - ay2))
    return math.sqrt(dx * dx + dy * dy)


def overlap_area(a, b):
    x_overlap = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    y_overlap = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return x_overlap * y_overlap


def proximity_score(layout, canvas_width):
    grouped = {}
    for obj in layout:
        key = obj["filename"]
        grouped.setdefault(key, []).append(obj)

    valid_groups = [g for g in grouped.values() if len(g) >= 2]
    if not valid_groups:
        return 1.0

    scores = []
    for group in valid_groups:
        dists = []
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                dists.append(edge_distance(group[i], group[j]))
        avg_dist = sum(dists) / len(dists)
        score = max(0.0, 1.0 - avg_dist / (canvas_width / 2))
        scores.append(score)

    return sum(scores) / len(scores)


def whitespace_score(layout, canvas_width):
    if len(layout) < 2:
        return 1.0

    dists = []
    for i in range(len(layout)):
        for j in range(i + 1, len(layout)):
            dists.append(edge_distance(layout[i], layout[j]))

    avg = sum(dists) / len(dists)
    ideal = canvas_width * 0.12
    return max(0.0, 1.0 - abs(avg - ideal) / ideal)


def alignment_score(layout, tolerance=10):
    if not layout:
        return 0.0

    xs = [obj["x"] for obj in layout]
    ys = [obj["y"] for obj in layout]

    aligned_x = sum(
        any(abs(x - other) <= tolerance for other in xs if x != other)
        for x in xs
    )
    aligned_y = sum(
        any(abs(y - other) <= tolerance for other in ys if y != other)
        for y in ys
    )

    return (aligned_x + aligned_y) / (2 * len(layout))


def contrast_score(layout, canvas_width, canvas_height):
    if not layout:
        return 0.0

    largest = max(layout, key=lambda o: o["w"] * o["h"])
    cx, cy = canvas_width / 2, canvas_height / 2
    lx, ly = center_of(largest)

    dist = math.sqrt((lx - cx) ** 2 + (ly - cy) ** 2)
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    return max(0.0, 1.0 - dist / max_dist)


def count_overlaps(layout):
    count = 0
    total_area = 0

    for i in range(len(layout)):
        for j in range(i + 1, len(layout)):
            area = overlap_area(layout[i], layout[j])
            if area > 0:
                count += 1
                total_area += area

    return count, total_area


def auto_aesthetic_score(layout, canvas_width, canvas_height):
    if not layout:
        return 0.0

    p = proximity_score(layout, canvas_width)
    w = whitespace_score(layout, canvas_width)
    a = alignment_score(layout)
    c = contrast_score(layout, canvas_width, canvas_height)

    base = 0.25 * p + 0.25 * w + 0.25 * a + 0.25 * c

    overlap_count, overlap_area_sum = count_overlaps(layout)
    penalty = 0.08 * overlap_count + min(0.25, overlap_area_sum / (canvas_width * canvas_height))

    final = max(0.0, base - penalty)
    return round(final, 4)