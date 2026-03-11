# OpenAlex & ABS Literature Search MCP

[![PyPI version](https://img.shields.io/pypi/v/openalex-ajg-mcp.svg)](https://pypi.org/project/openalex-ajg-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/openalex-ajg-mcp.svg)](https://pypi.org/project/openalex-ajg-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](#english) | [中文](#中文)

---

## English

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that helps AI agents search for high-quality academic literature using **OpenAlex** and the **ABS (AJG) Academic Journal Guide** ranking.

### Features

- **Smart Filtering**: Search only within ABS-ranked journals (e.g., Marketing 4*, Accounting 3+)
- **All Fields Search**: Leave `field` empty to search across ALL ABS journals (includes general management journals like AMJ, AMR, ASQ, etc.)
- **Excel Reports**: Auto-generate `.xlsx` reports with full metadata and reconstructed abstracts
- **RIS Export**: Standard citation files for EndNote/Zotero/Mendeley
- **Multi-language**: Auto-detects query language (English/Chinese) for localized summaries
- **AJG 2024**: Uses the latest Academic Journal Guide (2024 edition) data

### Installation

```bash
pip install openalex-ajg-mcp
```

Or using `uvx` (recommended for MCP):

```bash
uvx openalex-ajg-mcp
```

### Configuration

#### For Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "openalex": {
      "command": "openalex-ajg-mcp",
      "args": []
    }
  }
}
```

#### For Gemini Code / Other MCP Clients

Add to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["--refresh", "openalex-ajg-mcp"]
    }
  }
}
```

### Usage

#### Tool: `search_abs_literature`

Ask your AI assistant to search for academic literature:

> "Search for 'AI Agents' in 4* Information Management journals since 2023."

Or use the tool directly with parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | (required) | Search keywords |
| `field` | string | `""` (empty) | ABS Field Code (see table below). **Leave empty to search ALL ABS journals** (recommended for interdisciplinary topics) |
| `min_rank` | string | `"3"` | Minimum journal rank: `"3"`, `"4"`, or `"4*"` |
| `limit` | int | `0` | Maximum number of results (0 = all, up to 2000) |
| `year_start` | int | `2024` | Filter papers from this year onwards |
| `export` | bool | `False` | Set to `True` to generate Excel/RIS files |
| `lang` | string | `"auto"` | Output language: `"cn"`, `"en"`, or `"auto"` |

**Important**: 
- If you **don't specify a field**, the search will cover **all ABS-ranked journals** across all disciplines. This ensures you don't miss important papers published in general management journals (e.g., Academy of Management Journal, Administrative Science Quarterly).
- If you **specify a field** (e.g., `MKT`), the search will only cover journals in that specific discipline.

#### Tool: `search_journal_literature`

Search for literature within a specific journal (e.g., "Journal of Business Venturing").

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `journal_name` | string | (required) | Full journal name or abbreviation |
| `query` | string | (required) | Keywords (Use `*` for all papers in that year) |
| `year_start` | int | `2024` | Start year |
| `limit` | int | `0` | Max results |
| `export` | bool | `False` | Generate files |

#### Tool: `summarize_literature_report`

Generate a statistical summary from an exported Excel report.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string | (required) | Absolute path to the Excel file |
| `lang` | string | `"auto"` | Output language |

### ABS Field Codes

