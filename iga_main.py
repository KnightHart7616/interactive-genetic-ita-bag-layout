import os
import json
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageTk

from layout_utils import generate_layout_with_adjustment
from evolution import create_next_generation
from render_utils import draw_layout, save_layout_png
from aesthetic_score import auto_aesthetic_score


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    return load_json("config.json")


def load_object_list(path):
    objects = load_json(path)
    return sorted(objects, key=lambda o: o["w"] * o["h"], reverse=True)


def load_precomputed_backgrounds(path, k):
    data = load_json(path)
    sorted_bg = sorted(data["background_scores"], key=lambda x: x["distance"])
    return [item["filename"] for item in sorted_bg[:k]]


def list_json_files(folder):
    if not os.path.exists(folder):
        return []
    return sorted([f for f in os.listdir(folder) if f.lower().endswith(".json")])


def infer_bg_analysis_from_object_list(object_list_filename):
    if not object_list_filename.startswith("object_list_"):
        return None
    suffix = object_list_filename[len("object_list_"):]
    return f"bg_analysis_{suffix}"


def make_run_directory(config):
    results_folder = config["results_folder"]
    os.makedirs(results_folder, exist_ok=True)

    object_list_name = os.path.splitext(os.path.basename(config["object_list_path"]))[0]
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")

    run_name = f"run_{timestamp}_{object_list_name}"
    run_dir = os.path.join(results_folder, run_name)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def save_run_snapshots(config, run_dir):
    config_snapshot_path = os.path.join(run_dir, "config_snapshot.json")
    object_snapshot_path = os.path.join(run_dir, "object_list_snapshot.json")
    bg_snapshot_path = os.path.join(run_dir, "bg_analysis_snapshot.json")

    with open(config_snapshot_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    shutil.copyfile(config["object_list_path"], object_snapshot_path)
    shutil.copyfile(config["bg_analysis_path"], bg_snapshot_path)

    print(f"✅ Saved config snapshot: {config_snapshot_path}")
    print(f"✅ Saved object list snapshot: {object_snapshot_path}")
    print(f"✅ Saved bg analysis snapshot: {bg_snapshot_path}")


class IGAGUI:
    def __init__(self, master, config, objects, backgrounds, object_list_filename, bg_analysis_filename, run_dir):
        self.master = master
        self.config_data = config
        self.objects = objects
        self.backgrounds = backgrounds
        self.object_list_filename = object_list_filename
        self.bg_analysis_filename = bg_analysis_filename
        self.run_dir = run_dir

        self.master.title("IGA Ita Bag Layout Tool")

        self.generation = 0
        self.layouts = []
        self.current_layout_index = 0
        self.scores = [3] * config["num_layouts_per_gen"]

        self.best_layout = None
        self.best_score = None
        self.best_background = None
        self.best_fitness = -1
        self.best_generation = None

        self.score_history = []
        self.background_usage = {}

        self.auto_weight = 0.4
        self.user_weight = 0.6

        self.available_object_lists = list_json_files("object_lists")
        self.available_bg_analysis = list_json_files("bg_analysis")

        self.selected_object_list = tk.StringVar(value=self.object_list_filename)
        self.selected_bg_analysis = tk.StringVar(value=self.bg_analysis_filename)

        tk.Label(master, text="Object List:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.object_list_dropdown = ttk.Combobox(
            master,
            textvariable=self.selected_object_list,
            values=self.available_object_lists,
            state="readonly",
            width=30
        )
        self.object_list_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        tk.Label(master, text="BG Analysis:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.bg_analysis_dropdown = ttk.Combobox(
            master,
            textvariable=self.selected_bg_analysis,
            values=self.available_bg_analysis,
            state="readonly",
            width=30
        )
        self.bg_analysis_dropdown.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        tk.Button(master, text="Reload Combination", command=self.reload_combination).grid(
            row=2, column=0, columnspan=2, pady=5
        )

        self.object_list_dropdown.bind("<<ComboboxSelected>>", self.on_object_list_change)

        self.info_label = tk.Label(master, text="", font=("Arial", 11))
        self.info_label.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        self.img_label = tk.Label(master)
        self.img_label.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        tk.Button(master, text="← Previous Layout", command=self.prev_layout).grid(row=5, column=0)
        tk.Button(master, text="Next Layout →", command=self.next_layout).grid(row=5, column=1)

        self.score_var = tk.StringVar(value="Normal")
        self.score_dropdown = ttk.Combobox(
            master,
            textvariable=self.score_var,
            values=["Bad", "Normal", "Good"],
            state="readonly"
        )
        self.score_dropdown.grid(row=6, column=0, columnspan=2, pady=5)

        tk.Button(master, text="← Previous BG", command=self.prev_bg).grid(row=7, column=0)
        tk.Button(master, text="Next BG →", command=self.next_bg).grid(row=7, column=1)

        tk.Button(master, text="Submit Generation", command=self.submit_generation).grid(
            row=8, column=0, columnspan=2, pady=10
        )

        tk.Button(master, text="Save Current PNG", command=self.save_current_png).grid(
            row=9, column=0, columnspan=2, pady=5
        )

        self.stats_label = tk.Label(master, text="", font=("Arial", 10))
        self.stats_label.grid(row=10, column=0, columnspan=2, pady=(5, 10))

        self.bg_name_label = tk.Label(master, text="", font=("Arial", 10))
        self.bg_name_label.grid(row=11, column=0, columnspan=2, pady=(2, 0))

        self.score_info_label = tk.Label(master, text="", font=("Arial", 10))
        self.score_info_label.grid(row=12, column=0, columnspan=2, pady=(2, 0))

        self.status_label = tk.Label(master, text="", font=("Arial", 10))
        self.status_label.grid(row=13, column=0, columnspan=2, pady=(2, 10))

        tk.Button(master, text="Preview Best Result", command=self.preview_best_result).grid(
            row=14, column=0, columnspan=2, pady=5
        )

        tk.Button(master, text="Save All Current Previews", command=self.save_all_current_previews).grid(
            row=15, column=0, columnspan=2, pady=5
        )

        self.start_first_generation()

    def build_layout_entry(self, layout):
        return {
            "layout": layout,
            "bg_options": self.backgrounds or [None],
            "bg_index": 0
        }

    def score_to_text(self, score):
        mapping = {1: "Bad", 3: "Normal", 5: "Good"}
        return mapping.get(score, "Unknown")

    def normalize_user_score(self, score):
        return (score - 1) / 4

    def on_object_list_change(self, event=None):
        inferred = infer_bg_analysis_from_object_list(self.selected_object_list.get())
        if inferred in self.available_bg_analysis:
            self.selected_bg_analysis.set(inferred)

    def reload_combination(self):
        object_list_filename = self.selected_object_list.get()
        bg_analysis_filename = self.selected_bg_analysis.get()

        try:
            new_objects = load_object_list(os.path.join("object_lists", object_list_filename))
            new_backgrounds = load_precomputed_backgrounds(
                os.path.join("bg_analysis", bg_analysis_filename),
                self.config_data["top_k_backgrounds"]
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload combination:\n{e}")
            return

        self.objects = new_objects
        self.backgrounds = new_backgrounds
        self.object_list_filename = object_list_filename
        self.bg_analysis_filename = bg_analysis_filename

        self.config_data["object_list_path"] = os.path.join("object_lists", object_list_filename)
        self.config_data["bg_analysis_path"] = os.path.join("bg_analysis", bg_analysis_filename)

        self.run_dir = make_run_directory(self.config_data)
        save_run_snapshots(self.config_data, self.run_dir)

        self.generation = 0
        self.layouts = []
        self.current_layout_index = 0
        self.scores = [3] * self.config_data["num_layouts_per_gen"]
        self.best_layout = None
        self.best_background = None
        self.best_score = None
        self.best_fitness = -1
        self.best_generation = None
        self.score_history = []
        self.background_usage = {}

        self.start_first_generation()

        messagebox.showinfo("Reloaded", f"Loaded:\n{object_list_filename}\n{bg_analysis_filename}")

    def start_first_generation(self):
        self.generation = 1
        self.layouts = []

        for _ in range(self.config_data["num_layouts_per_gen"]):
            layout = generate_layout_with_adjustment(self.objects, self.config_data)
            self.layouts.append(self.build_layout_entry(layout))

        self.current_layout_index = 0
        self.scores = [3] * len(self.layouts)
        self.update_display()

    def start_next_generation(self, next_layouts):
        self.generation += 1
        self.layouts = [self.build_layout_entry(layout) for layout in next_layouts]
        self.current_layout_index = 0
        self.scores = [3] * len(self.layouts)
        self.update_display()

    def get_current_data(self):
        return self.layouts[self.current_layout_index]

    def update_display(self):
        data = self.get_current_data()
        bg_file = data["bg_options"][data["bg_index"]]

        rendered = draw_layout(data["layout"], bg_file, self.config_data)
        self.tk_img = ImageTk.PhotoImage(rendered)
        self.img_label.config(image=self.tk_img)

        self.info_label.config(
            text=(
                f"Generation {self.generation}/{self.config_data['total_generations']} | "
                f"Layout {self.current_layout_index + 1}/{len(self.layouts)} | "
                f"Background {data['bg_index'] + 1}/{len(data['bg_options'])}"
            )
        )

        self.score_var.set(self.score_to_text(self.scores[self.current_layout_index]))

        bg_name = bg_file if bg_file is not None else "white_background"
        self.bg_name_label.config(text=f"Background: {bg_name}")

        user_score = data.get("user_score", "-")
        auto_score = data.get("auto_score", "-")
        final_fitness = data.get("final_fitness", "-")

        if isinstance(auto_score, float):
            auto_score = f"{auto_score:.4f}"
        if isinstance(final_fitness, float):
            final_fitness = f"{final_fitness:.4f}"

        self.score_info_label.config(
            text=f"User Score: {user_score} | Auto Score: {auto_score} | Final Fitness: {final_fitness}"
        )

        if "user_score" in data:
            self.status_label.config(text="Status: Scored")
        else:
            self.status_label.config(text="Status: Not Scored Yet")

        if self.score_history:
            latest = self.score_history[-1]
            self.stats_label.config(
                text=(
                    f"Last Gen Stats | "
                    f"Best Fitness: {latest['best_fitness']:.4f} | "
                    f"Avg Fitness: {latest['avg_fitness']:.4f}"
                )
            )
        else:
            self.stats_label.config(text="No generation statistics yet.")

    def prev_layout(self):
        self.save_score()
        if self.current_layout_index > 0:
            self.current_layout_index -= 1
            self.update_display()

    def next_layout(self):
        self.save_score()
        if self.current_layout_index < len(self.layouts) - 1:
            self.current_layout_index += 1
            self.update_display()

    def prev_bg(self):
        data = self.get_current_data()
        if data["bg_index"] > 0:
            data["bg_index"] -= 1
            self.update_display()

    def next_bg(self):
        data = self.get_current_data()
        if data["bg_index"] < len(data["bg_options"]) - 1:
            data["bg_index"] += 1
            self.update_display()

    def save_score(self):
        mapping = {"Bad": 1, "Normal": 3, "Good": 5}
        score = mapping[self.score_var.get()]
        self.scores[self.current_layout_index] = score
        self.layouts[self.current_layout_index]["user_score"] = score

    def compute_fitnesses(self):
        fitnesses = []

        for i, entry in enumerate(self.layouts):
            auto_score = auto_aesthetic_score(
                entry["layout"],
                self.config_data["canvas_width"],
                self.config_data["canvas_height"]
            )
            user_score_norm = self.normalize_user_score(self.scores[i])

            final_score = (
                self.auto_weight * auto_score +
                self.user_weight * user_score_norm
            )

            entry["auto_score"] = round(auto_score, 4)
            entry["user_score"] = self.scores[i]
            entry["final_fitness"] = round(final_score, 4)

            fitnesses.append(final_score)

        return fitnesses

    def record_best(self):
        for entry in self.layouts:
            fitness = entry.get("final_fitness", 0)
            if fitness > self.best_fitness:
                self.best_fitness = fitness
                self.best_layout = entry["layout"]
                self.best_background = entry["bg_options"][entry["bg_index"]]
                self.best_generation = self.generation
                self.best_score = {
                    "user_score": entry.get("user_score"),
                    "auto_score": entry.get("auto_score"),
                    "final_fitness": entry.get("final_fitness")
                }

    def record_generation_stats(self):
        user_scores = [entry.get("user_score", 0) for entry in self.layouts]
        auto_scores = [entry.get("auto_score", 0) for entry in self.layouts]
        fitnesses = [entry.get("final_fitness", 0) for entry in self.layouts]

        stat = {
            "generation": self.generation,
            "best_user_score": max(user_scores) if user_scores else 0,
            "avg_user_score": round(sum(user_scores) / len(user_scores), 4) if user_scores else 0,
            "best_auto_score": max(auto_scores) if auto_scores else 0,
            "avg_auto_score": round(sum(auto_scores) / len(auto_scores), 4) if auto_scores else 0,
            "best_fitness": max(fitnesses) if fitnesses else 0,
            "avg_fitness": round(sum(fitnesses) / len(fitnesses), 4) if fitnesses else 0
        }

        self.score_history.append(stat)

        for entry in self.layouts:
            bg = entry["bg_options"][entry["bg_index"]]
            if bg is None:
                bg = "white_background"
            self.background_usage[bg] = self.background_usage.get(bg, 0) + 1

    def save_generation_json(self):
        output = []
        for data in self.layouts:
            output.append({
                "layout": data["layout"],
                "background": data["bg_options"][data["bg_index"]],
                "user_score": data.get("user_score"),
                "auto_score": data.get("auto_score"),
                "final_fitness": data.get("final_fitness")
            })

        output_path = os.path.join(self.run_dir, f"gen_{self.generation:02d}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved {output_path}")

    def save_current_png(self):
        data = self.get_current_data()
        bg_file = data["bg_options"][data["bg_index"]]
        save_path = os.path.join(
            self.run_dir,
            f"generation_{self.generation:02d}_layout_{self.current_layout_index + 1}.png"
        )
        save_layout_png(data["layout"], bg_file, self.config_data, save_path)
        messagebox.showinfo("Saved", f"Saved current layout to:\n{save_path}")

    def save_all_current_previews(self):
        save_dir = os.path.join(
            self.run_dir,
            f"generation_{self.generation:02d}_previews"
        )
        os.makedirs(save_dir, exist_ok=True)

        for idx, data in enumerate(self.layouts, start=1):
            bg_file = data["bg_options"][data["bg_index"]]
            save_path = os.path.join(save_dir, f"layout_{idx:02d}.png")
            save_layout_png(data["layout"], bg_file, self.config_data, save_path)

        messagebox.showinfo("Saved", f"Saved all current previews to:\n{save_dir}")

    def preview_best_result(self):
        if self.best_layout is None:
            messagebox.showwarning("Warning", "No best result available yet.")
            return

        preview_window = tk.Toplevel(self.master)
        preview_window.title("Best Result Preview")

        rendered = draw_layout(self.best_layout, self.best_background, self.config_data)
        tk_img = ImageTk.PhotoImage(rendered)

        label = tk.Label(preview_window, image=tk_img)
        label.image = tk_img
        label.pack(padx=10, pady=10)

        info = tk.Label(
            preview_window,
            text=(
                f"Best Fitness: {self.best_fitness:.4f}\n"
                f"Background: {self.best_background if self.best_background else 'white_background'}"
            ),
            font=("Arial", 10)
        )
        info.pack(pady=(0, 10))

    def save_best_result(self):
        if self.best_layout is None:
            return

        best_json = os.path.join(self.run_dir, "best_layout.json")
        best_png = os.path.join(self.run_dir, "best_layout.png")

        with open(best_json, "w", encoding="utf-8") as f:
            json.dump({
                "layout": self.best_layout,
                "background": self.best_background,
                "score_info": self.best_score
            }, f, indent=2, ensure_ascii=False)

        save_layout_png(self.best_layout, self.best_background, self.config_data, best_png)

        print(f"✅ Saved best layout JSON: {best_json}")
        print(f"✅ Saved best layout PNG: {best_png}")

    def save_statistics(self):
        score_history_path = os.path.join(self.run_dir, "score_history.json")
        background_usage_path = os.path.join(self.run_dir, "background_usage.json")

        with open(score_history_path, "w", encoding="utf-8") as f:
            json.dump(self.score_history, f, indent=2, ensure_ascii=False)

        with open(background_usage_path, "w", encoding="utf-8") as f:
            json.dump(self.background_usage, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved score history: {score_history_path}")
        print(f"✅ Saved background usage: {background_usage_path}")

    def get_most_used_background(self):
        if not self.background_usage:
            return None, 0
        bg, count = max(self.background_usage.items(), key=lambda x: x[1])
        return bg, count

    def save_run_summary_json(self):
        summary_path = os.path.join(self.run_dir, "run_summary.json")

        most_used_bg, most_used_count = self.get_most_used_background()

        avg_fitness_trend = [item["avg_fitness"] for item in self.score_history]
        best_fitness_trend = [item["best_fitness"] for item in self.score_history]

        summary = {
            "object_list_file": self.object_list_filename,
            "bg_analysis_file": self.bg_analysis_filename,
            "total_generations": self.generation,
            "best_generation": self.best_generation,
            "best_background": self.best_background,
            "best_score_info": self.best_score,
            "most_used_background": {
                "filename": most_used_bg,
                "count": most_used_count
            },
            "avg_fitness_trend": avg_fitness_trend,
            "best_fitness_trend": best_fitness_trend
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved run summary JSON: {summary_path}")

    def save_run_summary_txt(self):
        summary_path = os.path.join(self.run_dir, "run_summary.txt")

        most_used_bg, most_used_count = self.get_most_used_background()

        avg_fitness_trend = [item["avg_fitness"] for item in self.score_history]
        best_fitness_trend = [item["best_fitness"] for item in self.score_history]

        lines = []
        lines.append("IGA Run Summary")
        lines.append("=" * 40)
        lines.append(f"Object List File: {self.object_list_filename}")
        lines.append(f"BG Analysis File: {self.bg_analysis_filename}")
        lines.append(f"Total Generations: {self.generation}")
        lines.append(f"Best Generation: {self.best_generation}")
        lines.append(f"Best Background: {self.best_background}")
        lines.append(f"Best User Score: {self.best_score.get('user_score') if self.best_score else None}")
        lines.append(f"Best Auto Score: {self.best_score.get('auto_score') if self.best_score else None}")
        lines.append(f"Best Final Fitness: {self.best_score.get('final_fitness') if self.best_score else None}")
        lines.append("")
        lines.append(f"Most Used Background: {most_used_bg}")
        lines.append(f"Most Used Background Count: {most_used_count}")
        lines.append("")
        lines.append("Average Fitness Trend:")
        lines.append(", ".join(str(v) for v in avg_fitness_trend))
        lines.append("")
        lines.append("Best Fitness Trend:")
        lines.append(", ".join(str(v) for v in best_fitness_trend))

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✅ Saved run summary TXT: {summary_path}")

    def submit_generation(self):
        self.save_score()

        fitnesses = self.compute_fitnesses()
        self.update_display()

        for i, entry in enumerate(self.layouts):
            print(
                f"Layout {i+1} | "
                f"user={entry['user_score']} | "
                f"auto={entry['auto_score']:.4f} | "
                f"fitness={entry['final_fitness']:.4f}"
            )

        self.record_generation_stats()
        self.save_generation_json()
        self.record_best()

        if self.generation >= self.config_data["total_generations"]:
            self.save_best_result()
            self.save_statistics()
            self.save_run_summary_json()
            self.save_run_summary_txt()
            messagebox.showinfo("Done", "All generations completed.")
            self.master.quit()
            return

        current_layouts = [entry["layout"] for entry in self.layouts]
        next_layouts = create_next_generation(current_layouts, fitnesses, self.config_data)
        self.start_next_generation(next_layouts)


def main():
    config = load_config()

    objects = load_object_list(config["object_list_path"])
    backgrounds = load_precomputed_backgrounds(
        config["bg_analysis_path"],
        config["top_k_backgrounds"]
    )

    run_dir = make_run_directory(config)
    save_run_snapshots(config, run_dir)

    root = tk.Tk()

    object_list_filename = os.path.basename(config["object_list_path"])
    bg_analysis_filename = os.path.basename(config["bg_analysis_path"])

    app = IGAGUI(
        root,
        config,
        objects,
        backgrounds,
        object_list_filename,
        bg_analysis_filename,
        run_dir
    )

    root.mainloop()


if __name__ == "__main__":
    main()