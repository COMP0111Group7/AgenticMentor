from contextlib import AsyncExitStack

from agent_framework import tool
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from model_config import GITHUB_TOKEN, GITHUB_MCP_URL


class GithubMCP:
    async def __aenter__(self):
        self._stack = AsyncExitStack()
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-MCP-Readonly": "true",
        }
        read, write, _ = await self._stack.enter_async_context(
            streamablehttp_client(GITHUB_MCP_URL, headers=headers)
        )
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    def _result_text(self, result):
        return "\n".join(b.text for b in result.content if hasattr(b, "text"))

    def tools(self):
        @tool
        async def github_search_repositories(query: str) -> str:
            """Search GitHub repositories by keyword."""
            result = await self.session.call_tool("search_repositories", {"query": query})
            return self._result_text(result)

        @tool
        async def github_get_file_contents(owner: str, repo: str, path: str) -> str:
            """Fetch a file's contents from a GitHub repository."""
            result = await self.session.call_tool(
                "get_file_contents", {"owner": owner, "repo": repo, "path": path}
            )
            return self._result_text(result)

        @tool
        async def github_search_code(query: str) -> str:
            """Search code across GitHub repositories."""
            result = await self.session.call_tool("search_code", {"query": query})
            return self._result_text(result)

        @tool
        async def github_list_issues(owner: str, repo: str) -> str:
            """List issues for a GitHub repository."""
            result = await self.session.call_tool("list_issues", {"owner": owner, "repo": repo})
            return self._result_text(result)

        return [
            github_search_repositories,
            github_get_file_contents,
            github_search_code,
            github_list_issues,
        ]
