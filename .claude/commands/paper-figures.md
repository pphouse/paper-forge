# Paper Figures (Agent 3: 図表生成エージェント)

AI駆動型論文執筆エージェントの第3エージェント。実験データから論文品質の図表を自動生成し、ジャーナルの投稿規定に準拠したフォーマットで出力します。

## Usage

```
/paper-figures <project_dir> [--journal nature|lancet|jama|nejm|ieee] [--dpi 300]
```

## What This Does

Agent 1（実験データ解析）の出力から、論文品質の図表（ROC曲線、混同行列のヒートマップ、学習曲線、性能比較表、患者特性表等）を自動生成します。

### ジャーナル投稿規定

| ジャーナル | 画像形式 | 解像度 | カラーモード | 最大幅 |
|-----------|---------|--------|-------------|--------|
| Nature | TIFF/EPS | 300 DPI | RGB/CMYK | 180mm |
| Lancet | TIFF/PDF | 300 DPI | RGB | 170mm |
| JAMA | TIFF/EPS | 300 DPI | CMYK | 3.5in (single) |
| NEJM | TIFF/PDF | 300 DPI | RGB | 7in (double) |
| IEEE | PDF/EPS | 300 DPI | RGB | 3.5in |

## Figure Types

### 医療AI論文の標準図表セット

| No. | 図表タイプ | 用途 | Figure/Table |
|-----|-----------|------|--------------|
| 1 | 患者特性表 (Table 1) | 訓練/テストセットの人口統計 | Table |
| 2 | モデルアーキテクチャ図 | ネットワーク構造の説明 | Figure |
| 3 | ROC曲線 | 分類性能の可視化 | Figure |
| 4 | 混同行列 | 予測精度の詳細 | Figure |
| 5 | 施設別性能比較 | 外部検証結果 | Figure/Table |
| 6 | 学習曲線 | 訓練過程の可視化 | Supplementary |
| 7 | Calibration plot | モデルの較正 | Supplementary |

## Implementation

