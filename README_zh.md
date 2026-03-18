# review-gen

`review-gen` 是面向管理学、战略、创业、创新与组织研究的长期文献综述工作流工具包。

它的核心目标不是“多写一点”，而是：**把大规模文献库变成可控、可追踪、可复用的综述流水线**。

## 功能总览

1. 基于 ABS/AJG + OpenAlex 检索高质量期刊文献。
2. 构建并维护可持续更新的文献工作区。
3. 基于 manifest 做增量全文下载。
4. PDF 转 Markdown（MinerU）并分块检索。
5. 先规划后写作，冻结框架再起草正文。
6. 写作时生成引用白名单，交稿前做 DOI 审计，抑制幻觉引用。

## 系统架构

系统由 4 个技能 + 2 个内置后端组成。

### 技能层

- `openalex-ajg-insights`
  负责检索、语料合并、全文清单准备、增量下载、PDF 转 Markdown、分块检索。
- `management-review-planner`
  负责生成 `review_plan.md`，保存历史版本，支持中英文规划与动态核心文献选择。
- `management-review-writer`
  负责生成 `review_packet.md`、`review_guardrails.md`、`citation_allowlist.jsonl`，并支持草稿引用审计。
- `review-orchestrator`
  负责流程闸门：计划未批准不能写、引用审计未通过不能定稿。

### 后端层

- `backend/openalex-ajg-mcp`
- `backend/paper-download-mcp`

## 工作区约定（单一真值）

每个项目使用一个 `<review-workspace>`，固定目录如下：

```text
01_search/      # 检索原始结果
02_corpus/      # 合并语料（master_corpus.jsonl）
03_screening/   # 筛选表与证据表
04_fulltext/    # manifest + PDF inbox/archive
05_mineru/      # MinerU 原始与解析产物
06_chunks/      # 检索分块索引
07_plan/        # 当前计划 + 历史快照
08_outputs/     # packet、草稿、白名单、审计报告
```

关键控制文件：

- `02_corpus/master_corpus.jsonl`
- `03_screening/screening_table.csv`
- `04_fulltext/fulltext_manifest.csv`
- `07_plan/review_plan.md`
- `08_outputs/review_packet.md`
- `08_outputs/citation_allowlist.jsonl`
- `08_outputs/citation_audit_report.md`

## 端到端工作流

命令中的占位符：

- `<workflow-python>`
- `<review-gen-home>`
- `<review-workspace>`

### 1）初始化工作区

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  init-workspace \
  --topic "你的主题"
```

### 2）在 ABS/AJG 期刊中检索（默认上限已提高）

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/openalex_ajg_bridge.py \
  search-abs \
  --query "你的检索词" \
  --field "INFO MAN" \
  --min-rank "4" \
  --year-start 2018 \
  --limit 50
```

### 3）合并语料并准备全文清单

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  merge-search-results

python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  prepare-fulltext-manifest --min-priority medium
```

### 4）按优先级增量下载全文

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/download_manifest_papers.py \
  --workspace <review-workspace> \
  --min-priority high \
  --max-papers 10
```

### 5）PDF 转换与分块

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  convert-pdfs-with-mineru \
  --env-path <review-workspace>/04_fulltext/mineru.env

python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  chunk-markdown
```

### 6）生成综述计划（动态高质量策略）

```bash
python <review-gen-home>/skills/management-review-planner/scripts/build_review_plan.py \
  --workspace <review-workspace> \
  --topic "你的主题" \
  --word-count 2500 \
  --language zh \
  --top-papers-mode dynamic \
  --top-papers 0
```

说明：

- `dynamic` 模式优先覆盖 screening 中已纳入（included）的文献。
- 默认不会为了凑数量回填低价值未纳入文献，除非显式传 `--allow-fallback`。
- 中文规划支持从 `02_corpus/cnki_ris/` 导入知网 RIS。

### 7）生成写作包与引用白名单

```bash
python <review-gen-home>/skills/management-review-writer/scripts/build_review_packet.py \
  --workspace <review-workspace> \
  --topic "你的主题" \
  --top-papers-mode dynamic \
  --top-papers 0 \
  --output-path <review-workspace>/08_outputs/review_packet.md
```

### 8）定稿前执行引用审计

```bash
python <review-gen-home>/skills/management-review-writer/scripts/validate_draft_citations.py \
  --workspace <review-workspace> \
  --draft-path <review-workspace>/08_outputs/review_draft.md
```

审计项：

- 草稿 DOI 必须存在于 `citation_allowlist.jsonl`。
- DOI 可联机通过 Crossref/OpenAlex 校验。
- 可选严格模式会校验作者-年份型文内引用映射。

## 质量闸门（强约束）

1. 计划未批准，不进入正式写作。
2. 引用审计未通过，不进入最终交付。
3. 白名单外文献，未经显式核验不得引用。

## 运行环境与依赖

安装基础依赖：

```bash
pip install -r requirements.txt
```

如果你准备用 `MINERU_ACCESS_KEY` + `MINERU_SECRET_KEY` 给 MinerU 做鉴权，再额外安装 OpenXLab 的可选依赖：

```bash
pip install -r requirements-openxlab.txt
```

如果想要最省事的安装路径，优先使用 `MINERU_API_KEY`，这条路径不需要 OpenXLab 依赖。

项目已做路径无关设计，可在 PowerShell、macOS Terminal、Linux shell 使用。

## 仓库结构

```text
review-gen/
├── backend/
│   ├── openalex-ajg-mcp/
│   └── paper-download-mcp/
├── README.md
├── README_zh.md
├── requirements.txt
└── skills/
    ├── openalex-ajg-insights/
    ├── management-review-planner/
    ├── management-review-writer/
    └── review-orchestrator/
```
