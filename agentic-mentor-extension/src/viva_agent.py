import asyncio
import json
import warnings
import os
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model_config import OLLAMA_HOST as ollama_host, MODEL as model
from config import chat_history_dir, system_prompt_file, max_questions
warnings.filterwarnings("ignore")


def load_system_prompt(path: str) -> str:
    """Load the examiner's system prompt, stripping any leading YAML frontmatter."""
    with open(path, "r", encoding="utf-8") as file:
        content = file.read()
    if content.startswith("---"):
        # Drop the frontmatter block (--- ... ---) and keep the prompt body.
        parts = content.split("---", 2)
        if len(parts) == 3:
            content = parts[2]
    return content.strip()


from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework import Agent, FileHistoryProvider


# Talk to the local Ollama server through its OpenAI-compatible endpoint, same
# as the research agent. (On current agent-framework, OpenAIChatClient targets
# the OpenAI Responses API, which Ollama doesn't serve — the chat-completions
# client is the one that works against Ollama.)
repo_root = Path(sys.argv[1])
selected_model = sys.argv[2] if len(sys.argv) > 2 else model
client = OpenAIChatCompletionClient(
    base_url=f"{ollama_host}/v1",
    model=selected_model,
    api_key="ollama",  # Ollama ignores this, but the client requires a value.
)


history_path = repo_root / chat_history_dir
os.makedirs(history_path, exist_ok=True)
file_history = FileHistoryProvider(storage_path=history_path)


# The task spec and the Mentoring Agent's end-of-session handoff summary that
# every viva question must be grounded in. Both are injected up front so
# they're always in context. Paths can be passed on the command line, e.g.:
# python viva_agent.py path/to/summary.md path/to/spec.md

summary_path = repo_root / "mentor_chat_files" / "session_summaries" / "spec__default_session.md"
with open(summary_path, "r", encoding="utf-8") as file:
    session_summary = file.read()

spec_path = repo_root / "specs" / "spec" / "spec.md"
with open(spec_path, "r", encoding="utf-8") as file:
    task_spec = file.read()

transcript_path = repo_root / chat_history_dir / "viva_transcript.md"

instructions = (
    load_system_prompt(system_prompt_file)
    + "\n\n## Original Task Specification\n\n"
    + task_spec
    + "\n\n## Session Summary You're Given\n\n"
    + session_summary
)


viva_bot = Agent(
        client=client,
        name="Viva",
        instructions=instructions,
        context_providers=[file_history],
    )


# Prompt for the single upfront call that produces the whole question set as
# structured data. Each question carries an "ideal_answer" derived from the
# summary, which later anchors the feedback so it stays reliable.
QUESTION_PROMPT = (
    "Generate the viva questions now. Based only on the task specification and "
    f"session summary in your instructions, write up to {max_questions} questions. "
    "Generate fewer if they don't support that many well-grounded questions — "
    "never pad with filler. For each question include an ideal_answer: the two "
    "or three key points a good answer would contain, derived from the spec and "
    "summary. Respond with only a JSON array, no other text, in exactly this "
    "shape:\n"
    '[{"question": "...", "ideal_answer": "..."}]'
)


# Prompt sent for each feedback turn, anchored on the pre-generated ideal answer
# rather than free-form judgement.
FEEDBACK_PROMPT = (
    "Question asked: {question}\n"
    "Key points of a good answer: {ideal_answer}\n"
    "Student's answer: {answer}\n\n"
    "Give concise, constructive feedback on the student's answer as specified in "
    "your instructions: what they got right, what they missed compared to the "
    "key points, and one nudge toward deeper understanding. No grades. "
    "Two to four sentences. Reply with feedback only — do not ask or preview "
    "the next viva question; the interview loop delivers questions itself."
)


def parse_questions(text: str) -> list:
    """Pull the JSON array of questions out of the model's reply.

    Slicing from the first '[' to the last ']' tolerates code fences or stray
    prose around the JSON.
    """
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        raise ValueError(f"No JSON array found in model output:\n{text}")
    questions = json.loads(text[start:end + 1])
    questions = [q for q in questions if q.get("question") and q.get("ideal_answer")]
    if not questions:
        raise ValueError(f"Model output contained no usable questions:\n{text}")
    return questions[:max_questions]


async def generate_questions(session) -> list:
    """Ask the agent for the full question set upfront, retrying once on bad JSON."""
    response = await viva_bot.run(QUESTION_PROMPT, session=session)
    try:
        return parse_questions(response.text)
    except (ValueError, json.JSONDecodeError):
        response = await viva_bot.run(
            "Your last reply was not valid JSON. Respond again with only the "
            "JSON array of questions, no other text.",
            session=session,
        )
        return parse_questions(response.text)


def is_dont_know(answer: str) -> bool:
    """Detect blank or 'I don't know'-style answers that shouldn't be graded."""
    normalized = answer.lower().strip().rstrip(".!?")
    return normalized in {
        "", "i don't know", "i dont know", "idk", "don't know", "dont know",
        "no idea", "not sure", "i'm not sure", "im not sure", "pass", "skip",
    }


def save_transcript(transcript, out_path=transcript_path):
    """Save the question/answer/feedback transcript for downstream use."""
    lines = ["## Viva Transcript", ""]
    for number, entry in enumerate(transcript, 1):
        lines.append(f"### Question {number}")
        lines.append(f"**Examiner:** {entry['question']}\n")
        lines.append(f"**Student:** {entry['answer'] if entry['answer'].strip() else '(no answer)'}\n")
        lines.append(f"**Feedback:** {entry['feedback']}\n")
    with open(out_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    print(f"Viva transcript saved to {out_path}")


async def main():
    sessionID = "user_john_viva_001"
    session = viva_bot.create_session(session_id=sessionID)

    print("Generating viva questions from the task spec and session summary...")
    questions = await generate_questions(session)
    print(f"Prepared {len(questions)} questions. Type 'exit' or 'quit' to end the viva early.\n")

    # Running transcript of question/answer/feedback, saved at the end.
    transcript = []
    for number, item in enumerate(questions, 1):
        time.sleep(1)
        print(f"\n**Question {number}/{len(questions)}**: {item['question']}\n")
        answer = input()
        if answer.lower().strip() in ["exit", "quit"]:
            print("Ending the viva early.")
            break

        if is_dont_know(answer):
            # Don't send a blank answer to the model — be gentle, give the key
            # point, and move on, as the system prompt promises.
            feedback = (
                "No worries — this one is tough. The key point you were "
                f"reaching for: {item['ideal_answer']} Let's move on."
            )
        else:
            response = await viva_bot.run(
                FEEDBACK_PROMPT.format(
                    question=item["question"],
                    ideal_answer=item["ideal_answer"],
                    answer=answer,
                ),
                session=session,
            )
            feedback = response.text
        print(f"**Examiner:** {feedback}\n")
        transcript.append({
            "question": item["question"],
            "answer": answer,
            "feedback": feedback,
        })

    print("The viva is over.")
    if transcript:
        save_transcript(transcript)

if __name__ == "__main__":
    asyncio.run(main())
