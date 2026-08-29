import asyncio
import os
import sys
from pathlib import Path

from research.research_agent import run_research
from ingestion_agent import run_ingestion
from model_config import RESEARCH_MODEL, INGESTION_MODEL, MENTORING_MODEL, VIVA_MODEL

REPO_ROOT = Path(__file__).resolve().parent


def choose_model(stage: str, default: str) -> str:
    choice = input(f"Model for {stage} [{default}]: ").strip()
    return choice or default


async def run_agent_process(label: str, script: Path, *args: str, cwd: Path) -> None:
    """Run an agent as a child process, inheriting this terminal so its
    interactive prompts (input()) go straight to the student. Stops the whole
    workflow if the agent exits with an error.

    If this process is interrupted (Ctrl+C) or cancelled while waiting, the
    child is terminated too -- otherwise cancelling `proc.wait()` only stops
    us from watching it, leaving the actual subprocess running as an orphan
    with its own in-flight requests."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(script), *args, cwd=str(cwd)
    )
    try:
        returncode = await proc.wait()
    except BaseException:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        raise
    if returncode != 0:
        raise SystemExit(f"{label} exited with code {returncode} -- stopping workflow.")


async def main():
    # Inputs (both optional): the student's spec, and a session id used to key
    # the mentoring progress/summary so a run can be resumed.
    spec_path = sys.argv[1] if len(sys.argv) > 1 else "agent_files/prompt.md"
    session_id = sys.argv[2] if len(sys.argv) > 2 else "orchestration_session"
    context_path = "research/context.md"

    # Derived paths that thread the stages together. The Ingestion Agent writes
    # the feature under specs/<stem>/, and the Mentoring Agent writes its handoff
    # summary keyed by feature + session id -- the Viva Agent consumes both.
    feature_name = Path(spec_path).stem
    generated_spec = REPO_ROOT / "specs" / feature_name / "spec.md"
    summary_path = (
        REPO_ROOT / "mentoring_agent_v2" / "session_summaries"
        / f"{feature_name}__{session_id}.md"
    )

    print("--- Starting Agentic Mentor Orchestration ---")
    print(f"Target Specification: {spec_path}")
    print(f"Feature: {feature_name} | Session: {session_id}")

    # Phase 1: Research
    research_model = choose_model("research", RESEARCH_MODEL)
    print("\n=== PHASE 1: RUNNING RESEARCH AGENT ===")
    await run_research(spec_path, context_path, research_model)
    print(f"Research complete. Context written to {context_path}")

    # Phase 2: Ingestion
    ingestion_model = choose_model("ingestion", INGESTION_MODEL)
    print("\n=== PHASE 2: RUNNING INGESTION AGENT ===")
    await run_ingestion(spec_path, context_path, ingestion_model)
    print("Ingestion complete. Spec, plan, tasks and learning objectives generated.")

    if not generated_spec.exists():
        raise SystemExit(
            f"Expected {generated_spec.relative_to(REPO_ROOT)} after ingestion but it "
            "wasn't produced -- cannot continue to mentoring."
        )

    # Phase 3: Mentoring (interactive: phase-by-phase build + MCQ checkpoints)
    os.environ["MENTORING_MODEL"] = choose_model("mentoring", MENTORING_MODEL)
    print("\n=== PHASE 3: RUNNING MENTORING AGENT ===")
    await run_agent_process(
        "Mentoring Agent",
        REPO_ROOT / "mentoring_agent_v2" / "mentor_agent.py",
        feature_name,
        session_id,
        cwd=REPO_ROOT,
    )
    print(f"Mentoring complete. Summary at {summary_path.relative_to(REPO_ROOT)}")

    if not summary_path.exists():
        raise SystemExit(
            f"Expected mentoring summary at {summary_path.relative_to(REPO_ROOT)} but it "
            "wasn't produced -- cannot run the viva."
        )

    # Phase 4: Viva (interactive oral exam grounded in the spec + mentor summary).
    # Runs with cwd in viva_agent/ so its relative config paths (system prompt,
    # chat history, transcript) resolve locally; artifact paths are passed absolute.
    os.environ["VIVA_MODEL"] = choose_model("viva", VIVA_MODEL)
    print("\n=== PHASE 4: RUNNING VIVA AGENT ===")
    await run_agent_process(
        "Viva Agent",
        REPO_ROOT / "viva_agent" / "viva_agent.py",
        str(summary_path),
        str(generated_spec),
        cwd=REPO_ROOT / "viva_agent",
    )

    print("\n--- Agentic Mentor Orchestration complete ---")


def cli():
    asyncio.run(main())


if __name__ == "__main__":
    cli()
