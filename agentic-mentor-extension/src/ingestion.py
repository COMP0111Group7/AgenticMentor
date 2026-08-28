import asyncio
import os
import re

from pathlib import Path
import sys
from model_config import MODEL,OLLAMA_HOST

from agent_framework import Agent, SkillsProvider
from agent_framework.ollama import OllamaChatClient

REPO_ROOT = sys.argv[1]
REPO_ROOT=Path(REPO_ROOT).resolve()
CLARIFY_DONE_TOKEN = "CLARIFY_COMPLETE"


# Must stay in sync with the phase-header contract mentoring_agent_v2/mentor_agent.py
# parses tasks.md with (see PHASE_HEADER_RE / parse_phases there). If tasks.md has no
# heading matching this, the Mentoring Agent hard-crashes before mentoring can start.
PHASE_HEADER_RE = re.compile(r"^## Phase (\d+):\s*(.+)$", re.MULTILINE)
MAX_TASKS_FORMAT_RETRIES = 3

async def run_script(command: str) -> str:
    if not command.strip().startswith(str(REPO_ROOT / ".specify" / "scripts")):
        return "ERROR: run_script may only execute scripts under .specify/scripts/"
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=REPO_ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return out.decode(errors="replace")

async def read_file(path: str) -> str:
    target = (REPO_ROOT / path).resolve()
    if REPO_ROOT not in target.parents and target != REPO_ROOT:
        return "ERROR: path escapes repo root"
    if target.is_dir():
        return f"ERROR: expected a file but got directory: {path}"
    if not target.exists():
        return f"ERROR: {path} does not exist"
    return target.read_text()

async def write_file(path: str, content: str) -> str:
    target = (REPO_ROOT / path).resolve()
    if REPO_ROOT not in target.parents and target != REPO_ROOT:
        return "ERROR: path escapes repo root"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"wrote {len(content)} chars to {path}"

def build_agent(model:str) -> Agent:
    # Real spec-kit instructions live here as SKILL.md files (converted from
    # .github/agents/speckit.*.agent.md). SkillsProvider only discovers directories
    # that directly contain a file literally named "SKILL.md" -- .github/agents/
    # contains *.agent.md files, which it silently ignores (zero skills loaded,
    # no error). Keep this pointed at .github/skills/.
    # First-party skills from this repo -- safe to skip the interactive
    # load_skill/read_skill_resource approval gate. Without this, load_skill
    # calls stop and wait for approval that nothing in this driver script ever
    # grants, so the agent's turn ends with empty text and the pipeline hangs.
    speckit_skills = SkillsProvider.from_paths(
        skill_paths=".github/skills/",
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
    )

    instructions = (
        "You are the Ingestion Agent for the Agentic Mentor system.\n\n"
        "You will be driven through a fixed sequence of spec-kit slash commands, "
        "one per turn: /speckit.specify, /speckit.clarify, /speckit.plan, /speckit.tasks, "
        "and finally a custom synthesis step. Before acting on any of these commands, "
        "use the `load_skill` tool to load the matching skill "
        "(speckit-specify, speckit-clarify, speckit-plan, or speckit-tasks) and follow its "
        "instructions exactly, using the run_script/read_file/write_file tools to interact "
        "with the filesystem -- do not just describe what you would do, and do not rely on "
        "your own memory of what spec-kit commands do instead of the loaded skill.\n\n"
        "CLARIFY PHASE RULES:\n"
        "- If, after running /speckit.clarify, there are still unresolved ambiguities, "
        "ask the student your questions directly and stop -- do not guess answers yourself.\n"
        f"- Once there are no more outstanding questions, output the line {CLARIFY_DONE_TOKEN} "
        "on its own line so the calling script knows to proceed.\n\n"
        "TASKS.MD FORMAT CONTRACT (applies to /speckit.tasks output -- non-negotiable):\n"
        "- Every phase in tasks.md MUST be introduced by a level-2 markdown heading of the "
        "EXACT form '## Phase <N>: <Title>', where <N> is a literal sequential integer "
        "(1, 2, 3, ...). The downstream Mentoring Agent parses tasks.md with the regex "
        "'^## Phase (\\d+): (.+)$' and will hard-crash before mentoring starts if even one "
        "phase heading fails to match it.\n"
        "- Correct: '## Phase 1: Setup', '## Phase 2: Foundational', "
        "'## Phase 6: Polish & Cross-Cutting Concerns'.\n"
        "- WRONG -- do not do any of these: '## Phase N: Polish & Cross-Cutting Concerns' "
        "(the tasks-template.md placeholder 'N' left unreplaced -- this is the most common "
        "mistake, always replace it with the next sequential integer), "
        "'### Phase 1: Setup' (wrong heading level), "
        "'## Phase One: Setup' (number must be numeric, not spelled out), "
        "'**Phase 1: Setup**' (bold text is not a heading).\n"
        "- Every phase, including Setup, Foundational, each user story, and the final Polish "
        "phase, needs its own numbered '## Phase N:' heading -- do not merge phases or skip "
        "numbers.\n\n"
        "FINAL SYNTHESIS (after /speckit.tasks completes):\n"
        "Read the feature's spec.md, the provided research context file, and the newly generated tasks.md. "
        "You must then use the `write_file` tool to create a 'learning_objectives.md' file "
        "in the same directory as the spec, containing a comprehensive list of Academic Learning Objectives."
    )

    return Agent(
        client=OllamaChatClient(host=OLLAMA_HOST, model=model),
        name="IngestionAgent",
        instructions=instructions,
        context_providers=[speckit_skills],
        tools=[run_script, read_file, write_file],
    )

