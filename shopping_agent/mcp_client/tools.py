"""Helpers for discovering and calling MCP tools, and reading their results."""
from mcp import ClientSession
from mcp.types import CallToolResult


async def list_tool_names(session: ClientSession) -> list[str]:
    resp = await session.list_tools()
    return [t.name for t in resp.tools]


async def call(session: ClientSession, name: str, **args) -> CallToolResult:
    return await session.call_tool(name, args)


def result_text(result: CallToolResult) -> str:
    """Flatten a tool result's content blocks into plain text."""
    parts = [getattr(block, "text", "") for block in result.content]
    return "\n".join(p for p in parts if p)


def result_image(result: CallToolResult) -> tuple[str, str] | None:
    """Extract the first image block as (base64_data, mime_type), or None."""
    for block in result.content:
        if getattr(block, "type", None) == "image":
            return block.data, block.mimeType
    return None
