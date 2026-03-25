# Paper Analyze (Agent 1: 実験データ解析エージェント)

AI駆動型論文執筆エージェントの第1エージェント。実験データを解析し、モデルの特徴・性能・新規性を構造化します。

## Usage

```
/paper-analyze <experiment_dir> [--domain cardiology|oncology|general]
```

## What This Does

入力された実験データ（training loss曲線、AUC、精度、混同行列、ROC曲線、患者データ統計量等）を解析し、データの品質検証および統計的有意性の確認を行います。

### 1. データ検出と分類

| カテゴリ | 検出対象 |
|---------|---------|
| モデル出力 | `results_*.csv`, `predictions.csv`, `test_results.json` |
| 学習ログ | `training.log`, `loss_curve.csv`, `tensorboard/` |
| 設定ファイル | `config.yaml`, `hyperparams.json` |
| 患者データ | `patient_characteristics.csv`, `demographics.csv` |

### 2. 性能指標の自動計算

```python
# 自動計算される指標
metrics = {
    'classification': ['AUC-ROC', 'AUC-PR', 'Accuracy', 'Sensitivity', 'Specificity',
                       'PPV', 'NPV', 'F1-score', 'Youden Index'],
    'regression': ['MSE', 'RMSE', 'MAE', 'R²', 'Pearson r'],
    'calibration': ['Brier Score', 'Expected Calibration Error'],
    'confidence_intervals': '95% CI (Bootstrap, n=1000)'
}
```

### 3. 統計的検定

- **群間比較**: Mann-Whitney U検定、効果量（rank-biserial r）
- **施設間差異**: Kruskal-Wallis検定
- **ブートストラップ信頼区間**: AUC、感度、特異度の95% CI

### 4. 医療AI固有の解析

```python
# 循環器領域の特殊解析
cardiology_analysis = {
    'patient_characteristics': {
        'demographics': ['age', 'gender', 'BMI'],
        'comorbidities': ['hypertension', 'diabetes', 'dyslipidemia'],
        'medications': ['ACE-I', 'ARB', 'beta-blocker']
    },
    'diagnostic_metrics': {
        'rule_out': 'Sensitivity at Specificity >= 99%',
        'rule_in': 'Specificity at Sensitivity >= 90%',
        'clinical_utility': 'Net Benefit Analysis'
    }
}
```

## Implementation

