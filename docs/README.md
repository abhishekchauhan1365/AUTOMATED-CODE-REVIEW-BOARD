# Automated Code Review Board (CSE476 — Group 14)

## Project Overview

**Automated Code Review Board** is a production-style multi-agent code review and fix-recommendation platform built with **FastAPI**, **Microsoft Semantic Kernel**, **Groq LLM**, and **React + TypeScript + Tailwind CSS**. Users submit source files or unified Git diffs; four specialist AI agents inspect the change in parallel, a **Reviewer Manager** consolidates findings into an `APPROVE` or `REQUEST_CHANGES` decision, and a **Fix-Suggestion Agent** produces a statically validated unified diff patch for the highest-severity actionable finding.

## Agent Roster & Tools

| Agent | Module | Real Python Tools Invoked (`@kernel_function`) |
| --- | --- | --- |
| **Diff Agent** | `backend/agents/diff_agent.py` | `parse_git_diff()`, `extract_modified_files()`, `analyze_code_structure()` |
| **Style Agent** | `backend/agents/style_agent.py` | `run_linter()` (Ruff + AST checks), `calculate_complexity()` (Radon + duplication) |
| **Security Agent** | `backend/agents/security_agent.py` | `scan_for_secrets()` (with redaction), `run_security_analysis()` (Bandit + AST/pattern SQLi/shell/XSS) |
| **Test-Coverage Agent** | `backend/agents/test_coverage_agent.py` | `discover_test_files()`, `analyze_test_coverage()` (static symbol mapping + optional `pytest-cov` XML/JSON) |
| **Reviewer Manager** | `backend/agents/reviewer_manager.py` | `deduplicate_findings()`, `rank_findings()`, `generate_review_report()` |
| **Fix-Suggestion Agent** | `backend/agents/fix_suggestion_agent.py` | `extract_code_context()`, `generate_unified_patch()`, `validate_patch()` |

## Architecture & Why It Fits

The system uses a **Fan-Out / Fan-In** architecture powered by Semantic Kernel's `ConcurrentOrchestration` and `InProcessRuntime` (see [`docs/architecture_diagram.png`](./architecture_diagram.png)). Code review naturally decomposes into independent concerns (diff structure, formatting/complexity, security, and test coverage) that benefit from parallel execution, followed by a central synthesis step to eliminate cross-agent duplicates and enforce consistent merge policy. Deterministic static analyzers (Ruff, Bandit, Radon, AST) provide primary evidence so the Groq LLM interprets real diagnostics rather than inventing issues.

## Shared Memory Contents (`SharedChangeState`)

Defined in `backend/orchestration/state.py`, the async-locked shared state tracks:
- `review_id`, `overall_status`, `phase`, and `execution_timestamps`
- `submission_metadata` (title, description, submission type, model, `demo_mode`)
- `files` (`SubmittedFile` list) and `git_diff`
- `agent_statuses` (pending/running/completed/failed, activity, duration, tools invoked)
- `agent_findings`, `agent_outputs`, `severity_summary`, and `consolidated_findings`
- `merge_recommendation`, `fix_suggestion`, and `events` (streamed over SSE/WebSocket and appended to `backend/logs/review_runs.jsonl`)

## Failure Scenario Handled

If an individual specialist agent encounters a runtime error, API timeout, rate limit, or invalid JSON response, `SharedChangeState.mark_agent_failed()` records the exact error and prevents that agent from being marked successful, while the remaining parallel agents continue executing. In particular, if the **Security Agent** fails, the **Reviewer Manager** explicitly notes `"Incomplete checks: Security Agent failed"` and enforces `REQUEST_CHANGES` rather than falsely approving unverified code. When `GROQ_API_KEY` is absent or `USE_MOCK_LLM=true`, `MockGroqChatCompletion` executes the full Semantic Kernel pipeline deterministically in Demo Mode.

## Installation & Execution

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Optionally set GROQ_API_KEY; works out-of-the-box in Demo Mode
uvicorn main:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

### 3. Tests & Demo Notebook
```bash
cd backend
pytest tests -v
jupyter notebook ../automated_code_review_demo.ipynb
```

