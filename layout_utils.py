import random


def snap_to_grid(x, y, grid_size):
    return (x // grid_size) * grid_size, (y // grid_size) * grid_size


def is_overlap(x, y, w, h, others, padding):
    for o in others:
        ox, oy, ow, oh = o["x"], o["y"], o["w"], o["h"]
        if (
            x < ox + ow + padding and
            x + w + padding > ox and
            y < oy + oh + padding and
            y + h + padding > oy
        ):
            return True
    return False


def place_nonoverlap(existing, w, h, canvas_width, canvas_height, grid_size, padding, max_attempts):
    for _ in range(max_attempts):
        x = random.randint(padding, canvas_width - w - padding)
        y = random.randint(padding, canvas_height - h - padding)
        x, y = snap_to_grid(x, y, grid_size)

        if not is_overlap(x, y, w, h, existing, padding):
            return x, y

    return None, None


def adjust_layout(layout, new_obj, canvas_width, canvas_height, grid_size, padding, max_shift_attempts):
    for shift in range(1, max_shift_attempts + 1):
        test_layout = []
        success = True

        for obj in layout:
            moved = False

            for dx in [-grid_size * shift, 0, grid_size * shift]:
                for dy in [-grid_size * shift, 0, grid_size * shift]:
                    x_try = obj["x"] + dx
                    y_try = obj["y"] + dy

                    if (
                        0 <= x_try <= canvas_width - obj["w"] and
                        0 <= y_try <= canvas_height - obj["h"]
                    ):
                        if not is_overlap(x_try, y_try, obj["w"], obj["h"], test_layout, padding):
                            test_layout.append({
                                **obj,
                                "x": x_try,
                                "y": y_try
                            })
                            moved = True
                            break
                if moved:
                    break

            if not moved:
                success = False
                break

        if success:
            for x in range(padding, canvas_width - new_obj["w"], grid_size):
                for y in range(padding, canvas_height - new_obj["h"], grid_size):
                    if not is_overlap(x, y, new_obj["w"], new_obj["h"], test_layout, padding):
                        test_layout.append({
                            **new_obj,
                            "x": x,
                            "y": y
                        })
                        return test_layout

    return None


def generate_layout_with_adjustment(objects, config):
    placed = []

    for obj in objects:
        x, y = place_nonoverlap(
            placed,
            obj["w"],
            obj["h"],
            config["canvas_width"],
            config["canvas_height"],
            config["grid_size"],
            config["padding"],
            config["max_place_attempts"]
        )

        if x is not None:
            placed.append({
                **obj,
                "x": x,
                "y": y
            })
        else:
            adjusted = adjust_layout(
                placed,
                obj,
                config["canvas_width"],
                config["canvas_height"],
                config["grid_size"],
                config["padding"],
                config["max_adjust_shift_attempts"]
            )

            if adjusted:
                placed = adjusted

    return placed


def repair_layout(layout, config):
    repaired = []

    for obj in layout:
        x, y = obj["x"], obj["y"]
        w, h = obj["w"], obj["h"]

        x = max(0, min(x, config["canvas_width"] - w))
        y = max(0, min(y, config["canvas_height"] - h))
        x, y = snap_to_grid(x, y, config["grid_size"])

        if not is_overlap(x, y, w, h, repaired, config["padding"]):
            repaired.append({**obj, "x": x, "y": y})
        else:
            px, py = place_nonoverlap(
                repaired,
                w,
                h,
                config["canvas_width"],
                config["canvas_height"],
                config["grid_size"],
                config["padding"],
                config["max_place_attempts"]
            )
            if px is not None:
                repaired.append({**obj, "x": px, "y": py})

    return repaired