```python
#!/usr/bin/env python3
"""Agent 1: 実験データ解析エージェント"""

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve, confusion_matrix
from sklearn.metrics import precision_recall_curve, average_precision_score
from scipy import stats
import json
from pathlib import Path

class ExperimentAnalyzer:
    """実験データの包括的解析"""

    def __init__(self, experiment_dir: str, domain: str = 'cardiology'):
        self.experiment_dir = Path(experiment_dir)
        self.domain = domain
        self.results = {}

    def analyze(self) -> dict:
        """メイン解析パイプライン"""
        # 1. ファイル検出
        self.results['files'] = self._detect_files()

        # 2. データ読み込みと統合
        self.results['data'] = self._load_data()

        # 3. 性能指標計算
        self.results['performance'] = self._calculate_performance()

        # 4. 統計的検定
        self.results['statistics'] = self._statistical_tests()

        # 5. 患者特性解析
        self.results['patient_characteristics'] = self._analyze_patient_characteristics()

        # 6. 品質検証
        self.results['quality'] = self._validate_quality()

        # 7. 新規性評価
        self.results['novelty'] = self._assess_novelty()

        return self.results

    def _calculate_performance(self) -> dict:
        """性能指標の計算"""
        df = self.data
        y_true = df['label'].values
        y_prob = df['pred_prob'].values
        y_pred = df['pred'].values

        # 基本指標
        metrics = {
            'auc_roc': roc_auc_score(y_true, y_prob),
            'auc_pr': average_precision_score(y_true, y_prob),
        }

        # 混同行列から計算
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()

        metrics.update({
            'sensitivity': tp / (tp + fn),
            'specificity': tn / (tn + fp),
            'ppv': tp / (tp + fp) if (tp + fp) > 0 else 0,
            'npv': tn / (tn + fn) if (tn + fn) > 0 else 0,
            'accuracy': (tp + tn) / (tp + tn + fp + fn),
            'f1_score': 2 * tp / (2 * tp + fp + fn),
            'youden_index': (tp / (tp + fn)) + (tn / (tn + fp)) - 1
        })

        # ブートストラップ信頼区間
        metrics['confidence_intervals'] = self._bootstrap_ci(y_true, y_prob)

        # 臨床有用性指標（Rule-out/Rule-in）
        if self.domain == 'cardiology':
            metrics['clinical'] = self._clinical_utility(y_true, y_prob)

        return metrics

    def _bootstrap_ci(self, y_true, y_prob, n_bootstrap=1000, alpha=0.05):
        """ブートストラップ法による信頼区間"""
        np.random.seed(42)
        aucs = []
        for _ in range(n_bootstrap):
            idx = np.random.choice(len(y_true), len(y_true), replace=True)
            aucs.append(roc_auc_score(y_true[idx], y_prob[idx]))

        return {
            'auc_lower': np.percentile(aucs, alpha/2 * 100),
            'auc_upper': np.percentile(aucs, (1 - alpha/2) * 100)
        }

    def _clinical_utility(self, y_true, y_prob):
        """臨床有用性指標"""
        fpr, tpr, thresholds = roc_curve(y_true, y_prob)

        # Rule-out: Sensitivity at Specificity >= 99%
        idx_rule_out = np.where((1 - fpr) >= 0.99)[0]
        sens_at_spec99 = tpr[idx_rule_out[-1]] if len(idx_rule_out) > 0 else 0

        # Rule-in: Specificity at Sensitivity >= 90%
        idx_rule_in = np.where(tpr >= 0.90)[0]
        spec_at_sens90 = (1 - fpr[idx_rule_in[0]]) if len(idx_rule_in) > 0 else 0

        return {
            'sensitivity_at_specificity_99': sens_at_spec99,
            'specificity_at_sensitivity_90': spec_at_sens90
        }

    def generate_report(self) -> str:
        """構造化レポートの生成"""
        return f"""
## 実験データ解析レポート

### データセット概要
- 総サンプル数: {self.results['data']['n_samples']:,}
- 陽性例: {self.results['data']['n_positive']:,} ({self.results['data']['prevalence']:.1%})
- 施設数: {self.results['data']['n_institutions']}
- 交差検証: {self.results['data']['n_folds']}分割

### モデル性能
| 指標 | 値 | 95% CI |
|-----|-----|--------|
| AUC-ROC | {self.results['performance']['auc_roc']:.3f} | [{self.results['performance']['confidence_intervals']['auc_lower']:.3f}, {self.results['performance']['confidence_intervals']['auc_upper']:.3f}] |
| Sensitivity | {self.results['performance']['sensitivity']:.3f} | - |
| Specificity | {self.results['performance']['specificity']:.3f} | - |
| PPV | {self.results['performance']['ppv']:.3f} | - |
| NPV | {self.results['performance']['npv']:.3f} | - |

### 統計的検定
- Mann-Whitney U: p < 0.001
- 効果量 (r): {self.results['statistics']['effect_size']:.3f}

### 施設別性能
{self._format_institution_table()}

### 品質評価
- データ完全性: {self.results['quality']['completeness']:.1%}
- 欠損値: {self.results['quality']['missing_values']}件
- 問題点: {self.results['quality']['issues']}

### Agent 2への引き継ぎ情報
- 研究テーマ: {self.results['novelty']['research_topic']}
- 主要な知見: {self.results['novelty']['key_findings']}
- 先行研究検索キーワード: {', '.join(self.results['novelty']['search_keywords'])}
"""
```

## Output Format

### 1. 構造化データ (JSON)

```json
{
  "dataset": {
    "n_samples": 12423,
    "n_positive": 927,
    "prevalence": 0.0746,
    "institutions": ["kyudai", "todai", "ehime", "kumamoto", "saga", "osakakoritsu"]
  },
  "performance": {
    "auc_roc": 0.857,
    "auc_roc_ci": [0.842, 0.871],
    "sensitivity": 0.823,
    "specificity": 0.995
  },
  "clinical_utility": {
    "sensitivity_at_specificity_99": 0.412,
    "specificity_at_sensitivity_90": 0.876
  },
  "statistics": {
    "mann_whitney_p": 1.2e-105,
    "effect_size_r": 0.743
  },
  "agent2_handoff": {
    "research_topic": "Multimodal deep learning for aortic stenosis detection",
    "modalities": ["ECG", "Chest X-ray"],
    "search_keywords": ["aortic stenosis", "deep learning", "ECG", "chest X-ray", "multimodal"]
  }
}
```

### 2. Markdown レポート

```markdown
## 実験データ解析レポート

### データセット概要
- 総サンプル数: 12,423
- 陽性例: 927 (7.46%)
- 施設数: 6
- 交差検証: 3分割

### モデル性能
| 指標 | 値 | 95% CI |
|-----|-----|--------|
| AUC-ROC | 0.857 | [0.842, 0.871] |
| Sensitivity | 82.3% | - |
| Specificity | 99.5% | - |

### 臨床有用性
- Rule-out (Spec≥99%時のSens): 41.2%
- Rule-in (Sens≥90%時のSpec): 87.6%
```

## Integration with claude-scientific-skills

```python
# EDAスキルの統合
from eda_analyzer import analyze_file, generate_markdown_report

# 統計解析スキルの統合
from assumption_checks import comprehensive_assumption_check
```

## Notes

- **次のステップ**: `/paper-literature` でAgent 2（先行研究探索）を実行
- **出力保存先**: `<experiment_dir>/analysis_report.json`
- **医療AI固有**: 循環器領域では臨床有用性指標（Rule-out/Rule-in）を自動計算
