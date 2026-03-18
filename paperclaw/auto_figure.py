"""Automatic figure generation from experiment data.

Analyzes experiment directories and generates appropriate visualizations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

logger = logging.getLogger(__name__)

# Configure matplotlib
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
})

# Colorblind-friendly palette
COLORS = ['#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE', '#AA3377', '#BBBBBB']


class AutoFigureGenerator:
    """Automatically generate figures from experiment data.

    Analyzes CSV, JSON files and generates appropriate visualizations:
    - Training curves (loss, accuracy over epochs)
    - Model comparison bar charts
    - Confusion matrices
    - Hyperparameter heatmaps
    - Scatter plots for trade-off analysis

    Usage:
        generator = AutoFigureGenerator(experiment_dir)
        figures = generator.generate_all()
        # figures = {'training_curves.png': Path, 'comparison.png': Path, ...}
    """

    def __init__(self, experiment_dir: str | Path, output_dir: str | Path | None = None):
        """Initialize figure generator.

        Args:
            experiment_dir: Path to experiment directory
            output_dir: Where to save figures (default: experiment_dir/figures)
        """
        self.experiment_dir = Path(experiment_dir)
        self.output_dir = Path(output_dir) if output_dir else self.experiment_dir / "figures"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.data_files: dict[str, Path] = {}
        self.generated_figures: dict[str, Path] = {}

    def scan_data_files(self) -> dict[str, list[Path]]:
        """Scan for data files in experiment directory."""
        files = {
            "csv": list(self.experiment_dir.rglob("*.csv")),
            "json": list(self.experiment_dir.rglob("*.json")),
        }
        logger.info(f"Found {len(files['csv'])} CSV and {len(files['json'])} JSON files")
        return files

    def detect_data_type(self, df: pd.DataFrame) -> str:
        """Detect the type of data in a DataFrame."""
        columns = [c.lower() for c in df.columns]

        # Training history
        if any(kw in columns for kw in ['epoch', 'step', 'iteration']):
            if any(kw in columns for kw in ['loss', 'train_loss', 'val_loss']):
                return 'training_history'
            if any(kw in columns for kw in ['accuracy', 'acc', 'train_acc', 'val_acc']):
                return 'training_history'

        # Model comparison
        if any(kw in columns for kw in ['model', 'model_name', 'experiment']):
            if any(kw in columns for kw in ['accuracy', 'f1', 'score', 'metric']):
                return 'model_comparison'

        # Hyperparameter search
        if any(kw in columns for kw in ['learning_rate', 'lr', 'batch_size', 'epochs']):
            if any(kw in columns for kw in ['accuracy', 'loss', 'score', 'val_accuracy']):
                return 'hyperparameter_search'

        # Cross-validation or cross-lingual
        if any(kw in columns for kw in ['fold', 'language', 'train_language', 'test_language']):
            return 'cross_validation'

        return 'unknown'

    def detect_json_type(self, data: dict | list) -> str:
        """Detect the type of data in a JSON file."""
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                keys = set(data[0].keys())
                if 'matrix' in keys or any('confusion' in str(k).lower() for k in keys):
                    return 'confusion_matrix'
                if 'type' in keys and 'count' in keys:
                    return 'error_analysis'
                if 'config' in keys and ('accuracy' in keys or 'f1' in keys):
                    return 'ablation_study'
            return 'list_data'

        if isinstance(data, dict):
            keys = set(data.keys())
            if 'matrix' in keys and 'labels' in keys:
                return 'confusion_matrix'
            if 'accuracy' in keys or 'f1' in keys or 'precision' in keys:
                return 'metrics'

        return 'unknown'

    def plot_training_curves(self, csv_files: list[Path]) -> Path | None:
        """Generate training curves from multiple training history files."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

        plotted = False
        for i, csv_path in enumerate(csv_files[:len(COLORS)]):
            try:
                df = pd.read_csv(csv_path)
                data_type = self.detect_data_type(df)

                if data_type != 'training_history':
                    continue

                # Find epoch/step column
                x_col = None
                for col in ['epoch', 'step', 'iteration']:
                    if col in df.columns.str.lower().tolist():
                        x_col = df.columns[df.columns.str.lower() == col][0]
                        break
                if x_col is None:
                    x_col = df.columns[0]

                # Find loss columns
                loss_cols = [c for c in df.columns if 'loss' in c.lower()]
                acc_cols = [c for c in df.columns if 'acc' in c.lower()]

                label = csv_path.parent.name if csv_path.parent != self.experiment_dir else csv_path.stem
                color = COLORS[i % len(COLORS)]

                # Plot loss
                for col in loss_cols:
                    style = '--' if 'train' in col.lower() else '-'
                    alpha = 0.6 if 'train' in col.lower() else 1.0
                    axes[0].plot(df[x_col], df[col], style, color=color,
                                alpha=alpha, linewidth=2, label=f'{label}')

                # Plot accuracy
                for col in acc_cols:
                    style = '--' if 'train' in col.lower() else '-'
                    alpha = 0.6 if 'train' in col.lower() else 1.0
                    axes[1].plot(df[x_col], df[col], style, color=color,
                                alpha=alpha, linewidth=2, label=f'{label}')

                plotted = True

            except Exception as e:
                logger.warning(f"Failed to process {csv_path}: {e}")

        if not plotted:
            plt.close()
            return None

        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('Training Loss')
        axes[0].legend()

        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Accuracy')
        axes[1].set_title('Training Accuracy')
        axes[1].legend()

        plt.tight_layout()
        output_path = self.output_dir / 'training_curves.png'
        plt.savefig(output_path)
        plt.savefig(self.output_dir / 'training_curves.pdf')
        plt.close()

        self.generated_figures['training_curves'] = output_path
        return output_path

    def plot_model_comparison(self, df: pd.DataFrame, source_path: Path) -> Path | None:
        """Generate model comparison bar chart."""
        # Find model column
        model_col = None
        for col in ['model', 'model_name', 'experiment', 'name']:
            if col in df.columns.str.lower().tolist():
                model_col = df.columns[df.columns.str.lower() == col][0]
                break

        if model_col is None:
            return None

        # Find metric columns
        metric_cols = [c for c in df.columns if any(
            kw in c.lower() for kw in ['accuracy', 'f1', 'precision', 'recall', 'score']
        )]

        if not metric_cols:
            return None

        n_metrics = min(len(metric_cols), 3)
        fig, axes = plt.subplots(1, n_metrics, figsize=(5 * n_metrics, 4.5))
        if n_metrics == 1:
            axes = [axes]

        models = df[model_col].tolist()
        x = np.arange(len(models))

        for i, col in enumerate(metric_cols[:n_metrics]):
            bars = axes[i].bar(x, df[col], color=COLORS[:len(models)],
                              edgecolor='white', linewidth=1)
            axes[i].set_ylabel(col)
            axes[i].set_title(col.replace('_', ' ').title())
            axes[i].set_xticks(x)
            axes[i].set_xticklabels(models, rotation=15, ha='right')
            axes[i].bar_label(bars, fmt='%.3f', padding=3, fontsize=9)

        plt.tight_layout()
        output_path = self.output_dir / 'model_comparison.png'
        plt.savefig(output_path)
        plt.savefig(self.output_dir / 'model_comparison.pdf')
        plt.close()

        self.generated_figures['model_comparison'] = output_path
        return output_path

    def plot_confusion_matrix(self, data: dict, source_path: Path) -> Path | None:
        """Generate confusion matrix heatmap."""
        if 'matrix' not in data or 'labels' not in data:
            return None

        cm = np.array(data['matrix'])
        labels = data['labels']

        # Normalize
        cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(cm_norm, cmap='Blues', vmin=0, vmax=1)

        # Add colorbar
        plt.colorbar(im, ax=ax, label='Proportion')

        # Add text annotations
        for i in range(len(labels)):
            for j in range(len(labels)):
                color = 'white' if cm_norm[i, j] > 0.5 else 'black'
                ax.text(j, i, f'{cm_norm[i, j]:.2f}\n({cm[i, j]})',
                       ha='center', va='center', color=color, fontsize=10)

        ax.set_xticks(np.arange(len(labels)))
        ax.set_yticks(np.arange(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_yticklabels(labels)
        ax.set_xlabel('Predicted')
        ax.set_ylabel('True')
        ax.set_title('Confusion Matrix')

        plt.tight_layout()
        output_path = self.output_dir / f'confusion_matrix_{source_path.stem}.png'
        plt.savefig(output_path)
        plt.savefig(self.output_dir / f'confusion_matrix_{source_path.stem}.pdf')
        plt.close()

        self.generated_figures[f'confusion_matrix_{source_path.stem}'] = output_path
        return output_path

    def plot_hyperparameter_heatmap(self, df: pd.DataFrame, source_path: Path) -> Path | None:
        """Generate hyperparameter search heatmap."""
        # Find hyperparameter and metric columns
        hp_cols = [c for c in df.columns if any(
            kw in c.lower() for kw in ['learning_rate', 'lr', 'batch_size', 'epochs', 'dropout']
        )]
        metric_cols = [c for c in df.columns if any(
            kw in c.lower() for kw in ['accuracy', 'loss', 'f1', 'score']
        )]

        if len(hp_cols) < 2 or not metric_cols:
            return None

        # Create pivot table
        try:
            pivot = df.groupby([hp_cols[0], hp_cols[1]])[metric_cols[0]].mean().unstack()
        except Exception:
            return None

        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto')

        plt.colorbar(im, ax=ax, label=metric_cols[0])

        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_xticklabels([str(x) for x in pivot.columns])
        ax.set_yticklabels([f'{x:.0e}' if isinstance(x, float) and x < 0.01 else str(x)
                          for x in pivot.index])

        # Add text annotations
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot.values[i, j]
                if not np.isnan(val):
                    color = 'white' if val < pivot.values[~np.isnan(pivot.values)].mean() else 'black'
                    ax.text(j, i, f'{val:.3f}', ha='center', va='center', color=color, fontsize=9)

        ax.set_xlabel(hp_cols[1])
        ax.set_ylabel(hp_cols[0])
        ax.set_title('Hyperparameter Search Results')

        plt.tight_layout()
        output_path = self.output_dir / 'hyperparameter_search.png'
        plt.savefig(output_path)
        plt.savefig(self.output_dir / 'hyperparameter_search.pdf')
        plt.close()

        self.generated_figures['hyperparameter_search'] = output_path
        return output_path

    def plot_ablation_study(self, data: list[dict], source_path: Path) -> Path | None:
        """Generate ablation study horizontal bar chart."""
        if not data or not isinstance(data[0], dict):
            return None

        # Check for required keys
        if 'config' not in data[0] or ('accuracy' not in data[0] and 'f1' not in data[0]):
            return None

        configs = [d.get('config', d.get('name', f'Config {i}')) for i, d in enumerate(data)]
        metric_key = 'accuracy' if 'accuracy' in data[0] else 'f1'
        values = [d.get(metric_key, 0) for d in data]

        fig, ax = plt.subplots(figsize=(10, 6))

        # Color: first green, middle orange, last red
        colors = ['#228833'] + ['#CCBB44'] * (len(configs) - 2) + ['#EE6677']
        if len(configs) <= 2:
            colors = ['#228833', '#EE6677'][:len(configs)]

        bars = ax.barh(configs, values, color=colors, edgecolor='white', linewidth=1)

        ax.set_xlabel(metric_key.title())
        ax.set_title('Ablation Study')

        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.002, bar.get_y() + bar.get_height()/2,
                   f'{width:.3f}', va='center', fontsize=9)

        plt.tight_layout()
        output_path = self.output_dir / 'ablation_study.png'
        plt.savefig(output_path)
        plt.savefig(self.output_dir / 'ablation_study.pdf')
        plt.close()

        self.generated_figures['ablation_study'] = output_path
        return output_path

    def plot_error_analysis(self, data: list[dict], source_path: Path) -> Path | None:
        """Generate error analysis bar chart."""
        if not data or not isinstance(data[0], dict):
            return None

        if 'type' not in data[0] or 'count' not in data[0]:
            return None

        types = [d['type'] for d in data]
        counts = [d['count'] for d in data]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.Set3(np.linspace(0, 1, len(types)))
        bars = ax.barh(types, counts, color=colors, edgecolor='white', linewidth=1)

        ax.set_xlabel('Count')
        ax.set_title('Error Analysis')

        # Add count and percentage labels
        total = sum(counts)
        for bar, count in zip(bars, counts):
            pct = count / total * 100
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                   f'{int(count)} ({pct:.1f}%)', va='center', fontsize=9)

        plt.tight_layout()
        output_path = self.output_dir / 'error_analysis.png'
        plt.savefig(output_path)
        plt.savefig(self.output_dir / 'error_analysis.pdf')
        plt.close()

        self.generated_figures['error_analysis'] = output_path
        return output_path

    def generate_all(self) -> dict[str, Path]:
        """Generate all possible figures from experiment data.

        Returns:
            Dictionary mapping figure names to their paths
        """
        logger.info(f"Scanning experiment directory: {self.experiment_dir}")
        files = self.scan_data_files()

        # Process CSV files
        training_files = []
        comparison_file = None
        hp_file = None

        for csv_path in files['csv']:
            try:
                df = pd.read_csv(csv_path)
                data_type = self.detect_data_type(df)

                if data_type == 'training_history':
                    training_files.append(csv_path)
                elif data_type == 'model_comparison':
                    if comparison_file is None:
                        comparison_file = (df, csv_path)
                elif data_type == 'hyperparameter_search':
                    if hp_file is None:
                        hp_file = (df, csv_path)

            except Exception as e:
                logger.warning(f"Failed to process {csv_path}: {e}")

        # Generate training curves
        if training_files:
            logger.info("Generating training curves...")
            self.plot_training_curves(training_files)

        # Generate model comparison
        if comparison_file:
            logger.info("Generating model comparison...")
            self.plot_model_comparison(*comparison_file)

        # Generate hyperparameter search
        if hp_file:
            logger.info("Generating hyperparameter search...")
            self.plot_hyperparameter_heatmap(*hp_file)

        # Process JSON files
        for json_path in files['json']:
            try:
                with open(json_path) as f:
                    data = json.load(f)

                data_type = self.detect_json_type(data)

                if data_type == 'confusion_matrix':
                    logger.info(f"Generating confusion matrix from {json_path.name}...")
                    self.plot_confusion_matrix(data, json_path)
                elif data_type == 'ablation_study':
                    logger.info("Generating ablation study...")
                    self.plot_ablation_study(data, json_path)
                elif data_type == 'error_analysis':
                    logger.info("Generating error analysis...")
                    self.plot_error_analysis(data, json_path)

            except Exception as e:
                logger.warning(f"Failed to process {json_path}: {e}")

        logger.info(f"Generated {len(self.generated_figures)} figures")
        return self.generated_figures


def generate_figures_for_project(experiment_dir: str | Path, output_dir: str | Path | None = None) -> dict[str, Path]:
    """Convenience function to generate figures.

    Args:
        experiment_dir: Path to experiment directory
        output_dir: Where to save figures

    Returns:
        Dictionary mapping figure names to paths
    """
    generator = AutoFigureGenerator(experiment_dir, output_dir)
    return generator.generate_all()
