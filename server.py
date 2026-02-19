"""
Wayback Machine MCP Server

An MCP server that provides tools for interacting with the Internet Archive's
Wayback Machine. Fetch snapshots, search history, and retrieve archived content.
"""

import asyncio
import json
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
)

# Initialize MCP server
app = Server("wayback-machine-mcp")

WAYBACK_AVAILABILITY_API = "http://archive.org/wayback/available"
WAYBACK_CDY A_API = "https://web.archive.org/cdx/search/cdx"
WAYBACK_BASE_URL = "https://web.archive.org/web"


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_latest_snapshot",
            description=(
                "Get the most recent archived snapshot of a URL from the Wayback Machine. "
                "Returns the snapshot URL, timestamp, and HTTP status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to look up in the Wayback Machine (e.g. 'example.com' or 'https://example.com/page')",
                    }
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="get_snapshot_at_date",
            description=(
                "Get the closest archived snapshot of a URL to a specific date/time. "
                "Returns the snapshot URL, timestamp, and HTTP status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to look up in the Wayback Machine",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": (
                            "The target date/time in YYYYMMDdhhmmss format (1-14 digits). "
                            "Examples: '20230101' for Jan 1 2023, '20230101120000' for noon on Jan 1 2023."
                        ),
                    },
                },
                "required": ["url", "timestamp"],
            },
        ),
        Tool(
            name="search_snapshots",
            description=(
                "Search the Wayback Machine CDX index for all archived snapshots of a URL. "
                "Returns a list of snapshots with timestamps, status codes, and MIME types. "
                "Supports date range filtering and result limits."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to search for (supports wildcards with '*', e.g. 'example.com/*')",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date filter in YYYYMMDD format (optional)",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date filter in YYYYMMDD format (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 100)",
                        "default": 10,
                    },
                    "status_code": {
                        "type": "string",
                        "description": "Filter by HTTP status code (e.g. '200', '404'). Optional.",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="get_snapshot_content",
            description=(
                "Fetch the raw content of a specific Wayback Machine snapshot. "
                "Returns the page content as text. Use get_latest_snapshot or search_snapshots first to get a snapshot URL."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "snapshot_url": {
                        "type": "string",
                        "description": "The full Wayback Machine snapshot URL (e.g. 'https://web.archive.org/web/20230101120000/https://example.com')",
                    },
                    "raw": {
                        "type": "boolean",
                        "description": "If true, fetch the raw archived content without Wayback Machine toolbar (default: false)",
                        "default": False,
                    },
                },
                "required": ["snapshot_url"],
            },
        ),
        Tool(
            name="check_url_availability",
            description=(
                "Check whether a URL has been archived in the Wayback Machine at all, "
                "and how many snapshots are available."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to check availability for",
                    }
                },
                "required": ["url"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    try:
        if name == "get_latest_snapshot":
            return await get_latest_snapshot(arguments)
        elif name == "get_snapshot_at_date":
            return await get_snapshot_at_date(arguments)
        elif name == "search_snapshots":
            return await search_snapshots(arguments)
        elif name == "get_snapshot_content":
            return await get_snapshot_content(arguments)
        elif name == "check_url_availability":
            return await check_url_availability(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def get_latest_snapshot(args: dict) -> CallToolResult:
    url = args["url"]
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            WAYBACK_AVAILABILITY_API,
            params={"url": url},
        )
        response.raise_for_status()
        data = response.json()

    snapshots = data.get("archived_snapshots", {})
    closest = snapshots.get("closest")

    if not closest or not closest.get("available"):
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"available": False, "url": url, "message": "No snapshots found for this URL"},
                        indent=2,
                    ),
                )
            ]
        )

    timestamp = closest["timestamp"]
    formatted_time = _format_timestamp(timestamp)

    result = {
        "available": True,
        "original_url": url,
        "snapshot_url": closest["url"],
        "timestamp": timestamp,
        "formatted_time": formatted_time,
        "status": closest.get("status", "unknown"),
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )


async def get_snapshot_at_date(args: dict) -> CallToolResult:
    url = args["url"]
    timestamp = args["timestamp"]

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            WAYBACK_AVAILABILITY_API,
            params={"url": url, "timestamp": timestamp},
        )
        response.raise_for_status()
        data = response.json()

    snapshots = data.get("archived_snapshots", {})
    closest = snapshots.get("closest")

    if not closest or not closest.get("available"):
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "available": False,
                            "url": url,
                            "requested_timestamp": timestamp,
                            "message": "No snapshots found near this date",
                        },
                        indent=2,
                    ),
                )
            ]
        )

    snap_timestamp = closest["timestamp"]
    result = {
        "available": True,
        "original_url": url,
        "requested_timestamp": timestamp,
        "snapshot_url": closest["url"],
        "actual_timestamp": snap_timestamp,
        "actual_formatted_time": _format_timestamp(snap_timestamp),
        "status": closest.get("status", "unknown"),
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )


