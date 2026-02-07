## Table of Contents
1. [What This Project Does](#what-this-project-does)
2. [Why This Project Is Interesting](#why-this-project-is-interesting)
3. [Project Origins & Personal Extensions](#project-origins--personal-extensions)
4. [High-Level Architecture](#high-level-architecture)
5. [Beginner-Friendly Explanation (With Analogies)](#beginner-friendly-explanation-with-analogies)
6. [End-to-End Application Flow](#end-to-end-application-flow)
7. [Agentic AI Backend (LangGraph)](#agentic-ai-backend-langgraph)
8. [Human-in-the-Loop & Resume Capability](#human-in-the-loop--resume-capability)
9. [Persistent Checkpointing](#persistent-checkpointing)
10. [Outputs](#outputs)
11. [Tech Stack](#tech-stack)
12. [Who This Repo Is For](#who-this-repo-is-for)
13. [Next Steps & Future Improvements](#next-steps--future-improvements)


## What This Project Does
This application generates long-form research reports by orchestrating multiple AI agents
that collaborate on a topic, conduct research, synthesize findings, and produce a final
written report.

Instead of a single prompt → single answer workflow, this system:

- Creates multiple AI “analysts”
- Allows human feedback mid-execution
- Runs interviews in parallel
- Aggregates results safely
- Produces downloadable DOCX and PDF reports

## Why This Project Is Interesting
Most AI demos are stateless and one-shot.

I have been using this project to explore what production-grade agentic AI
systems look like beyond simple chains, and to incrementally evolve an
educational starting point into a more realistic system design.

- Long-running workflows
- Explicit state modeling
- Pause / resume behavior
- Human-in-the-loop decision points
- Durable persistence across requests

This mirrors real enterprise AI use cases much more closely than simple chatbot pipelines.

## Project Origins & Personal Extensions

This project originally started as part of an AI bootcamp I completed in 2025.
The core idea and initial scaffolding in the `main` branch are based on that
bootcamp curriculum.

I have been actively refactoring and extending the project to make it more production-oriented and aligned with real-world agentic AI systems. Examples of my own contributions include:

- Refactoring error handling and logging (e.g., using `log.exception` for
  structured error reporting)
- Introducing a persistent LangGraph checkpointer backed by SQLite to support
  pause/resume workflows
- Restructuring workflows to better separate orchestration, state, and tooling
- Improving code readability, maintainability, and documentation

This repository is intentionally a **living project**. My goal is to continue
iterating on it by adding evaluation, guardrails, observability, and other
production-grade features over time.

## High-Level Architecture
At a high level, the system has four layers:

Browser (HTML Forms)
↓
FastAPI Backend
↓
LangGraph Agentic Workflow
↓
SQLite Persistent Checkpoints

- The frontend collects user input and feedback
- The backend manages sessions and workflow execution
- **LangGraph** orchestrates the agentic workflow
- **SQLite** stores workflow state so execution can resume later

## Beginner-Friendly Explanation (With Analogies)
Think of this system as a research manager running a small research team.

### 1️⃣ Hire analysts
The system creates several AI analysts, each with a different perspective.
- “You focus on technical details.”
- “You focus on business impact.”
- “You focus on risks and limitations.”

### 2️⃣ Pause for human guidance
Before research begins, the manager pauses and asks:
- “Do you want to adjust direction or add guidance?”

This is where **human-in-the-loop** happens.

### 3️⃣ Run interviews in parallel
Each analyst independently:
- Asks questions
- Searches the web
- Writes findings

All analysts work **at the same time,** not sequentially.

### 4️⃣ Synthesize and write
Once all analysts finish:
- Their findings are gathered
- A writer agent synthesizes the content
- A final report is produced

## End-to-End Application Flow
1. User logs in
1. User submits a research topic
1. Backend initializes the agentic workflow
1. Workflow pauses before human feedback
1. User submits feedback
1. Workflow resumes from saved state
1. Interviews run in parallel
1. Results are aggregated
1. Final report is generated and saved
1. User downloads the report

## Agentic AI Backend (LangGraph)
Unlike linear chains, this graph-based design makes parallelism, branching,
and resumability first-class concerns.

Key concepts:
- **Nodes** → individual steps (create analysts, interview, write report)
- **Edges** → transitions between steps
- **State** → shared memory across all steps
- **Fan-out / Fan-in** → parallel interviews with safe aggregation

This structure enables:
- Parallel execution
- Conditional branching
- Pause and resume behavior

## Human-in-the-Loop & Resume Capability
The workflow is intentionally designed to **pause before interviews begin.**

At that point:
- State is checkpointed
- Execution stops
- The user can submit feedback

When feedback is submitted:
- The workflow resumes from the exact pause point
- No work is repeated
- Execution continues seamlessly

This pattern is critical for real-world AI systems where humans must review or guide AI behavior.

## Persistent Checkpointing
Workflow state is persisted using a SQLite-based LangGraph checkpointer.

Why this matters:
- State survives backend restarts
- Workflows can be resumed later
- Execution is not tied to in-memory objects

Each workflow run is identified by a thread ID, allowing LangGraph to reload the correct state when resuming.

⚠️ Note: Session-to-thread mapping is currently in memory and would be persisted
(e.g., Redis or a database) in a production deployment.

## Outputs
The final research report is saved as:
- 📄 DOCX
- 📕 PDF

Files are stored on disk and made available for download through the web interface.

## Tech Stack
- **Backend:** FastAPI
- **Agentic AI:** LangGraph, LangChain
- **LLMs:** OpenAI / Groq (pluggable)
- **Persistence:** SQLite checkpointer
- **Frontend:** HTML + Jinja templates
- **Document Generation:** python-docx, reportlab

## Who This Repo Is For
- Engineers learning agentic AI systems
- Developers exploring LangGraph
- Anyone interested in stateful AI workflows
- Recruiters evaluating real-world AI design skills

## Next Steps & Future Improvements
- Persist session → thread mapping in a database
- Add progress indicators to the UI
- Make interview workflows independently resumable
- Improve observability and tracing
- Package and deploy with Docker

