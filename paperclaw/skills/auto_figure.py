"""Auto Figure Skill - Generate figures from experiment data."""

from __future__ import annotations

from pathlib import Path
import json
import csv

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import register_skill


@register_skill
class AutoFigureSkill(Skill):
    """Automatically generate figures from experiment data.

    Input:
        - Data files (CSV, JSON) in project directory
        - Optional: specific data directory

    Output:
        - Generated figure files (PNG/PDF)
        - Figure metadata for spec integration
    """

    @property
    def name(self) -> str:
        return "auto-figure"

    @property
    def description(self) -> str:
        return "Generate figures from experiment data (CSV/JSON)"

    def execute(self, context: SkillContext) -> SkillResult:
        result = SkillResult(status=SkillStatus.SUCCESS)

        # Find data directory
        data_dir = context.config.get("data_dir")
        if data_dir:
            data_dir = Path(data_dir)
        else:
            # Look for common data directories
            for candidate in ["data", "experiment", "results", "."]:
                candidate_path = context.project_dir / candidate
                if candidate_path.exists() and candidate_path.is_dir():
                    data_dir = candidate_path
                    break

        if not data_dir or not data_dir.exists():
            result.add_message("No data directory found")
            return result

        # Create output directory
        output_dir = context.project_dir / "figures" / "auto"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find and process data files
        data_files = list(data_dir.glob("**/*.csv")) + list(data_dir.glob("**/*.json"))
        generated = []

        for data_file in data_files:
            try:
                fig_info = self._process_data_file(data_file, output_dir)
                if fig_info:
                    generated.append(fig_info)
                    result.artifacts.append(fig_info["path"])
            except Exception as e:
                result.add_error(f"Error processing {data_file.name}: {e}")

        result.data["generated_figures"] = generated
        result.metrics["files_processed"] = len(data_files)
        result.metrics["figures_generated"] = len(generated)
        result.add_message(f"Generated {len(generated)} figures from {len(data_files)} data files")

        return result

    def _process_data_file(self, data_file: Path, output_dir: Path) -> dict | None:
        """Process a data file and generate appropriate visualization."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            return None

        # Load data
        if data_file.suffix == ".csv":
            data = self._load_csv(data_file)
        else:
            data = self._load_json(data_file)

        if not data:
            return None

        # Detect data type and generate figure
        fig_type = self._detect_data_type(data, data_file.stem)
        if not fig_type:
            return None

        output_path = output_dir / f"{data_file.stem}.png"

        # Generate figure based on type
        plt.figure(figsize=(10, 6))

        if fig_type == "training_history":
            self._plot_training_history(data)
        elif fig_type == "model_comparison":
            self._plot_model_comparison(data)
        elif fig_type == "confusion_matrix":
            self._plot_confusion_matrix(data)
        elif fig_type == "ablation_study":
            self._plot_ablation_study(data)
        elif fig_type == "hyperparameter_search":
            self._plot_hyperparameter_search(data)
        else:
            plt.close()
            return None

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            "path": output_path,
            "type": fig_type,
            "source": str(data_file),
        }

    def _load_csv(self, path: Path) -> list[dict]:
        """Load CSV file."""
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _load_json(self, path: Path) -> list | dict:
        """Load JSON file."""
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _detect_data_type(self, data: list | dict, filename: str) -> str | None:
        """Detect the type of data for visualization."""
        filename_lower = filename.lower()

        # Check filename hints
        if "training" in filename_lower or "history" in filename_lower:
            return "training_history"
        if "comparison" in filename_lower or "model" in filename_lower:
            return "model_comparison"
        if "confusion" in filename_lower:
            return "confusion_matrix"
        if "ablation" in filename_lower:
            return "ablation_study"
        if "hyperparameter" in filename_lower or "grid" in filename_lower:
            return "hyperparameter_search"

        # Check data structure
        if isinstance(data, list) and data:
            keys = set(data[0].keys()) if isinstance(data[0], dict) else set()

            if {"epoch", "loss"} <= keys or {"epoch", "train_loss"} <= keys:
                return "training_history"
            if {"model", "accuracy"} <= keys or {"model", "f1"} <= keys:
                return "model_comparison"
            if {"config", "accuracy"} <= keys:
                return "ablation_study"

        return None

    def _plot_training_history(self, data: list[dict]) -> None:
        """Plot training history."""
        import matplotlib.pyplot as plt

        epochs = [int(d.get("epoch", i+1)) for i, d in enumerate(data)]

        # Plot available metrics
        for key in ["loss", "train_loss", "val_loss", "accuracy", "train_acc", "val_acc"]:
            values = [float(d[key]) for d in data if key in d]
            if values:
                style = '--' if 'train' in key else '-'
                plt.plot(epochs[:len(values)], values, style, label=key, linewidth=2)

        plt.xlabel('Epoch')
        plt.ylabel('Value')
        plt.title('Training History')
        plt.legend()
        plt.grid(True, alpha=0.3)

    def _plot_model_comparison(self, data: list[dict]) -> None:
        """Plot model comparison bar chart."""
        import matplotlib.pyplot as plt
        import numpy as np

        models = [d.get("model", f"Model {i+1}") for i, d in enumerate(data)]

        # Find numeric metrics
        metrics = {}
        for key in ["accuracy", "f1", "f1_score", "precision", "recall"]:
            values = [float(d[key]) for d in data if key in d]
            if values:
                metrics[key] = values

        if not metrics:
            return

        x = np.arange(len(models))
        width = 0.8 / len(metrics)

        for i, (metric, values) in enumerate(metrics.items()):
            offset = (i - len(metrics)/2 + 0.5) * width
            plt.bar(x + offset, values, width, label=metric)

        plt.xlabel('Model')
        plt.ylabel('Score')
        plt.title('Model Comparison')
        plt.xticks(x, models, rotation=45, ha='right')
        plt.legend()
        plt.ylim(0, 1.1)

    def _plot_confusion_matrix(self, data: list | dict) -> None:
        """Plot confusion matrix heatmap."""
        import matplotlib.pyplot as plt
        import numpy as np

        if isinstance(data, dict) and "matrix" in data:
            matrix = np.array(data["matrix"])
            labels = data.get("labels", [str(i) for i in range(len(matrix))])
        elif isinstance(data, list):
            matrix = np.array(data)
            labels = [str(i) for i in range(len(matrix))]
        else:
            return

        plt.imshow(matrix, cmap='Blues')
        plt.colorbar()

        for i in range(len(matrix)):
            for j in range(len(matrix[0])):
                color = 'white' if matrix[i, j] > matrix.max() / 2 else 'black'
                plt.text(j, i, str(matrix[i, j]), ha='center', va='center', color=color)

        plt.xticks(range(len(labels)), labels)
        plt.yticks(range(len(labels)), labels)
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix')

    def _plot_ablation_study(self, data: list[dict]) -> None:
        """Plot ablation study results."""
        import matplotlib.pyplot as plt

        configs = [d.get("config", f"Config {i+1}") for i, d in enumerate(data)]
        accuracy = [float(d.get("accuracy", d.get("f1", 0))) for d in data]

        colors = ['#4CAF50' if i == 0 else '#FF9800' for i in range(len(configs))]
        plt.barh(configs, accuracy, color=colors)
        plt.xlabel('Score')
        plt.title('Ablation Study')

    def _plot_hyperparameter_search(self, data: list[dict]) -> None:
        """Plot hyperparameter search results."""
        import matplotlib.pyplot as plt
        import numpy as np

        # Extract unique parameter values
        param_keys = [k for k in data[0].keys() if k not in ["accuracy", "f1", "score"]]
        if len(param_keys) < 2:
            return

        p1_key, p2_key = param_keys[:2]
        p1_vals = sorted(set(str(d[p1_key]) for d in data))
        p2_vals = sorted(set(str(d[p2_key]) for d in data))

        matrix = np.zeros((len(p1_vals), len(p2_vals)))
        for d in data:
            i = p1_vals.index(str(d[p1_key]))
            j = p2_vals.index(str(d[p2_key]))
            matrix[i, j] = float(d.get("accuracy", d.get("f1", d.get("score", 0))))

        plt.imshow(matrix, cmap='RdYlGn')
        plt.colorbar(label='Score')
        plt.xticks(range(len(p2_vals)), p2_vals)
        plt.yticks(range(len(p1_vals)), p1_vals)
        plt.xlabel(p2_key)
        plt.ylabel(p1_key)
        plt.title('Hyperparameter Search')
