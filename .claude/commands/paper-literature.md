# Paper Literature (Agent 2: 先行研究探索エージェント)

AI駆動型論文執筆エージェントの第2エージェント。学術データベースを検索し、関連する先行研究を自動収集・整理します。

## Usage

```
/paper-literature <project_dir> [--keywords "keyword1, keyword2"] [--max-papers 50]
```

## What This Does

Agent 1（実験データ解析）の出力に基づき、学術データベース（PubMed、Semantic Scholar、Google Scholar等）を検索し、関連する先行研究を自動収集・整理します。新規性の位置づけやRelated Workセクションのドラフトも生成します。

### 1. 検索ソース

| データベース | API | 用途 |
|------------|-----|------|
| PubMed | Entrez E-utilities | 医学論文（MEDLINE） |
| Semantic Scholar | S2 API | AI/ML論文、引用ネットワーク |
| arXiv | arXiv API | プレプリント、最新研究 |
| Google Scholar | SerpAPI (有料) | 広範な学術検索 |

### 2. 検索戦略

```python
# Agent 1からの引き継ぎ情報を使用
search_strategy = {
    'primary_keywords': ['aortic stenosis', 'deep learning', 'multimodal'],
    'secondary_keywords': ['ECG', 'chest X-ray', 'screening'],
    'mesh_terms': ['Aortic Valve Stenosis', 'Deep Learning', 'Electrocardiography'],
    'date_range': '2019-2025',  # 過去5年
    'filters': {
        'article_types': ['Journal Article', 'Clinical Study'],
        'languages': ['English']
    }
}
```

### 3. 論文分類

| カテゴリ | 説明 |
|---------|------|
| 直接関連 | 同じ疾患 + 同じ手法 |
| 手法関連 | 異なる疾患 + 同じ手法（マルチモーダルDL） |
| 疾患関連 | 同じ疾患 + 異なる手法（従来診断法） |
| ベンチマーク | 比較対象となる先行研究 |

## Implementation

