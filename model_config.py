import os

OLLAMA_HOST = "http://localhost:18434"
# MODEL = "qwen3.6:27b" 
MODEL = "gemma4:26b"
OPENAI_BASE_URL = f"{OLLAMA_HOST}/v1"

RESEARCH_MODEL = os.environ.get("RESEARCH_MODEL", MODEL)
INGESTION_MODEL = os.environ.get("INGESTION_MODEL", MODEL)
MENTORING_MODEL = os.environ.get("MENTORING_MODEL", MODEL)
VIVA_MODEL = os.environ.get("VIVA_MODEL", MODEL)

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # secret: set via env, not committed
ARXIV_SCRIPT = "research/arxiv_mcp.py"
