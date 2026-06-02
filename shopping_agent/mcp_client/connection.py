"""Connects to a Playwright MCP server over stdio and manages its lifecycle."""
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class PlaywrightMCP:
    def __init__(self, headless: bool = True, user_data_dir: str | None = ".pw-profile",
                 extra_args: list[str] | None = None):
        args = ["@playwright/mcp@latest"]
        if headless:
            args.append("--headless")
        if user_data_dir:
            args += ["--user-data-dir", os.path.abspath(user_data_dir)]
        if extra_args:
            args.extend(extra_args)
        self._params = StdioServerParameters(command="npx", args=args)
        self._stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "PlaywrightMCP":
        read, write = await self._stack.enter_async_context(stdio_client(self._params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()
        self.session = None
