import os
from pathlib import Path
import asyncio


from agent_framework import Agent, MCPStdioTool
from agent_framework.openai import OpenAIChatCompletionClient
from local_github_mcp import GithubMCP

from model_config import OPENAI_BASE_URL, MODEL


# set LOCAL_MODEL_URL, MODEL_NAME, ARXIV_SCRIPT as env vars before running
LOCAL_MODEL_URL = OPENAI_BASE_URL
MODEL_NAME = MODEL
DIRNAME = Path(__file__).resolve().parent
ARXIV_SCRIPT =os.path.join(DIRNAME, "arxiv_mcp.py")

PROMPT_TEMPLATE = (
    "Below is a project specification. You have two tools: arxiv search "
    "and GitHub search. You MUST use both — first call search_papers "
    "at least once for relevant arxiv papers, AND separately call "
    "github_search_repositories or github_search_code at least once "
    "for relevant real-world implementations. Do not skip either tool. "
    "This research will be used by the next agent to understand the "
    "context of the problem, so structure your findings clearly "
    "(by topic, with paper titles/repo names and key takeaways).\n\n"
    "Keep it concise: max 2-3 bullet points per source, no more than "
    "500 words total. Skip sources that aren't directly relevant. "
    "Only cite a GitHub repository if you actually called a github_* "
    "tool and got a real result back — never invent repository names "
    "from memory. If a github_* tool call returns nothing relevant, "
    "say so explicitly rather than substituting a remembered repo.\n\n"
    "--- SPECIFICATION ---\n{spec}\n--- END SPECIFICATION ---"
)

async def run_research(spec_path: str, output_context_path: str, model: str = None) -> None:
    """Runs the research agent on a specification and saves the context."""
    with open(spec_path) as f:
        spec = f.read()
    selected_model = model or MODEL_NAME
    arxiv = MCPStdioTool(name="arxiv", command=f"{DIRNAME.parent}/venv/bin/python3", args=[ARXIV_SCRIPT])

    client = OpenAIChatCompletionClient(base_url=LOCAL_MODEL_URL, api_key="not-needed", model=selected_model)
    async with GithubMCP() as github, arxiv, Agent(
        client=client,
        name="ResearchAgent",
        instructions="You help find and summarize arxiv papers and GitHub repositories relevant to a given specification. GitHub access is read-only.",
    ) as agent:
        result = await agent.run(
            PROMPT_TEMPLATE.format(spec=spec),
            tools=[arxiv, *github.tools()],
            client_kwargs={"extra_body": {"options": {"num_ctx": 16384}}},
            function_invocation_kwargs={"max_function_calls": 6},
        )

    # Ensure output directory exists before writing
    out_path = Path(output_context_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w") as f:
        f.write(result.text)

async def main():
    import sys
    if len(sys.argv) not in (3, 4):
        print("Usage: python research_agent.py <spec_path> <output_context_path> [model]")
        sys.exit(1)
    spec_path = sys.argv[1]
    output_context_path = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) == 4 else None
    await run_research(spec_path, output_context_path, model)

if __name__ == "__main__":
    asyncio.run(main())