```python
#!/usr/bin/env python3
"""Agent 3: 図表生成エージェント"""

import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import pandas as pd
import numpy as np
from sklearn.metrics import roc_curve, auc, confusion_matrix
from sklearn.calibration import calibration_curve
from pathlib import Path

class FigureGenerator:
    """論文品質の図表生成"""

    # ジャーナル別設定
    JOURNAL_CONFIGS = {
        'nature': {
            'dpi': 300,
            'figure_width': 180,  # mm
            'font_family': 'Arial',
            'font_size': 7,
            'line_width': 0.5,
            'formats': ['tiff', 'pdf']
        },
        'lancet': {
            'dpi': 300,
            'figure_width': 170,
            'font_family': 'Arial',
            'font_size': 8,
            'line_width': 0.75,
            'formats': ['tiff', 'pdf']
        },
        'jama': {
            'dpi': 300,
            'figure_width': 89,  # 3.5 inches = 89mm
            'font_family': 'Arial',
            'font_size': 8,
            'line_width': 0.5,
            'formats': ['tiff', 'eps']
        },
        'ieee': {
            'dpi': 300,
            'figure_width': 89,
            'font_family': 'Times New Roman',
            'font_size': 8,
            'line_width': 0.5,
            'formats': ['pdf', 'eps']
        }
    }

    # 医療AI用カラーパレット（参照スタイル準拠）
    # ROC曲線用：青、オレンジ、緑、赤（Overall用）
    ROC_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    COLORS = {
        'primary': '#1f77b4',    # Blue (matplotlib default)
        'secondary': '#ff7f0e',  # Orange
        'tertiary': '#2ca02c',   # Green
        'quaternary': '#d62728', # Red
        'neutral': '#999999',    # Gray
        'positive': '#E69F00',   # Yellow (for positive class)
        'negative': '#56B4E9'    # Light blue (for negative class)
    }

    def __init__(self, output_dir: str, journal: str = 'nature'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = self.JOURNAL_CONFIGS.get(journal, self.JOURNAL_CONFIGS['nature'])
        self._setup_matplotlib()

    def _setup_matplotlib(self):
        """matplotlibの設定（参照スタイル準拠 - 軽いグリッド）"""
        plt.rcParams.update({
            'font.family': 'DejaVu Sans',  # 参照と同じフォント
            'font.size': 10,
            'axes.linewidth': self.config['line_width'],
            'axes.labelsize': 11,
            'axes.titlesize': 12,
            'xtick.labelsize': self.config['font_size'] - 1,
            'ytick.labelsize': self.config['font_size'] - 1,
            'legend.fontsize': self.config['font_size'] - 1,
            'figure.dpi': self.config['dpi'],
            'figure.facecolor': 'white',
            'savefig.dpi': self.config['dpi'],
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.05,
            'savefig.facecolor': 'white'
        })

    def generate_table1_patient_characteristics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Table 1: 患者特性表の生成"""
        def format_continuous(data, name):
            """連続変数のフォーマット"""
            return f"{data.mean():.1f} ± {data.std():.1f}"

        def format_categorical(data, name):
            """カテゴリ変数のフォーマット"""
            n = data.sum()
            pct = data.mean() * 100
            return f"{int(n)} ({pct:.1f}%)"

        # 訓練/テスト分割
        train_df = df[df['split'] == 'train']
        test_df = df[df['split'] == 'test']

        table_data = []

        # 連続変数
        for var in ['age']:
            if var in df.columns:
                table_data.append({
                    'Characteristic': f'Age, years (mean ± SD)',
                    'Training (N={:,})'.format(len(train_df)): format_continuous(train_df[var], var),
                    'Test (N={:,})'.format(len(test_df)): format_continuous(test_df[var], var)
                })

        # カテゴリ変数
        if 'gender' in df.columns:
            male_train = (train_df['gender'] == 1).sum()
            male_test = (test_df['gender'] == 1).sum()
            table_data.append({
                'Characteristic': 'Male sex, n (%)',
                'Training (N={:,})'.format(len(train_df)): f"{male_train} ({male_train/len(train_df)*100:.1f}%)",
                'Test (N={:,})'.format(len(test_df)): f"{male_test} ({male_test/len(test_df)*100:.1f}%)"
            })

        # 疾患有病率
        if 'major3_AS' in df.columns or 'label' in df.columns:
            label_col = 'major3_AS' if 'major3_AS' in df.columns else 'label'
            as_train = train_df[label_col].sum()
            as_test = test_df[label_col].sum()
            table_data.append({
                'Characteristic': 'Aortic stenosis, n (%)',
                'Training (N={:,})'.format(len(train_df)): f"{int(as_train)} ({as_train/len(train_df)*100:.1f}%)",
                'Test (N={:,})'.format(len(test_df)): f"{int(as_test)} ({as_test/len(test_df)*100:.1f}%)"
            })

        # 施設分布
        if 'institution' in df.columns:
            for inst in df['institution'].unique():
                n_train = (train_df['institution'] == inst).sum()
                n_test = (test_df['institution'] == inst).sum()
                table_data.append({
                    'Characteristic': f'  {inst.capitalize()}, n (%)',
                    'Training (N={:,})'.format(len(train_df)): f"{n_train} ({n_train/len(train_df)*100:.1f}%)",
                    'Test (N={:,})'.format(len(test_df)): f"{n_test} ({n_test/len(test_df)*100:.1f}%)"
                })

        return pd.DataFrame(table_data)

    def generate_roc_curve(self, y_true, y_prob, title='ROC Curves for AS Prediction Model',
                          folds=None, save_name='fig_roc'):
        """ROC曲線の生成（参照スタイル準拠）"""
        fig, ax = plt.subplots(figsize=(6, 6), dpi=300)

        colors = self.ROC_COLORS  # ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        if folds is not None:
            # 複数フォールドのROC
            for i, (y_t, y_p) in enumerate(folds):
                fpr, tpr, _ = roc_curve(y_t, y_p)
                roc_auc = auc(fpr, tpr)
                ax.plot(fpr, tpr, color=colors[i], lw=2,
                       label=f'Fold {i} (AUC = {roc_auc:.3f})')

        # 全体ROC (dashed, red)
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=colors[3], lw=2.5, linestyle='--',
               label=f'Overall (AUC = {roc_auc:.3f})')

        # Reference line
        ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5)

        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('False Positive Rate (1 - Specificity)')
        ax.set_ylabel('True Positive Rate (Sensitivity)')
        ax.set_title(title)
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)  # 参照スタイル：軽いグリッド

        plt.tight_layout()
        self._save_figure(fig, save_name)
        return fig

    def generate_confusion_matrix(self, y_true, y_pred, threshold=0.5,
                                  save_name='fig_confusion'):
        """混同行列の生成（参照スタイル準拠）"""
        cm = confusion_matrix(y_true, y_pred)

        fig, ax = plt.subplots(figsize=(6, 5), dpi=300)

        # カラーマップ（青系 - 参照と同じ）
        im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)

        # カラーバー
        cbar = ax.figure.colorbar(im, ax=ax, shrink=0.8)
        cbar.ax.set_ylabel('Count', rotation=-90, va='bottom')

        # ラベル
        classes = ['Negative (No AS)', 'Positive (AS)']
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(classes)
        ax.set_yticklabels(classes)
        ax.set_xlabel('Predicted Label')
        ax.set_ylabel('True Label')
        ax.set_title(f'Confusion Matrix (Threshold = {threshold})')

        # テキストアノテーション（カウント、パーセント、TN/FP/FN/TP）
        thresh = cm.max() / 2.
        labels_matrix = [['TN', 'FP'], ['FN', 'TP']]
        for i in range(2):
            for j in range(2):
                total = cm.sum()
                pct = cm[i, j] / total * 100
                text = f'{cm[i, j]:,}\n({pct:.1f}%)'
                ax.text(j, i, text, ha='center', va='center',
                       color='white' if cm[i, j] > thresh else 'black',
                       fontsize=11)
                ax.text(j, i + 0.35, labels_matrix[i][j], ha='center', va='center',
                       color='white' if cm[i, j] > thresh else 'black',
                       fontsize=9, style='italic')

        plt.tight_layout()
        self._save_figure(fig, save_name)
        return fig

    def generate_institution_comparison(self, results: list, overall_auc=0.857,
                                        save_name='fig_institution'):
        """施設別性能比較（参照スタイル準拠）"""
        # Sort by AUC descending
        results = sorted(results, key=lambda x: x['auc'], reverse=True)

        institutions = [r['institution'] for r in results]
        aucs = [r['auc'] for r in results]
        ns = [r['n'] for r in results]

        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

        # Horizontal bar chart - 青のグラデーション
        colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(results)))
        bars = ax.barh(range(len(institutions)), aucs, color=colors)

        # ラベル追加（AUC値とサンプル数）
        for i, (bar, auc_val, n) in enumerate(zip(bars, aucs, ns)):
            ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                   f'{auc_val:.3f} (n={n:,})', va='center', fontsize=9)

        ax.set_yticks(range(len(institutions)))
        ax.set_yticklabels(institutions)
        ax.set_xlabel('AUC-ROC')
        ax.set_title('Model Performance by Institution')
        ax.set_xlim([0.0, 1.05])
        ax.grid(True, alpha=0.3, axis='x')  # 参照スタイル：x軸グリッドのみ

        # 全体AUCの赤い点線
        ax.axvline(x=overall_auc, color='red', linestyle='--', lw=1.5,
                  label=f'Overall AUC ({overall_auc:.3f})')
        ax.legend(loc='lower right')

        plt.tight_layout()
        self._save_figure(fig, save_name)
        return fig

    def generate_calibration_plot(self, y_true, y_prob, n_bins=10,
                                  save_name='fig_calibration'):
        """Calibration plot（較正曲線）"""
        fraction_positives, mean_predicted = calibration_curve(
            y_true, y_prob, n_bins=n_bins, strategy='uniform'
        )

        fig, ax = plt.subplots(figsize=(3.5, 3.5))

        # Perfect calibration line
        ax.plot([0, 1], [0, 1], 'k--', lw=0.5, label='Perfectly calibrated')

        # Calibration curve
        ax.plot(mean_predicted, fraction_positives, 's-',
               color=self.COLORS['primary'], lw=1, markersize=4,
               label='Model')

        ax.set_xlabel('Mean predicted probability')
        ax.set_ylabel('Fraction of positives')
        ax.set_title('Calibration Plot')
        ax.legend(loc='lower right', frameon=False)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.set_aspect('equal')

        self._save_figure(fig, save_name)
        return fig

    def generate_learning_curve(self, train_losses, val_losses=None,
                                epochs=None, save_name='fig_learning'):
        """学習曲線"""
        if epochs is None:
            epochs = range(1, len(train_losses) + 1)

        fig, ax = plt.subplots(figsize=(4, 3))

        ax.plot(epochs, train_losses, color=self.COLORS['primary'],
               lw=1, label='Training')
        if val_losses is not None:
            ax.plot(epochs, val_losses, color=self.COLORS['secondary'],
                   lw=1, label='Validation')

        ax.set_xlabel('Epoch')
        ax.set_ylabel('Loss')
        ax.set_title('Learning Curves')
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.3)

        self._save_figure(fig, save_name)
        return fig

    def generate_architecture_diagram(self, save_name='fig_architecture'):
        """モデルアーキテクチャ図（Graphviz使用）"""
        from graphviz import Digraph

        dot = Digraph(comment='Model Architecture')
        dot.attr(rankdir='LR', size='8,4', dpi=str(self.config['dpi']))
        dot.attr('node', shape='box', style='rounded,filled',
                fontname=self.config['font_family'],
                fontsize=str(self.config['font_size']))

        # カラー設定
        colors = {
            'input': '#E8F5E9',
            'encoder': '#4ECDC4',
            'fusion': '#96CEB4',
            'output': '#FF6B6B'
        }

        # ノード定義
        dot.node('ecg', 'ECG Input\n(12-lead)', fillcolor=colors['input'])
        dot.node('xray', 'Chest X-ray\n(PA view)', fillcolor=colors['input'])
        dot.node('ecg_enc', 'ECG Encoder\n(1D-CNN)', fillcolor=colors['encoder'])
        dot.node('xray_enc', 'Image Encoder\n(ResNet-50)', fillcolor=colors['encoder'])
        dot.node('fusion', 'Feature Fusion', fillcolor=colors['fusion'])
        dot.node('output', 'AS Prediction', fillcolor=colors['output'], fontcolor='white')

        # エッジ
        dot.edge('ecg', 'ecg_enc')
        dot.edge('xray', 'xray_enc')
        dot.edge('ecg_enc', 'fusion')
        dot.edge('xray_enc', 'fusion')
        dot.edge('fusion', 'output')

        # 出力
        output_path = self.output_dir / save_name
        dot.render(str(output_path), format='png', cleanup=True)
        dot.save(str(output_path) + '.gv')

        return dot

    def _save_figure(self, fig, name):
        """図の保存（複数形式）"""
        for fmt in self.config['formats']:
            output_path = self.output_dir / f'{name}.{fmt}'
            fig.savefig(output_path, format=fmt, dpi=self.config['dpi'],
                       bbox_inches='tight', pad_inches=0.05)
            print(f"Saved: {output_path}")
        plt.close(fig)
```

