# Paper Review (自動レビュー・品質改善)

AI Scientist型のセルフレビュー機能。生成された論文ドラフトの品質を自動評価し、改善提案を行います。

## Usage

```
/paper-review <project_dir> [--strict] [--output review_report.md]
```

## What This Does

Agent 4（論文執筆）の出力を多角的に評価し、以下の観点から品質チェックを行います：

1. **構造的整合性**: IMRaD形式の遵守、セクション間の論理的整合
2. **数値の一貫性**: 図表と本文の数値が一致しているか
3. **引用の適切性**: 主張に対する適切な引用があるか
4. **統計的妥当性**: 統計手法と結果報告の適切性
5. **臨床的意義**: 臨床的解釈の妥当性
6. **言語品質**: 文法、スタイル、明瞭さ

## Review Checklist

### 1. Title & Abstract Review

| チェック項目 | 基準 |
|------------|------|
| タイトル長 | 10-15語 |
| 抄録構造 | Background/Methods/Results/Conclusions |
| 抄録長 | ジャーナル規定に準拠 |
| 主要数値の記載 | AUC、サンプルサイズ、信頼区間 |

### 2. Methods Review

| チェック項目 | 基準 |
|------------|------|
| 研究デザイン | 明確に記載 |
| 倫理承認 | IRB承認番号 |
| 対象者基準 | 包含/除外基準 |
| モデル詳細 | アーキテクチャ、ハイパーパラメータ |
| 統計手法 | 適切な検定、多重比較補正 |
| ソフトウェア | バージョン番号 |

### 3. Results Review

| チェック項目 | 基準 |
|------------|------|
| 主要評価項目 | AUC + 95% CI |
| 副次評価項目 | 感度、特異度、PPV、NPV |
| サブグループ解析 | 施設別、年齢層別 |
| 図表参照 | 本文中で参照 |
| 数値の一貫性 | 図表と本文が一致 |

### 4. Discussion Review

| チェック項目 | 基準 |
|------------|------|
| 主要所見 | 結果の要約 |
| 先行研究との比較 | 文献引用付き |
| 臨床的意義 | 実用上の意味 |
| 限界点 | 3-5点の記載 |
| 将来展望 | 次のステップ |

## Implementation