```python
#!/usr/bin/env python3
"""Agent 2: 先行研究探索エージェント"""

import requests
from Bio import Entrez
import json
from datetime import datetime
from typing import List, Dict
import time

class LiteratureSearchAgent:
    """先行研究の自動収集・整理"""

    def __init__(self, email: str = "research@example.com"):
        Entrez.email = email
        self.papers = []

    def search_pubmed(self, query: str, max_results: int = 50) -> List[Dict]:
        """PubMed検索"""
        # 検索実行
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            sort="relevance",
            datetype="pdat",
            mindate="2019",
            maxdate="2025"
        )
        record = Entrez.read(handle)
        handle.close()

        pmids = record["IdList"]
        if not pmids:
            return []

        # 詳細情報取得
        handle = Entrez.efetch(
            db="pubmed",
            id=",".join(pmids),
            rettype="xml",
            retmode="xml"
        )
        records = Entrez.read(handle)
        handle.close()

        papers = []
        for article in records['PubmedArticle']:
            medline = article['MedlineCitation']
            article_data = medline['Article']

            paper = {
                'pmid': str(medline['PMID']),
                'title': article_data['ArticleTitle'],
                'authors': self._extract_authors(article_data.get('AuthorList', [])),
                'journal': article_data['Journal']['Title'],
                'year': self._extract_year(article_data),
                'abstract': self._extract_abstract(article_data),
                'doi': self._extract_doi(article_data),
                'source': 'PubMed'
            }
            papers.append(paper)

        return papers

    def search_semantic_scholar(self, query: str, max_results: int = 50) -> List[Dict]:
        """Semantic Scholar検索"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': max_results,
            'fields': 'title,authors,year,abstract,citationCount,journal,externalIds'
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            return []

        data = response.json()
        papers = []

        for paper in data.get('data', []):
            papers.append({
                'title': paper.get('title', ''),
                'authors': [a['name'] for a in paper.get('authors', [])],
                'year': paper.get('year'),
                'abstract': paper.get('abstract', ''),
                'citations': paper.get('citationCount', 0),
                'doi': paper.get('externalIds', {}).get('DOI'),
                'source': 'SemanticScholar'
            })

        return papers

    def search_arxiv(self, query: str, max_results: int = 20) -> List[Dict]:
        """arXiv検索（最新のプレプリント）"""
        import urllib.request
        import xml.etree.ElementTree as ET

        base_url = 'http://export.arxiv.org/api/query'
        query_url = f'{base_url}?search_query=all:{query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending'

        response = urllib.request.urlopen(query_url)
        data = response.read().decode('utf-8')
        root = ET.fromstring(data)

        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        papers = []

        for entry in root.findall('atom:entry', ns):
            paper = {
                'title': entry.find('atom:title', ns).text.strip(),
                'authors': [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)],
                'year': entry.find('atom:published', ns).text[:4],
                'abstract': entry.find('atom:summary', ns).text.strip(),
                'arxiv_id': entry.find('atom:id', ns).text.split('/')[-1],
                'source': 'arXiv'
            }
            papers.append(paper)

        return papers

    def categorize_papers(self, papers: List[Dict], context: Dict) -> Dict[str, List[Dict]]:
        """論文の分類"""
        categories = {
            'directly_related': [],      # 同疾患 + 同手法
            'method_related': [],        # 異疾患 + 同手法
            'disease_related': [],       # 同疾患 + 異手法
            'benchmark': [],             # 比較対象
            'background': []             # 背景知識
        }

        disease_keywords = context.get('disease_keywords', ['aortic stenosis'])
        method_keywords = context.get('method_keywords', ['deep learning', 'neural network'])

        for paper in papers:
            title_abstract = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()

            has_disease = any(kw.lower() in title_abstract for kw in disease_keywords)
            has_method = any(kw.lower() in title_abstract for kw in method_keywords)

            if has_disease and has_method:
                categories['directly_related'].append(paper)
            elif has_method and not has_disease:
                categories['method_related'].append(paper)
            elif has_disease and not has_method:
                categories['disease_related'].append(paper)
            else:
                categories['background'].append(paper)

        return categories

    def assess_novelty(self, categories: Dict, our_results: Dict) -> Dict:
        """新規性の評価"""
        directly_related = categories['directly_related']

        # 既存研究との比較
        existing_aucs = []
        existing_modalities = set()
        existing_datasets = []

        for paper in directly_related:
            # 抽象からメトリクスを抽出（簡易版）
            abstract = paper.get('abstract', '').lower()
            if 'auc' in abstract:
                # AUC値の抽出ロジック
                pass
            if 'ecg' in abstract:
                existing_modalities.add('ECG')
            if 'x-ray' in abstract or 'chest' in abstract:
                existing_modalities.add('Chest X-ray')

        novelty_assessment = {
            'is_novel_approach': len(directly_related) < 5,
            'is_novel_modality_combination': 'multimodal' not in str(existing_modalities).lower(),
            'performance_comparison': {
                'existing_best_auc': max(existing_aucs) if existing_aucs else None,
                'our_auc': our_results.get('auc_roc'),
                'improvement': None  # 計算
            },
            'novelty_claims': self._generate_novelty_claims(categories, our_results)
        }

        return novelty_assessment

    def _generate_novelty_claims(self, categories, our_results) -> List[str]:
        """新規性の主張を生成"""
        claims = []

        if len(categories['directly_related']) < 3:
            claims.append("First study to apply multimodal deep learning combining ECG and chest X-ray for AS detection")

        if our_results.get('n_samples', 0) > 10000:
            claims.append("Largest multicenter validation study to date")

        claims.append(f"Achieved AUC of {our_results.get('auc_roc', 0):.3f} across {our_results.get('n_institutions', 0)} institutions")

        return claims

    def generate_related_work_draft(self, categories: Dict) -> str:
        """Related Workセクションのドラフト生成"""
        sections = []

        # 疾患背景
        sections.append("### Disease Background")
        sections.append(self._format_paper_group(categories['disease_related'][:5],
            "Previous studies on aortic stenosis diagnosis have relied on..."))

        # 方法論
        sections.append("\n### Deep Learning in Cardiovascular Medicine")
        sections.append(self._format_paper_group(categories['method_related'][:5],
            "Deep learning approaches have been successfully applied to..."))

        # 直接関連研究
        sections.append("\n### Multimodal Approaches for AS Detection")
        sections.append(self._format_paper_group(categories['directly_related'],
            "Recent studies have begun exploring multimodal approaches..."))

        # ギャップ
        sections.append("\n### Research Gap")
        sections.append("Despite these advances, no prior study has combined ECG and chest X-ray "
                       "using deep learning for AS screening in a large-scale multicenter setting.")

        return "\n".join(sections)

    def _format_paper_group(self, papers: List[Dict], intro: str) -> str:
        """論文グループのフォーマット"""
        text = intro + "\n\n"
        for paper in papers[:5]:
            authors = paper.get('authors', ['Unknown'])
            first_author = authors[0].split()[-1] if authors else 'Unknown'
            year = paper.get('year', '')
            text += f"- {first_author} et al. ({year}): {paper.get('title', '')}\n"
        return text

    def export_bibliography(self, papers: List[Dict], format: str = 'bibtex') -> str:
        """参考文献のエクスポート"""
        if format == 'bibtex':
            entries = []
            for i, paper in enumerate(papers):
                entry = self._to_bibtex(paper, f"ref{i+1}")
                entries.append(entry)
            return "\n\n".join(entries)
        return ""

    def _to_bibtex(self, paper: Dict, key: str) -> str:
        """BibTeX形式への変換"""
        authors = paper.get('authors', ['Unknown'])
        author_str = ' and '.join(authors[:3])
        if len(authors) > 3:
            author_str += ' and others'

        return f"""@article{{{key},
  title = {{{paper.get('title', '')}}},
  author = {{{author_str}}},
  journal = {{{paper.get('journal', 'arXiv preprint')}}},
  year = {{{paper.get('year', '')}}},
  doi = {{{paper.get('doi', '')}}}
}}"""
```