async def search_snapshots(args: dict) -> CallToolResult:
    url = args["url"]
    limit = min(int(args.get("limit", 10)), 100)
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    status_code = args.get("status_code")

    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,length",
        "limit": limit,
    }
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    if status_code:
        params["filter"] = f"statuscode:{status_code}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(WAYBACK_CDY A_API, params=params)
        response.raise_for_status()
        raw = response.json()

    if not raw or len(raw) < 2:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"url": url, "total_found": 0, "snapshots": []}, indent=2
                    ),
                )
            ]
        )

    # First row is headers
    headers = raw[0]
    rows = raw[1:]

    snapshots = []
    for row in rows:
        entry = dict(zip(headers, row))
        ts = entry.get("timestamp", "")
        snapshots.append(
            {
                "timestamp": ts,
                "formatted_time": _format_timestamp(ts),
                "snapshot_url": f"{WAYBACK_BASE_URL}/{ts}/{entry.get('original', '')}",
                "original_url": entry.get("original", ""),
                "status_code": entry.get("statuscode", ""),
                "mime_type": entry.get("mimetype", ""),
                "size_bytes": entry.get("length", ""),
            }
        )

    result = {
        "url": url,
        "total_found": len(snapshots),
        "snapshots": snapshots,
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )


async def get_snapshot_content(args: dict) -> CallToolResult:
    snapshot_url = args["snapshot_url"]
    raw = args.get("raw", False)

    # For raw mode, insert 'id_' flag into the Wayback URL
    if raw and "/web/" in snapshot_url:
        parts = snapshot_url.split("/web/", 1)
        ts_and_url = parts[1].split("/", 1)
        if len(ts_and_url) == 2:
            snapshot_url = f"{parts[0]}/web/{ts_and_url[0]}id_/{ts_and_url[1]}"

    async with httpx.AsyncClient(
        timeout=60, follow_redirects=True, headers={"User-Agent": "wayback-machine-mcp/1.0"}
    ) as client:
        response = await client.get(snapshot_url)
        response.raise_for_status()
        content = response.text

    # Truncate if too large
    MAX_CHARS = 50_000
    truncated = len(content) > MAX_CHARS
    if truncated:
        content = content[:MAX_CHARS]

    result = {
        "snapshot_url": snapshot_url,
        "content_length": len(content),
        "truncated": truncated,
        "content": content,
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )


async def check_url_availability(args: dict) -> CallToolResult:
    url = args["url"]

    # Use CDX to count total snapshots
    async with httpx.AsyncClient(timeout=30) as client:
        # Get count
        count_response = await client.get(
            WAYBACK_CDX_API,
            params={"url": url, "output": "json", "fl": "timestamp", "limit": 1, "showNumPages": "true"},
        )

        # Get first and last snapshots
        first_response = await client.get(
            WAYBACK_CDX_API,
            params={"url": url, "output": "json", "fl": "timestamp,statuscode", "limit": 1},
        )
        last_response = await client.get(
            WAYBACK_CDX_API,
            params={"url": url, "output": "json", "fl": "timestamp,statuscode", "limit": 1, "fastLatest": "true"},
        )

    first_data = first_response.json() if first_response.status_code == 200 else []
    last_data = last_response.json() if last_response.status_code == 200 else []

    first_snapshot = None
    last_snapshot = None

    if first_data and len(first_data) > 1:
        ts = first_data[1][0]
        first_snapshot = {"timestamp": ts, "formatted_time": _format_timestamp(ts)}

    if last_data and len(last_data) > 1:
        ts = last_data[1][0]
        last_snapshot = {"timestamp": ts, "formatted_time": _format_timestamp(ts)}

    result = {
        "url": url,
        "is_archived": first_snapshot is not None,
        "first_snapshot": first_snapshot,
        "latest_snapshot": last_snapshot,
        "wayback_url": f"https://web.archive.org/web/*/{url}",
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )


def _format_timestamp(ts: str) -> str:
    """Convert YYYYMMDDthmmss to a readable datetime string."""
    try:
        ts = ts.ljust(14, "0")
        dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