```python
#!/usr/bin/env python3
"""Paper Review: AI Scientist型セルフレビュー"""

import yaml
import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class ReviewItem:
    """レビュー項目"""
    category: str
    check: str
    status: str  # 'pass', 'warning', 'fail'
    message: str
    suggestion: Optional[str] = None

class PaperReviewer:
    """論文品質の自動レビュー"""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.spec = self._load_spec()
        self.analysis = self._load_analysis()
        self.issues: List[ReviewItem] = []

    def _load_spec(self) -> Dict:
        """paper_spec.yamlの読み込み"""
        spec_file = self.project_dir / 'paper_spec.yaml'
        with open(spec_file, encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_analysis(self) -> Dict:
        """analysis_report.jsonの読み込み"""
        analysis_file = self.project_dir / 'analysis_report.json'
        if analysis_file.exists():
            with open(analysis_file) as f:
                return json.load(f)
        return {}

    def review(self) -> List[ReviewItem]:
        """全レビューを実行"""
        self._review_structure()
        self._review_numbers()
        self._review_statistics()
        self._review_citations()
        self._review_figures()
        self._review_language()
        self._review_clinical()
        return self.issues

    def _review_structure(self):
        """構造的整合性のレビュー"""
        sections = self.spec.get('sections', [])
        required_sections = ['Introduction', 'Methods', 'Results', 'Discussion']

        # セクション存在チェック
        section_headings = [s['heading']['en'] for s in sections]
        for req in required_sections:
            if req not in section_headings:
                self.issues.append(ReviewItem(
                    category='Structure',
                    check=f'{req} section',
                    status='fail',
                    message=f'Missing required section: {req}',
                    suggestion=f'Add {req} section to complete IMRaD structure'
                ))
            else:
                self.issues.append(ReviewItem(
                    category='Structure',
                    check=f'{req} section',
                    status='pass',
                    message=f'{req} section present'
                ))

        # Abstract構造チェック
        abstract = self.spec.get('abstract', {}).get('en', '')
        abstract_parts = ['Background', 'Methods', 'Results', 'Conclusions']
        for part in abstract_parts:
            if part.lower() not in abstract.lower() and f'**{part}**' not in abstract:
                self.issues.append(ReviewItem(
                    category='Structure',
                    check=f'Abstract {part}',
                    status='warning',
                    message=f'Abstract may be missing {part} section',
                    suggestion=f'Add structured {part} subsection to abstract'
                ))

    def _review_numbers(self):
        """数値の一貫性チェック"""
        analysis_perf = self.analysis.get('performance', {})
        spec_tables = self.spec.get('tables', {})

        # AUC値の一貫性
        analysis_auc = analysis_perf.get('auc_roc')
        if analysis_auc:
            # 本文中のAUC検索
            for section in self.spec.get('sections', []):
                content = section.get('content', {}).get('en', '')
                # AUC値の抽出（0.XXX形式）
                auc_matches = re.findall(r'AUC[^\d]*(\d+\.\d{3})', content)
                for match in auc_matches:
                    if abs(float(match) - analysis_auc) > 0.001:
                        self.issues.append(ReviewItem(
                            category='Numbers',
                            check='AUC consistency',
                            status='fail',
                            message=f'AUC mismatch: text shows {match}, analysis shows {analysis_auc:.3f}',
                            suggestion='Update text to match analysis results'
                        ))

        # サンプルサイズの一貫性
        analysis_n = self.analysis.get('dataset', {}).get('n_samples')
        if analysis_n:
            for section in self.spec.get('sections', []):
                content = section.get('content', {}).get('en', '')
                # サンプルサイズの抽出
                n_matches = re.findall(r'(\d{1,3}(?:,\d{3})*)\s*patients', content)
                for match in n_matches:
                    n_text = int(match.replace(',', ''))
                    if n_text != analysis_n:
                        self.issues.append(ReviewItem(
                            category='Numbers',
                            check='Sample size consistency',
                            status='warning',
                            message=f'Sample size mismatch: text shows {n_text}, analysis shows {analysis_n}',
                            suggestion='Verify sample size matches analysis'
                        ))

    def _review_statistics(self):
        """統計的妥当性のレビュー"""
        for section in self.spec.get('sections', []):
            content = section.get('content', {}).get('en', '')

            # 信頼区間の記載
            if section.get('heading', {}).get('en') == 'Results':
                if 'AUC' in content and '95%' not in content and 'CI' not in content:
                    self.issues.append(ReviewItem(
                        category='Statistics',
                        check='Confidence intervals',
                        status='warning',
                        message='AUC reported without 95% confidence interval',
                        suggestion='Add 95% CI for AUC (e.g., "AUC 0.857, 95% CI: 0.842-0.871")'
                    ))

            # p値の適切な報告
            if 'p <' in content or 'p=' in content or 'p =' in content:
                if 'p < 0.001' in content or 'p<0.001' in content:
                    pass  # OK
                elif re.search(r'p\s*[<=]\s*0\.0+\d', content):
                    self.issues.append(ReviewItem(
                        category='Statistics',
                        check='P-value reporting',
                        status='warning',
                        message='Very small p-values should be reported as "p < 0.001"',
                        suggestion='Use "p < 0.001" instead of exact small values'
                    ))

    def _review_citations(self):
        """引用の適切性チェック"""
        references = self.spec.get('references', [])
        n_refs = len(references)

        # 引用数チェック
        if n_refs < 20:
            self.issues.append(ReviewItem(
                category='Citations',
                check='Reference count',
                status='warning',
                message=f'Only {n_refs} references. Typical medical AI papers have 30-50.',
                suggestion='Add more relevant references, especially for Introduction and Discussion'
            ))
        else:
            self.issues.append(ReviewItem(
                category='Citations',
                check='Reference count',
                status='pass',
                message=f'{n_refs} references included'
            ))

        # 本文中の引用マーカー
        for section in self.spec.get('sections', []):
            heading = section.get('heading', {}).get('en', '')
            content = section.get('content', {}).get('en', '')

            if heading == 'Introduction':
                citation_markers = re.findall(r'\[\d+(?:,\s*\d+)*\]', content)
                if len(citation_markers) < 5:
                    self.issues.append(ReviewItem(
                        category='Citations',
                        check='Introduction citations',
                        status='warning',
                        message=f'Introduction has only {len(citation_markers)} citation markers',
                        suggestion='Add citations for key claims in Introduction'
                    ))

    def _review_figures(self):
        """図表の整合性チェック"""
        figures = self.spec.get('figures', {})
        tables = self.spec.get('tables', {})

        # 必須図表
        required_figures = ['fig_roc']
        required_tables = ['tab_performance']

        for fig in required_figures:
            if fig not in figures:
                self.issues.append(ReviewItem(
                    category='Figures',
                    check=f'{fig}',
                    status='warning',
                    message=f'Recommended figure missing: {fig}',
                    suggestion=f'Add {fig} for standard reporting'
                ))

        # 図のファイル存在チェック
        for fig_id, fig_spec in figures.items():
            fig_path = self.project_dir / fig_spec.get('path', '')
            if not fig_path.exists():
                self.issues.append(ReviewItem(
                    category='Figures',
                    check=f'{fig_id} file',
                    status='fail',
                    message=f'Figure file not found: {fig_spec.get("path")}',
                    suggestion='Run /paper-figures to generate missing figures'
                ))

    def _review_language(self):
        """言語品質のレビュー"""
        for section in self.spec.get('sections', []):
            content_en = section.get('content', {}).get('en', '')
            content_ja = section.get('content', {}).get('ja', '')

            # 日本語コンテンツの存在
            if not content_ja or content_ja == '[Japanese]' or len(content_ja) < 50:
                self.issues.append(ReviewItem(
                    category='Language',
                    check=f'{section.get("heading", {}).get("en", "")} Japanese',
                    status='warning',
                    message='Japanese content missing or placeholder',
                    suggestion='Generate Japanese content for bilingual output'
                ))

            # 受動態の過剰使用（英語）
            passive_phrases = len(re.findall(r'\b(was|were|been|being)\s+\w+ed\b', content_en))
            word_count = len(content_en.split())
            if word_count > 0 and passive_phrases / word_count > 0.05:
                self.issues.append(ReviewItem(
                    category='Language',
                    check='Passive voice',
                    status='warning',
                    message='High frequency of passive voice detected',
                    suggestion='Consider using active voice for clarity'
                ))

    def _review_clinical(self):
        """臨床的妥当性のレビュー"""
        discussion = None
        for section in self.spec.get('sections', []):
            if section.get('heading', {}).get('en') == 'Discussion':
                discussion = section.get('content', {}).get('en', '')
                break

        if discussion:
            # 限界点の記載
            limitations_keywords = ['limitation', 'limit', 'weakness', 'shortcoming']
            has_limitations = any(kw in discussion.lower() for kw in limitations_keywords)
            if not has_limitations:
                self.issues.append(ReviewItem(
                    category='Clinical',
                    check='Limitations',
                    status='fail',
                    message='Discussion does not mention study limitations',
                    suggestion='Add a "Limitations" subsection discussing study weaknesses'
                ))

            # 臨床的意義の記載
            clinical_keywords = ['clinical', 'practice', 'screening', 'diagnosis', 'patient']
            clinical_mentions = sum(1 for kw in clinical_keywords if kw in discussion.lower())
            if clinical_mentions < 3:
                self.issues.append(ReviewItem(
                    category='Clinical',
                    check='Clinical implications',
                    status='warning',
                    message='Limited discussion of clinical implications',
                    suggestion='Expand discussion of how findings translate to clinical practice'
                ))

    def generate_report(self) -> str:
        """レビューレポートの生成"""
        report = ["# Paper Review Report\n"]
        report.append(f"**Project:** {self.project_dir.name}\n")
        report.append(f"**Generated:** {self._get_timestamp()}\n")
        report.append("---\n")

        # サマリー
        pass_count = sum(1 for i in self.issues if i.status == 'pass')
        warn_count = sum(1 for i in self.issues if i.status == 'warning')
        fail_count = sum(1 for i in self.issues if i.status == 'fail')

        report.append("## Summary\n")
        report.append(f"- Pass: {pass_count}\n")
        report.append(f"- Warnings: {warn_count}\n")
        report.append(f"- Failures: {fail_count}\n")

        # スコア
        total = pass_count + warn_count + fail_count
        score = (pass_count + 0.5 * warn_count) / total * 100 if total > 0 else 0
        report.append(f"\n**Quality Score: {score:.0f}/100**\n")

        # カテゴリ別詳細
        categories = {}
        for item in self.issues:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)

        for category, items in categories.items():
            report.append(f"\n## {category}\n")
            for item in items:
                icon = {'pass': '✓', 'warning': '⚠', 'fail': '✗'}[item.status]
                report.append(f"\n### {icon} {item.check}\n")
                report.append(f"**Status:** {item.status.upper()}\n")
                report.append(f"{item.message}\n")
                if item.suggestion:
                    report.append(f"\n**Suggestion:** {item.suggestion}\n")

        # 改善アクション
        if fail_count > 0 or warn_count > 0:
            report.append("\n## Recommended Actions\n")
            action_num = 1
            for item in self.issues:
                if item.status in ['fail', 'warning'] and item.suggestion:
                    report.append(f"{action_num}. {item.suggestion}\n")
                    action_num += 1

        return "".join(report)

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
```

