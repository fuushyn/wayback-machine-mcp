# wayback-machine-mcp

An MCP (Model Context Protocol) server for interacting with the [Internet Archive Wayback Machine](https://web.archive.org/). Fetch archived snapshots, search history, and retrieve archived web content directly from your AI assistant.

## Tools

| Tool | Description |
|------|-------------|
| `get_latest_snapshot` | Get the most recent archived snapshot of any URL |
| `get_snapshot_at_date` | Get the closest snapshot to a specific date/time |
| `search_snapshots` | Search all archived snapshots with filters (date range, status code, limit) |
| `get_snapshot_content` | Fetch the full content of an archived page |
| `check_url_availability` | Check if a URL has been archived and see first/last snapshot dates |

## Installation

### Using `uv` (recommended)

```bash
uv pip install wayback-machine-mcp
```

### From source

```bash
git clone https://github.com/lakshyaag/wayback-machine-mcp
cd wayback-machine-mcp
pip install -e .
```

## Usage

### With Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "wayback-machine": {
      "command": "python",
      "args": ["/path/to/wayback-machine-mcp/server.py"]
    }
  }
}
```

Or with `uv`:

```json
{
  "mcpServers": {
    "wayback-machine": {
      "command": "uvx",
      "args": ["wayback-machine-mcp"]
    }
  }
}
```

### With any MCP client

Run the server directly:

```bash
python server.py
```

## Example Queries

Once connected, you can ask your AI assistant things like:

- *"What did Google's homepage look like in 2005?"*
- *"Find all archived snapshots of example.com from 2020"*
- *"Get the closest snapshot of twitter.com to January 1, 2023"*
- *"Has archive.org ever archived this URL: mysite.com?"*
- *"Fetch the content of an archived page from 2015"*

## API Details

This server uses two Wayback Machine APIs (no API key required):

- **[Availability API](https://archive.org/help/wayback_api.php)** — Fast lookup for the closest snapshot to a date
- **[CDX API](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server)** — Full search index with filtering and pagination

## Requirements

- Python 3.10+
- `mcp>=1.0.0`
- `httpx>=0.27.0`

## License

MIT
