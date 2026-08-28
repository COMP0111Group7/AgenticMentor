### Research Literature: Multi-Agent Orchestration & Workflows (ArXiv)
*Note: Academic literature heavily leans toward theoretical simulations and reinforcement learning rather than practical software pipeline orchestration.*

- **"From Model-Based Screening to Data-Driven Surrogates: A Multi-Stage Workflow for Exploring Stochastic Agent-Based Models"**  
  Proposes a multi-stage automated pipeline that uses model-based screening to identify dominant variables, followed by machine-learning surrogates to map complex nonlinear interactions. Provides a theoretical blueprint for structuring deterministic agent workflows in highly stochastic environments.
  
- **"A Survey of Multi-Agent Deep Reinforcement Learning with Communication"**  
  Establishes nine critical dimensions for analyzing inter-agent communication (e.g., broadcast vs. targeted, conditional constraints). Highlights that effective multi-agent systems require explicit structural classifications of how agents share context—an architectural concept directly applicable to configuring MCP tools and local LLM routing.

### Real-World Implementations: Agent Orchestrators & Pipelines (GitHub)
*Focuses on modern frameworks that support dynamic task graphs, local models, and specialized agent separation.*

- **`microsoft/agent-framework`**  
  - A robust Python SDK explicitly built for orchestrating multi-agent workflows. 
  - Highly relevant to the `orchestration.py` specification; it provides enterprise-grade scaffolding to delegate tasks across distinct agents (e.g., Research vs. Ingestion) while managing API dependencies and environment states cleanly.

- **`open-multi-agent/open-multi-agent`**  
  - A widely adopted framework that dynamically builds task DAGs at runtime based on a user's high-level goal, rather than relying on static graphs.
  - Excellent reference for designing systems that route between varied LLMs, demonstrating best practices for managing local model contexts and parallel agent execution.

- **`golutra/golutra`**  
  - A Rust-based platform designed to unify multiple coding agents (like Codex or proprietary tools) into a single automated workspace supporting long-running, parallelized workflows.
  - Offers architectural insights into abstracting different LLM endpoints behind a unified orchestration layer, similar to configuring `LOCAL_MODEL_URL` and `GITHUB_MCP_URL` simultaneously.