## Output Format

### review_report.md

```markdown
# Paper Review Report

**Project:** major3_AS_paper
**Generated:** 2026-03-21 12:00:00

---

## Summary

- Pass: 15
- Warnings: 5
- Failures: 2

**Quality Score: 78/100**

## Structure

### ✓ Introduction section
**Status:** PASS
Introduction section present

### ✓ Methods section
**Status:** PASS
Methods section present

## Numbers

### ✗ AUC consistency
**Status:** FAIL
AUC mismatch: text shows 0.850, analysis shows 0.857

**Suggestion:** Update text to match analysis results

## Citations

### ⚠ Introduction citations
**Status:** WARNING
Introduction has only 3 citation markers

**Suggestion:** Add citations for key claims in Introduction

## Recommended Actions

1. Update text to match analysis results
2. Add citations for key claims in Introduction
3. Generate Japanese content for bilingual output
4. Add a "Limitations" subsection discussing study weaknesses
```

## Quality Score Interpretation

| Score | 評価 | 次のアクション |
|-------|------|---------------|
| 90-100 | Excellent | 投稿準備完了 |
| 80-89 | Good | 軽微な修正後に投稿可 |
| 70-79 | Acceptable | 改善推奨箇所の修正 |
| 60-69 | Needs Work | 複数箇所の修正必要 |
| <60 | Major Revision | 大幅な見直し必要 |

## Iterative Improvement

```
/paper-generate → /paper-review → 修正 → /paper-review → ... → /paper-build
```

レビュースコアが80以上になるまで修正を繰り返すことを推奨します。

## Notes

- **次のステップ**: スコア80以上で `/paper-build` を実行
- **反復改善**: レビュー結果に基づいて修正し、再度レビューを実行
- **OCRチェック**: 図表の数値確認は `/paper-qa` で実施
