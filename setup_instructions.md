# Prepare Workflow

Install the dependencies into your python environment

```code
pip install -r requirements.txt
```

Set your GitHub token (used by the Research Agent's GitHub MCP):

```code
export GITHUB_TOKEN=<PASTE GITHUB PAT>
```

All other settings (model, Ollama host, GitHub MCP URL, arxiv script path) live in `model_config.py`.

# Run workflow

Run the orchestrator

```code
python orchestration.py
```
