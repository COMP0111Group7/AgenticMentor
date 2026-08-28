from flask import Flask, render_template

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Mock data (no backend / DB yet — this stands in for what the agents
# would eventually generate from an ingested assignment spec).
# ---------------------------------------------------------------------------

RUBRIC_MATRIX = {
    "must_haves": [
        {"id": 1, "text": "Use a PostgreSQL database", "status": "pending"},
        {"id": 2, "text": "Data must persist across restarts", "status": "flagged"},
        {"id": 3, "text": "Implement RESTful API endpoints", "status": "met"},
        {"id": 4, "text": "Secure authentication (JWT)", "status": "pending"},
        {"id": 5, "text": "Input validation on all forms", "status": "pending"},
    ],
    "learning_objectives": [
        {"id": 1, "text": "Demonstrate understanding of RESTful API design", "weight": 25},
        {"id": 2, "text": "Secure authentication", "weight": 20},
        {"id": 3, "text": "Database schema design", "weight": 20},
        {"id": 4, "text": "Error handling and validation", "weight": 15},
        {"id": 5, "text": "Code organization and documentation", "weight": 20},
    ],
}

AGENT_REFERENCES = [
    {
        "title": "Python Best Practices for Web Development",
        "url": "https://docs.python.org/3/library/",
        "source": "Python Official Docs"
    },
    {
        "title": "REST API Design Guidelines",
        "url": "https://restfulapi.net/best-practices/",
        "source": "RESTful API"
    },
    {
        "title": "Database Optimization Techniques",
        "url": "https://www.postgresql.org/docs/",
        "source": "PostgreSQL Docs"
    },
    {
        "title": "Frontend Framework Comparison",
        "url": "https://developer.mozilla.org/en-US/",
        "source": "MDN Web Docs"
    },
    {
        "title": "Testing Strategies and Best Practices",
        "url": "https://testing-library.com/",
        "source": "Testing Library"
    }
]

CHAT_THREAD = [
    {
        "role": "student",
        "text": "Set up a basic express server with local memory storage for the task list.",
    },
    {
        "role": "agent",
        "text": "Wait — the assignment rubric specifies that data must persist across restarts. "
                "Your prompt relies on in-memory storage, which won't satisfy that must-have. "
                "How should we adjust this to meet the criteria?",
        "flag": "Data must persist across restarts",
    },
    {
        "role": "student",
        "text": "Good catch. Let's use PostgreSQL with a simple tasks table instead.",
    },
    {
        "role": "agent",
        "text": "That satisfies the persistence requirement and the PostgreSQL must-have. "
                "Quick concept check: why does a relational database guarantee durability "
                "that in-memory storage doesn't?",
        "concept": True,
    },
]

CHAT_HISTORY = [
    {
        "id": "c1",
        "title": "Initial build planning",
        "preview": "Set up a basic express server with local memory storage...",
        "messages": CHAT_THREAD
    },
    {
        "id": "c2",
        "title": "DB schema discussion",
        "preview": "Discussed PostgreSQL schema and relationships.",
        "messages": [
            {"role":"student", "text":"Sketch schema with users and tasks"},
            {"role":"agent", "text":"Consider foreign key constraints and ON DELETE CASCADE"}
        ]
    }
]

VIVA_QUESTIONS = [
    {
        "id": 1,
        "rubric_link": "Secure authentication (20%)",
        "question": "I see you implemented JWT tokens for the authentication requirement. "
                     "Walk me through how your code signs these tokens, and how you "
                     "prevented token tampering.",
        "answered": False,
    },
    {
        "id": 2,
        "rubric_link": "RESTful API design (25%)",
        "question": "Your /tasks endpoint handles both GET and POST. Why did you choose "
                     "those HTTP methods, and what would PUT vs PATCH mean for updates here?",
        "answered": False,
    },
    {
        "id": 3,
        "rubric_link": "Database schema design (20%)",
        "question": "Explain the relationship between your users and tasks tables. "
                     "What would happen if a user were deleted?",
        "answered": False,
    },
]

PHASES = ["upload", "build", "submit", "viva"]


@app.route("/")
def index():
    return render_template("index.html", active_phase="upload", phases=PHASES)


@app.route("/build")
def build():
    return render_template(
        "build.html",
        active_phase="build",
        phases=PHASES,
        rubric=RUBRIC_MATRIX,
        chat=CHAT_THREAD,
        references=AGENT_REFERENCES,
        chat_history=CHAT_HISTORY,
    )


@app.route("/submit")
def submit():
    return render_template(
        "submit.html",
        active_phase="submit",
        phases=PHASES,
        rubric=RUBRIC_MATRIX,
        references=AGENT_REFERENCES,
    )


@app.route("/viva")
def viva():
    return render_template(
        "viva.html",
        active_phase="viva",
        phases=PHASES,
        rubric=RUBRIC_MATRIX,
        questions=VIVA_QUESTIONS,
    )


if __name__ == "__main__":
    app.run(debug=True)
