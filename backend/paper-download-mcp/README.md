# Paper Download MCP Server

English | [简体中文](https://github.com/Oxidane-bot/paper-download-mcp/blob/main/README.zh-CN.md)

MCP server for downloading academic papers by DOI, arXiv ID, or URL.

## What You Get

- `paper_download`: Download one or more papers (1-50 per call)
- `paper_get_metadata`: Get paper metadata without downloading
- Optional PDF-to-Markdown conversion via `to_markdown`

## Quick Start (MCP Clients)

Before configuration, make sure `uvx` is available:

```bash
uvx --version
```

### Claude Code

Add as a project-scoped MCP server:

```bash
claude mcp add --transport stdio --scope project --env PAPER_DOWNLOAD_EMAIL=your-email@university.edu paper-download -- uvx paper-download-mcp
```

This writes `.mcp.json` in the current project. Equivalent config:

```json
{
  "mcpServers": {
    "paper-download": {
      "command": "uvx",
      "args": ["paper-download-mcp"],
      "env": {
        "PAPER_DOWNLOAD_EMAIL": "your-email@university.edu"
      }
    }
  }
}
```

### Codex

Add with CLI:

```bash
codex mcp add paper-download --env PAPER_DOWNLOAD_EMAIL=your-email@university.edu -- uvx paper-download-mcp
```

Equivalent `~/.codex/config.toml` snippet:

```toml
[mcp_servers.paper-download]
command = "uvx"
args = ["paper-download-mcp"]

[mcp_servers.paper-download.env]
PAPER_DOWNLOAD_EMAIL = "your-email@university.edu"
```

### Claude Desktop

Edit Claude Desktop MCP config:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "paper-download": {
      "command": "uvx",
      "args": ["paper-download-mcp"],
      "env": {
        "PAPER_DOWNLOAD_EMAIL": "your-email@university.edu"
      }
    }
  }
}
```

Restart Claude Desktop after editing the file.

## Configuration

### Required

- `PAPER_DOWNLOAD_EMAIL`: Required for Unpaywall API usage.

### Optional (Advanced)

- `PAPER_DOWNLOAD_OUTPUT_DIR`: Global fallback output directory.

In most cases, you do not need `PAPER_DOWNLOAD_OUTPUT_DIR`. Prefer passing `output_dir` in the `paper_download` tool call when you want a specific location.

Legacy env vars are still supported for compatibility:

- `SCIHUB_CLI_EMAIL`
- `SCIHUB_OUTPUT_DIR`

## Tools

### `paper_download`

Download papers with configurable concurrency (default `parallel=10`).
If `parallel=1`, papers are processed sequentially with a 2-second delay between items.
OA-first routing uses OpenAlex and Unpaywall first; CORE is disabled by default in MCP runtime.

Parameters:

- `identifiers` (required): `list[str]`, 1-50 items
- `output_dir` (optional): target directory (default uses runtime fallback: `PAPER_DOWNLOAD_OUTPUT_DIR` or `./downloads`)
- `parallel` (optional): concurrent workers, `1-50` (default `10`)
- `to_markdown` (optional): convert PDF to Markdown (`false` by default)
- `md_output_dir` (optional): Markdown directory (default `<output_dir>/md`)

Examples:

```text
paper_download(["10.1038/nature12373"])
paper_download(["10.1038/nature12373", "2301.00001"], output_dir="/path/to/papers")
paper_download(["10.1038/nature12373", "10.1126/science.169.3946.635"], parallel=10)
paper_download(["10.1038/nature12373"], to_markdown=true)
```

### `paper_get_metadata`

Get metadata quickly (no PDF download).

Parameters:

- `identifier` (required): DOI, arXiv ID, or URL

Example:

```text
paper_get_metadata("10.1038/nature12373")
```

## Troubleshooting

### `PAPER_DOWNLOAD_EMAIL environment variable is required`

Set `PAPER_DOWNLOAD_EMAIL` in your MCP server config.

### `uvx: command not found`

Install `uv`, then re-run the MCP configuration.

### Download path errors

Pass a writable directory with `output_dir`, for example:

```text
paper_download(["10.1038/nature12373"], output_dir="/absolute/path")
```

## Legal Notice

This tool can access papers from multiple sources, including Unpaywall and Sci-Hub. You are responsible for complying with copyright and local laws in your jurisdiction.

## License

MIT. See `LICENSE`.
