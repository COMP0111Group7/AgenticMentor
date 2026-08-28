from pathlib import Path

from agent_framework import Agent, MCPStdioTool
from agent_framework.openai import OpenAIChatCompletionClient
from .local_github_mcp import GithubMCP
from model_config import OPENAI_BASE_URL, RESEARCH_MODEL, ARXIV_SCRIPT

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

async def run_research(spec_path: str, output_context_path: str, model: str = RESEARCH_MODEL) -> None:
    """Runs the research agent on a specification and saves the context."""
    with open(spec_path) as f:
        spec = f.read()

    arxiv = MCPStdioTool(name="arxiv", command="python", args=[ARXIV_SCRIPT])
    client = OpenAIChatCompletionClient(base_url=OPENAI_BASE_URL, api_key="not-needed", model=model)

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