| Code | Field Name |
|------|------------|
| `ACCOUNT` | Accounting |
| `BUS HIST & ECON HIST` | Business History & Economic History |
| `ECON` | Economics |
| `ENT-SBM` | Entrepreneurship & Small Business Management |
| `ETHICS-CSR-MAN` | Ethics, CSR & Management (includes AMJ, AMR, ASQ) |
| `FINANCE` | Finance |
| `HRM&EMP` | Human Resource Management & Employment Studies |
| `IB&AREA` | International Business & Area Studies |
| `INFO MAN` | Information Management |
| `INNOV` | Innovation |
| `MDEV&EDU` | Management Development & Education |
| `MKT` | Marketing |
| `OPS&TECH` | Operations & Technology Management |
| `OR&MANSCI` | Operations Research & Management Science |
| `ORG STUD` | Organization Studies |
| `PSYCH (GENERAL)` | Psychology (General) |
| `PSYCH (WOP-OB)` | Psychology (Work & Organizational) |
| `PUB SEC` | Public Sector & Health Care |
| `REGIONAL STUDIES, PLANNING AND ENVIRONMENT` | Regional Studies |
| `SECTOR` | Sector Studies |
| `SOC SCI` | Social Sciences |
| `STRAT` | Strategy |

### Example Output

```
## Literature Search Report

Found **15** papers (Field: ALL Fields, Rank: 4+, Year: 2023+).
Files Generated:
- Excel Report: `report_ALL_4.xlsx`
- RIS Citations: `citations_ALL_4.ris`

### Top Recommended (Most Cited)
**1. The Janus Effect of Generative AI...**
- 2023 | Information Systems Research | Citations: 199
- Abstract: ...
```

### Generated Files

| File | Description |
|------|-------------|
| `report_[FIELD]_[RANK].xlsx` | Excel spreadsheet with Journal, Year, Title, Authors, Citations, DOI, Abstract |
| `citations_[FIELD]_[RANK].ris` | RIS format citations for import into reference managers |

### Development

```bash
# Clone the repository
git clone https://github.com/harrylee0412/openalex-ajg-mcp.git
cd openalex-ajg-mcp

# Install in development mode
pip install -e .

# Run locally
python -m openalex_mcp
```

### Data Source

- **OpenAlex**: Free and open catalog of the world's scholarly papers ([openalex.org](https://openalex.org))
- **ABS Academic Journal Guide 2024**: Published by the Chartered Association of Business Schools

### License

MIT License - see [LICENSE](LICENSE) for details.

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 中文

一个 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 服务器，帮助 AI 助手使用 **OpenAlex** 和 **ABS (AJG) 学术期刊指南** 排名搜索高质量的学术文献。

### 功能特点

- **智能筛选**: 仅在 ABS 排名期刊中搜索（如营销 4*、会计 3+）
- **全领域搜索**: 不指定 `field` 时将搜索所有 ABS 期刊（包括 AMJ、AMR、ASQ 等综合管理期刊）
- **Excel 报告**: 自动生成包含完整元数据和重建摘要的 `.xlsx` 报告
- **RIS 导出**: 标准引文文件，可导入 EndNote/Zotero/Mendeley
- **多语言支持**: 自动检测查询语言（中/英文）生成本地化摘要
- **AJG 2024**: 使用最新的学术期刊指南（2024 版）数据

### 安装

```bash
pip install openalex-ajg-mcp
```

或使用 `uvx`（推荐用于 MCP）：

```bash
uvx openalex-ajg-mcp
```

### 配置

#### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "openalex": {
      "command": "openalex-ajg-mcp",
      "args": []
    }
  }
}
```

#### Gemini Code / 其他 MCP 客户端

在 `mcp_config.json` 中添加：

```json
{
  "mcpServers": {
    "openalex": {
      "command": "uvx",
      "args": ["--refresh", "openalex-ajg-mcp"]
    }
  }
}
```

### 使用方法

#### 工具: `search_abs_literature`

让 AI 助手搜索学术文献：

> "搜索 2023 年以来信息管理领域 4* 期刊中关于 'AI Agents' 的论文。"

或直接使用参数调用工具：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | string | (必填) | 搜索关键词 |
| `field` | string | `""`（空） | ABS 领域代码（见下表）。**留空则搜索所有 ABS 期刊**（推荐用于跨学科研究） |
| `min_rank` | string | `"3"` | 最低期刊等级：`"3"`、`"4"` 或 `"4*"` |
| `limit` | int | `0` | 最大结果数（0 = 全部，最多 2000） |
| `year_start` | int | `2024` | 起始年份 |
| `export` | bool | `False` | 设为 `True` 生成 Excel/RIS 文件 |
| `lang` | string | `"auto"` | 输出语言：`"cn"`、`"en"` 或 `"auto"` |

**重要说明**: 
- **不指定领域**时，搜索将覆盖**所有 ABS 排名期刊**，这样可以确保不会遗漏发表在综合管理期刊（如 Academy of Management Journal、Administrative Science Quarterly）中的重要论文。
- **指定领域**（如 `MKT`）时，搜索仅覆盖该特定学科的期刊。

#### 工具: `search_journal_literature`

在特定期刊中搜索文献（如 "Journal of Business Venturing"）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `journal_name` | string | (必填) | 期刊全名或缩写 |
| `query` | string | (必填) | 关键词（使用 `*` 获取该年份所有论文） |
| `year_start` | int | `2024` | 起始年份 |
| `limit` | int | `0` | 最大结果数 |
| `export` | bool | `False` | 生成文件 |

#### 工具: `summarize_literature_report`

从导出的 Excel 报告生成统计摘要。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | string | (必填) | Excel 文件的绝对路径 |
| `lang` | string | `"auto"` | 输出语言 |

### ABS 领域代码

| 代码 | 领域名称 |
|------|----------|
| `ACCOUNT` | 会计 |
| `BUS HIST & ECON HIST` | 商业史与经济史 |
| `ECON` | 经济学 |
| `ENT-SBM` | 创业与小企业管理 |
| `ETHICS-CSR-MAN` | 伦理、CSR 与管理（含 AMJ、AMR、ASQ） |
| `FINANCE` | 金融 |
| `HRM&EMP` | 人力资源管理与雇佣研究 |
| `IB&AREA` | 国际商务与区域研究 |
| `INFO MAN` | 信息管理 |
| `INNOV` | 创新 |
| `MDEV&EDU` | 管理发展与教育 |
| `MKT` | 营销 |
| `OPS&TECH` | 运营与技术管理 |
| `OR&MANSCI` | 运筹学与管理科学 |
| `ORG STUD` | 组织研究 |
| `PSYCH (GENERAL)` | 心理学（通用） |
| `PSYCH (WOP-OB)` | 心理学（工作与组织） |
| `PUB SEC` | 公共部门与医疗 |
| `REGIONAL STUDIES, PLANNING AND ENVIRONMENT` | 区域研究 |
| `SECTOR` | 行业研究 |
| `SOC SCI` | 社会科学 |
| `STRAT` | 战略 |

### 示例输出

```
## 文献搜索报告

已找到 **15** 篇文献 (领域: 所有领域, 等级: 4+, 年份: 2023+)。
文件已导出:
- Excel 报告: `report_ALL_4.xlsx`
- RIS 引文: `citations_ALL_4.ris`

### 高引推荐
**1. The Janus Effect of Generative AI...**
- 2023 | Information Systems Research | 引用: 199
- 摘要: ...
```

### 生成的文件

| 文件 | 说明 |
|------|------|
| `report_[领域]_[等级].xlsx` | Excel 电子表格，包含期刊、年份、标题、作者、引用数、DOI、摘要 |
| `citations_[领域]_[等级].ris` | RIS 格式引文，可导入参考文献管理器 |

### 开发

```bash
# 克隆仓库
git clone https://github.com/harrylee0412/openalex-ajg-mcp.git
cd openalex-ajg-mcp

# 开发模式安装
pip install -e .

# 本地运行
python -m openalex_mcp
```

### 数据来源

- **OpenAlex**: 全球学术论文的免费开放目录 ([openalex.org](https://openalex.org))
- **ABS 学术期刊指南 2024**: 由英国特许商学院协会发布

### 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)。

### 贡献

欢迎贡献！请随时提交 Pull Request。