## Output Format

### 1. 検索結果サマリー (JSON)

```json
{
  "search_summary": {
    "total_papers_found": 127,
    "after_deduplication": 89,
    "by_source": {
      "PubMed": 45,
      "SemanticScholar": 32,
      "arXiv": 12
    }
  },
  "categories": {
    "directly_related": 8,
    "method_related": 23,
    "disease_related": 31,
    "benchmark": 5,
    "background": 22
  },
  "novelty_assessment": {
    "is_novel": true,
    "novelty_claims": [
      "First multimodal DL study for AS using ECG + CXR",
      "Largest multicenter validation (N=12,423)"
    ]
  },
  "key_references": [
    {
      "citation": "Attia et al. (2019)",
      "title": "Screening for cardiac contractile dysfunction using AI-ECG",
      "relevance": "benchmark",
      "our_improvement": "+0.05 AUC"
    }
  ]
}
```

### 2. Related Work ドラフト

```markdown
## Related Work

### Aortic Stenosis Diagnosis
Aortic stenosis (AS) is traditionally diagnosed through echocardiography,
which requires specialized equipment and expertise [1, 2]. Recent studies
have explored...

### Deep Learning in Cardiovascular Imaging
Deep learning has demonstrated remarkable success in cardiovascular
applications. Attia et al. showed that AI-ECG could detect reduced
ejection fraction with AUC 0.93 [3]. Zhang et al. extended this to...

### Multimodal Approaches
The combination of multiple data modalities has shown promise in
medical AI. However, no prior study has integrated ECG and chest
X-ray for AS detection.

### Research Gap
Despite advances in single-modality approaches, there remains a need
for accessible, multimodal screening tools that can be deployed in
primary care settings where echocardiography is not readily available.
```

### 3. 参考文献リスト (BibTeX)

```bibtex
@article{attia2019screening,
  title = {Screening for cardiac contractile dysfunction using an
           artificial intelligence-enabled electrocardiogram},
  author = {Attia, Zachi I and others},
  journal = {Nature Medicine},
  year = {2019},
  doi = {10.1038/s41591-018-0240-2}
}
```

## Web Search Integration

Claude Codeの`WebSearch`ツールを使用してリアルタイム検索も可能：

```
# PubMed検索の例
検索クエリ: "aortic stenosis" AND "deep learning" AND ("ECG" OR "electrocardiogram")
```

## Notes

- **次のステップ**: `/paper-figures` でAgent 3（図表生成）を実行
- **出力保存先**: `<project_dir>/literature/`
- **API制限**: PubMedは1秒あたり3リクエストまで
- **引用形式**: 投稿先ジャーナルに合わせて調整可能
