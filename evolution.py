import random
from layout_utils import repair_layout


def select_parents(layouts, fitnesses):
    weighted = []

    for layout, fitness in zip(layouts, fitnesses):
        copies = max(1, int(fitness * 100))
        weighted.extend([layout] * copies)

    if not weighted:
        return random.choice(layouts), random.choice(layouts)

    return random.choice(weighted), random.choice(weighted)


def crossover_layout(parent1, parent2):
    child = []
    min_len = min(len(parent1), len(parent2))

    for i in range(min_len):
        p1 = parent1[i]
        p2 = parent2[i]

        child.append({
            **p1,
            "x": (p1["x"] + p2["x"]) // 2,
            "y": (p1["y"] + p2["y"]) // 2
        })

    return child


def mutate_layout(layout, config):
    mutated = []

    for obj in layout:
        new_obj = obj.copy()

        if random.random() < config["mutation_rate"]:
            dx = random.choice([-config["grid_size"], 0, config["grid_size"]])
            dy = random.choice([-config["grid_size"], 0, config["grid_size"]])
            new_obj["x"] += dx
            new_obj["y"] += dy

        mutated.append(new_obj)

    return repair_layout(mutated, config)


def create_next_generation(current_layouts, fitnesses, config):
    paired = list(zip(current_layouts, fitnesses))
    paired.sort(key=lambda x: x[1], reverse=True)

    elite_count = max(1, len(current_layouts) // 5)
    elites = [layout for layout, _ in paired[:elite_count]]

    next_generation = elites.copy()

    while len(next_generation) < config["num_layouts_per_gen"]:
        p1, p2 = select_parents(current_layouts, fitnesses)
        child = crossover_layout(p1, p2)
        child = mutate_layout(child, config)
        next_generation.append(child)

    return next_generation[:config["num_layouts_per_gen"]]