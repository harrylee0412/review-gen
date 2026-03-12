"""FastMCP server entry point for paper download MCP server."""

from mcp.server.fastmcp import FastMCP

from .runtime import get_runtime_config

# Initialize FastMCP server
mcp = FastMCP("paper-download-mcp")

# Legacy exports kept for backward compatibility with older imports.
EMAIL = get_runtime_config().email
DEFAULT_OUTPUT_DIR = get_runtime_config().default_output_dir


def _require_email() -> str:
    """
    Validate that email configuration is present.

    Returns:
        Email address

    Raises:
        ValueError: If PAPER_DOWNLOAD_EMAIL environment variable is not set
    """
    config = get_runtime_config()
    if not config.email:
        raise ValueError(
            "PAPER_DOWNLOAD_EMAIL environment variable is required.\n"
            "This email is used for Unpaywall API compliance.\n\n"
            "To configure:\n"
            "1. Set environment variable: export PAPER_DOWNLOAD_EMAIL=your-email@university.edu\n"
            "   (legacy fallback: SCIHUB_CLI_EMAIL)\n"
            "2. Or add to Claude Desktop config:\n"
            "   {\n"
            '     "mcpServers": {\n'
            '       "paper-download": {\n'
            '         "command": "uvx",\n'
            '         "args": ["paper-download-mcp"],\n'
            '         "env": {"PAPER_DOWNLOAD_EMAIL": "your-email@university.edu"}\n'
            "       }\n"
            "     }\n"
            "   }\n"
        )
    return config.email


def main():
    """Main entry point for the MCP server."""
    # Validate email configuration on startup
    _require_email()

    # Import tools to register them with the server
    # Must import before mcp.run() to ensure tools are registered
    from .tools import download, metadata  # noqa: F401

    # Run the FastMCP server with stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
