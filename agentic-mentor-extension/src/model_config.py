import os
from dotenv import load_dotenv
load_dotenv()


OLLAMA_HOST = "http://localhost:18434"
MODEL = "qwen3.6:27b"
# MODEL = "gemma4:31b"
OPENAI_BASE_URL = f"{OLLAMA_HOST}/v1"

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # secret: set via env, not committed

