## 📘 Developer Appendix

**Understanding the Agentic AI Backend (LangGraph + Persistence)**

### 1. Purpose of This Appendix

This appendix is a **deep technical companion** to the main README.

The README explains what the system does and why it is interesting.
This document explains **how it actually works under the hood** and **why specific architectural decisions were made.**

This guide is written for:
- My future self (to re-understand the system months later)
- Engineers learning LangGraph and agentic workflows
- Reviewers or interviewers evaluating system design choices

The goal is not just to describe the code, but to explain the mental model required to reason about stateful, resumable AI workflows.

### 2. Mental Model: How the System Actually Runs

Before looking at files, functions, or LangGraph APIs, it’s important to understand **how to think about this system.**

### 2.1 This is NOT a request → response system

A traditional LLM app looks like this:

User Request → Prompt → LLM → Response → Done

That model breaks down when you need:
- Multiple agents
- Parallel work
- Human review in the middle
- Long-running workflows
- Resume after interruption

This project instead treats AI execution as a process, not a single call.

### 2.2 Think in terms of a “workflow instance”

Every time a user clicks Generate Report, the system creates:
- One workflow instance
- Identified by a **thread_id**
- With a single evolving state object

You should mentally picture it like this:

#### Workflow instance diagram
```
Workflow Instance
├── thread_id = "user123-abc123"
├── State (changes over time)
├── Execution pointer (which node is next)
└── Checkpoints (saved to disk)
```
This workflow instance may:
- Run for seconds or minutes
- Pause and wait for human input
- Resume later
- Survive backend restarts

### 2.3 State is the heart of everything

In this system:
**Nothing important lives in local variables.**

Everything that matters lives in **shared workflow state.**

State answers questions like:
- What is the research topic?
- Which analysts exist?
- How many interviews are expected?
- How many interviews are complete?
- What sections have been written so far?
- Has human feedback been provided?

LangGraph enforces this discipline by design:
- Nodes receive state
- Nodes return state updates
- State is checkpointed automatically

If you understand the state, you understand the system.

### 2.4 Nodes are steps, not functions

A common beginner mistake is to think:
> “A node is just a function call.”

A better mental model:
**A node is a step in a long-running process.**

Each node:
- Receives the current state
- Performs one logical unit of work
- Returns updates to the shared state
- Does not control what runs next

The **graph,** not the node, controls flow.

### 2.5 The graph is the real “program”

Instead of writing control flow like this:
```python
do_a()
if condition:
    do_b()
else:
    do_c()
```

You declare flow like this:

Node A ──▶ Node B ──▶ Node C
          │
          └────▶ Node D

This is important because:
- Execution order is explicit
- Parallelism is possible
- Pausing/resuming is natural
- State transitions are inspectable

The graph **is the program.**

### 2.6 Fan-out and fan-in are first-class concepts
One of the most important ideas in this project is **parallel execution.**

Mentally, think:

Prepare Interviews
│
├── Interview Analyst A
├── Interview Analyst B
├── Interview Analyst C
│
Gather Results

Key points:
- Each interview runs independently
- Each interview updates shared state
- The system must know when all interviews are done
- The graph must not continue early or loop forever

This is why counters like:
- expected_interviews
- completed_interviews
exist in the state.

### 2.7 Pausing is intentional, not an error

A major conceptual shift:
**Pausing execution is a feature, not a failure.**

When the workflow pauses:
- State is fully valid
- Execution pointer is known
- Nothing is “half-done”

The pause simply means:
> “We are waiting for an external signal (human feedback).”

This is what enables:
- Human-in-the-loop
- Resume across HTTP requests
- Resume after server restarts

### 2.8 Persistence changes how you design everything

Because state is persisted:
- You cannot rely on in-memory objects
- You must assume the process may restart
- You must treat state as the single source of truth

This pushes the design closer to:
- Workflow engines
- Durable task systems
- Orchestration frameworks

… and away from:
- Scripts
- Linear chains
- Request-scoped logic

### 3. Summary: The Mental Checklist
When reasoning about this system, always ask:
- What does the state look like right now?
- Which node is about to run?
- What state updates will this node produce?
- Should execution continue, branch, pause, or end?
- If the server restarted now, could this resume safely?
- If you can answer those questions, you understand the system.