async def run_clarify_loop(agent: Agent, session, spec_path: Path) -> None:
    rel_path = spec_path.relative_to(REPO_ROOT)
    
    prompt = (
        f"/speckit.clarify\n\n"
        f"The feature specification is located at '{rel_path}'. "
        f"You MUST use the `read_file` tool to read this file before attempting to clarify. "
        f"Do not guess the contents."
    )
    result = await agent.run(prompt, session=session)
    while CLARIFY_DONE_TOKEN not in result.text:
        print("\n## CLARIFY PHASE ")
        print(result.text)
        # TODO: replace input() with however our solution collects the
        # student's answer (chat UI, website, etc.)
        # student_answer = input("\nYour answer: ").strip()
        student_answer=sys.stdin.readline().strip()
        result = await agent.run(student_answer, session=session)

async def run_ingestion(spec_path_str: str, context_path_str: str, model: str = MODEL) -> None:
    """Drives the Ingestion Agent through the specify, clarify, plan, tasks, and synthesis loop."""

    agent = build_agent(model)
    session = agent.create_session()

    spec_path = Path(spec_path_str)
    with open(spec_path, "r") as f:
        file_content = f.read()

    # --- Step 1: /speckit.specify ---
    # NOTE Flaw: this hands the model the FULL student
    # spec as the "description" for /speckit.specify, which is designed to
    # expand a short description into a spec via a template. The model may
    # paraphrase/restructure the student's text rather than preserve it
    # verbatim. If fidelity to the original wording matters, replace this
    # step with a direct write_file() call from Python instead of routing
    # it through the LLM.
    feature_name = spec_path.stem
    target_spec_path = f"specs/{feature_name}/spec.md"

    prompt = (
        f"/speckit.specify\n\n"
        f"CRITICAL INSTRUCTION: You MUST use the `write_file` tool to save the resulting "
        f"specification EXACTLY to the path '{target_spec_path}'. Do not use any other path or filename.\n\n"
        f"--- STUDENT SPECIFICATION ---\n{file_content}\n"
        "--- END STUDENT SPECIFICATION ---"
    )
    result = await agent.run(prompt, session=session)
    print("## SPECIFY PHASE")
    print(result.text)
    
    for msg in getattr(result, "messages", []):
        tool_calls = getattr(msg, "tool_calls", None) or getattr(msg, "function_calls", None)
        if tool_calls:
            print("TOOL CALLS:", tool_calls)
    
    active_spec = REPO_ROOT / target_spec_path
    if not active_spec.exists():
        print(f"ERROR: {target_spec_path} not found after /speckit.specify -- aborting.")
        return

    rel_spec_path = active_spec.relative_to(REPO_ROOT)

    # --- Step 2: /speckit.clarify (interactive) ---
    await run_clarify_loop(agent, session, spec_path=active_spec)

    # --- Step 3: /speckit.plan ---
    plan_prompt = (
        f"/speckit.plan\n\n"
        f"The active feature specification is located at: '{rel_spec_path}'\n"
        f"Use your tools and internal skills to generate the plan for this specification now. "
        f"Do not attempt to scan or browse directories; use this path directly. Do not make conversational excuses."
    )
    
    print("## PLAN PHASE")
    result = await agent.run(plan_prompt, session=session)

    print(result.text)

    if not (active_spec.parent / "plan.md").exists():
        print(f"ERROR: no plan.md found in {rel_spec_path.parent} after /speckit.plan -- aborting.")
        return

    # --- Step 4: /speckit.tasks ---
    tasks_prompt = (
        f"/speckit.tasks\n\n"
        f"The active feature specification is located at: '{rel_spec_path}'\n"
        f"Use your tools and internal skills to generate the task list for this specification now. "
        f"Rely on the provided path directly.\n\n"
        f"REMINDER -- CRITICAL FORMAT RULE: every phase heading in the tasks.md you write must be "
        f"'## Phase <N>: <Title>' with <N> a literal sequential integer (1, 2, 3, ...). Never leave "
        f"a placeholder 'N', never use a different heading level or bold text instead of a heading, "
        f"and never omit a phase's number. This will be checked automatically after you write the file."
    )
    
    print("## TASKS CREATION PHASE")
    result = await agent.run(tasks_prompt, session=session)

    print(result.text)

    # --- Step 4b: Validate tasks.md phase-header format, with bounded self-repair ---
    tasks_path = active_spec.parent / "tasks.md"
    rel_tasks_path = tasks_path.relative_to(REPO_ROOT)
    for attempt in range(1, MAX_TASKS_FORMAT_RETRIES + 1):
        if not tasks_path.exists():
            print(f"ERROR: expected tasks.md at '{rel_tasks_path}' but it was not created -- aborting.")
            return
        if PHASE_HEADER_RE.search(tasks_path.read_text()):
            break
        print(
            f"=== tasks.md at '{rel_tasks_path}' has no '## Phase N: ...' headers "
            f"(attempt {attempt}/{MAX_TASKS_FORMAT_RETRIES}) -- asking agent to fix it ==="
        )
        if attempt == MAX_TASKS_FORMAT_RETRIES:
            print(
                f"ERROR: tasks.md at '{rel_tasks_path}' still has no '## Phase N: ...' sections "
                f"after {MAX_TASKS_FORMAT_RETRIES} attempts -- aborting before handing off to the "
                f"Mentoring Agent."
            )
            return
        fix_prompt = (
            f"The tasks.md you wrote at '{rel_tasks_path}' does not contain any heading matching "
            f"the required pattern '## Phase <N>: <Title>' (regex: '^## Phase (\\d+): (.+)$', "
            f"case-sensitive, must be a level-2 heading with a literal integer). Use `read_file` to "
            f"re-read '{rel_tasks_path}', rewrite every phase heading to match this exact format "
            f"(replacing any leftover 'N' placeholder with the correct sequential integer), and use "
            f"`write_file` to save the corrected file back to '{rel_tasks_path}'. Do not change the "
            f"task content, only the phase headings."
        )
        result = await agent.run(fix_prompt, session=session)
        print("=== TASKS FORMAT FIX OUTPUT ===")
        print(result.text)

    # --- Step 5: Final Synthesis (Learning Objectives) ---
    synthesis_prompt = (
        f"FINAL SYNTHESIS\n\n"
        f"The spec-kit task generation is complete. Now, read the active specification at '{rel_spec_path}', "
        f"the generated tasks, and the academic research context located at '{context_path_str}'.\n"
        f"Using these documents, generate a list of Academic Learning Objectives. "
        f"You MUST use your `write_file` tool to save these objectives to a file called "
        f"'{active_spec.parent.relative_to(REPO_ROOT)}/learning_objectives.md'."
    )
    
    print("## SYNTHESIS PHASE")
    result = await agent.run(synthesis_prompt, session=session)
    print(result.text)

async def main():
    spec_path = os.path.join(REPO_ROOT, "assignment_brief", "spec.md")
    context_path = str(os.path.join(REPO_ROOT, "research", "context.md"))
    model = sys.argv[2] if len(sys.argv) > 2 else MODEL
    await run_ingestion(spec_path, context_path,model)

if __name__ == "__main__":
    asyncio.run(main())