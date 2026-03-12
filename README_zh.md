# review-gen

`review-gen` 是一套面向管理学、战略、创业、创新与组织研究的长期文献综述工具包。它把文献检索、语料库构建、增量文献下载、全文收集、PDF 转 Markdown、分块检索、综述规划、计划批准和综述写作串成一条稳定的多 agent 工作流。

## 平台无关模式

这一版已经改成平台无关的使用方式。核心脚本不再依赖固定的 Windows 路径，使用时只需要替换三个占位符：

- `<workflow-python>`：能够运行这些综述脚本的 Python 解释器
- `<review-gen-home>`：`review-gen` 包所在目录
- `<review-workspace>`：某个具体综述项目的工作区目录

也就是说，同一套工作流逻辑可以在 Windows PowerShell、macOS 终端或 Linux shell 中使用，主要差别只在于你填入的本地路径不同。

## 依赖要求

先安装 Python 依赖：

```bash
pip install -r requirements.txt
```

当前工具包依赖：

- `requests`
- `openxlab-dev`
- `httpx`
- `pydantic`
- `pandas`
- `openpyxl`
- `xlsxwriter`
- `python-dotenv`
- `mcp`
- `beautifulsoup4`
- `curl-cffi`
- `cloudscraper`
- `pymupdf4llm`
- `lxml`

说明：

- 这份依赖现在同时覆盖 `review-gen` 本身，以及内置的 `openalex-ajg-mcp` 和 `paper-download-mcp` 后端。
- 当你通过 `MINERU_ACCESS_KEY` 和 `MINERU_SECRET_KEY` 来鉴权 MinerU 时，会用到 `openxlab-dev`。
- 如果你只使用直接可用的 MinerU bearer token，并把它写入 `MINERU_API_KEY`，逻辑上不必走 OpenXLab 路径，但为了方便跨机器安装，`requirements.txt` 里仍然把它包含进去了。

## 内置后端

`review-gen` 现在已经把两个后端都内置进仓库：

- `backend/openalex-ajg-mcp`
- `backend/paper-download-mcp`

这意味着在一台新机器上，通常只需要 clone 一个 `review-gen` 仓库，就可以直接开始使用，不必再单独 clone 检索后端或下载后端。

如果以后你想覆盖这些内置后端，工作流依然支持：

- `--repo-root <path>` 用于 OpenAlex bridge
- `OPENALEX_AJG_MCP_ROOT=<path>`
- `PAPER_DOWNLOAD_MCP_ROOT=<path>`

## 工具包包含什么

目前包里有四个 skills，再加上内置后端：

- `openalex-ajg-insights`
  负责检索高等级期刊文献、保留检索语料、准备全文清单、按 manifest 增量下载重点文献、通过 MinerU 把 PDF 转成 Markdown，并高效检索摘要或全文观点。
- `management-review-planner`
  负责在正式写作前构建并持续打磨综述框架。
- `management-review-writer`
  负责把已批准框架和已整理证据转成正式综述正文。
- `review-orchestrator`
  负责把项目路由到下一步 subagent、检查当前状态，并在用户明确同意后处理计划批准或重新打开计划。
- `backend/openalex-ajg-mcp`
  `openalex-ajg-insights` 调用的内置文献检索后端。
- `backend/paper-download-mcp`
  manifest 增量下载工作流调用的内置 PDF 下载后端。

## 增量全文下载

现在全文流程已经支持基于 `fulltext_manifest.csv` 的增量下载。

这个功能特别适合：

- 先下载经典或奠基性文献
- 暂时不下载优先级较低的文献
- 让 manifest 一直作为“缺什么、下了什么、转了什么、哪里失败了”的唯一真值表

推荐方式是：

1. 先完成检索并合并 corpus
2. 再运行 `prepare-fulltext-manifest`
3. 先用更高优先级或较小上限下载第一批经典文献
4. 后续再按需要继续补下载其他文献

下载器默认是增量模式，所以已经存在 PDF 的文献会自动跳过，除非你明确要求覆盖。

## 规划逻辑

planner 不再默认只有一个 `focal concept`。现在它会从用户给出的主题和现有文献出发，把需要综述的构念、概念、机制和关系拆解出来。

当前的规划顺序是：

1. 追溯关键构念定义与概念边界
2. 提出章节级架构
3. 细化每个章节内部的段落级蓝图
4. 在冻结框架前与用户反复打磨

这意味着 planner 可以支持单概念综述、双概念关系综述、中介逻辑、调节逻辑，或者更开放的概念性主题，而不需要先被套进僵硬的预设模板。

## 计划存档机制

每次 planner 修订时，都会把当前活跃框架写入 `07_plan/review_plan.md`，同时在 `07_plan/history/` 下生成一个带时间戳的快照。

因此你会同时拥有两层规划记录：

- 当前正在执行的活跃框架 `review_plan.md`
- 完整的历史检查点 `07_plan/history/*.md`

当计划被批准或重新打开时，orchestrator 也会额外留下一个带时间戳的状态快照，方便长期追踪框架是如何演化的。

## MinerU 鉴权

MinerU 凭证不会写进代码，而是放在独立的 env 文件里，通常是：

`04_fulltext/mineru.env`

当前工作流支持两种鉴权路径：

1. `MINERU_API_KEY`
   如果你已经有可以直接调用 MinerU 的 token，就用这个。

2. `MINERU_ACCESS_KEY` + `MINERU_SECRET_KEY`
   如果你通过 OpenXLab SDK 鉴权，就使用这两个字段。工作流会先尝试把它们换成 JWT，然后再调用 MinerU。

请求头会自动规范成：

`Authorization: Bearer <token>`

一个典型的 env 文件如下：

```env
MINERU_API_KEY=
MINERU_ACCESS_KEY=replace-with-your-access-key
MINERU_SECRET_KEY=replace-with-your-secret-key
MINERU_API_BASE_URL=https://mineru.net
MINERU_MODEL_VERSION=vlm
MINERU_LANGUAGE=en
MINERU_ENABLE_FORMULA=true
MINERU_ENABLE_TABLE=true
MINERU_IS_OCR=false
```

建议做法：

- 如果你已经有可用的 MinerU bearer token，优先放在 `MINERU_API_KEY`
- 否则就存 `MINERU_ACCESS_KEY` 和 `MINERU_SECRET_KEY`
- 不要把任何凭证硬编码到脚本、说明文档或提示词里

## 推荐工作流

1. 用 `openalex-ajg-insights` 构建语料库。
2. 用 `management-review-planner` 生成第一版 `review_plan.md`。
3. 和用户一起打磨章节与段落蓝图。
4. 让每轮规划修订都生成一个时间戳存档。
5. 用户明确口头确认后，让 `review-orchestrator` 批准计划。
6. 再用 `management-review-writer` 在已批准框架内执行正文写作。

## 目录结构

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

## 建议的使用顺序

长期项目里，建议先用 `openalex-ajg-insights` 建立语料，用 manifest 驱动下载优先级 PDF，再让 `review-orchestrator` 判断当前工作区应该进入 planning 还是 writing。