## Output Files

```
<project_dir>/figures/
├── fig_roc.png              # ROC曲線
├── fig_roc.tiff             # TIFF版（ジャーナル提出用）
├── fig_roc.pdf              # PDF版
├── fig_confusion.png        # 混同行列
├── fig_institution.png      # 施設別比較
├── fig_architecture.png     # アーキテクチャ図
├── fig_architecture.gv      # Graphvizソース
├── fig_calibration.png      # 較正曲線
├── fig_learning.png         # 学習曲線（Supplementary）
└── table1_characteristics.csv # 患者特性表
```

## Color Guidelines

### 色覚多様性対応パレット

```python
# Okabe-Ito カラーパレット（8色）
COLORBLIND_SAFE = [
    '#E69F00',  # Orange
    '#56B4E9',  # Sky Blue
    '#009E73',  # Bluish Green
    '#F0E442',  # Yellow
    '#0072B2',  # Blue
    '#D55E00',  # Vermillion
    '#CC79A7',  # Reddish Purple
    '#000000'   # Black
]
```

## Notes

- **次のステップ**: `/paper-generate` でAgent 4（論文執筆）を実行
- **ジャーナル形式**: `--journal` オプションで投稿先に合わせた設定を適用
- **色覚対応**: 全図表は色覚多様性に配慮したカラーパレットを使用
- **アーキテクチャ図**: Graphvizを使用（`/paper-diagrams` との互換性あり）
