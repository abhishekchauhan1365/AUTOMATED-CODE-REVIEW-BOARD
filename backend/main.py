"""FastAPI entrypoint for Automated Code Review Board."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

from orchestration.schemas import (
    FixSuggestion,
    ReviewCreateRequest,
    ReviewDetailResponse,
    ReviewStatusResponse,
    ReviewSummaryItem,
)
from pydantic import BaseModel, Field
from services.file_service import FileValidationError, MAX_FILE_SIZE_BYTES, MAX_UPLOAD_FILES
from services.llm_service import is_demo_mode_enabled
from services.review_service import (
    approve_patch,
    fetch_stats,
    get_active_state,
    get_detail,
    get_logs,
    get_patch,
    get_status,
    initialize_storage,
    list_history,
    remove_review,
    start_review,
)

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_storage()
    yield


app = FastAPI(
    title="Automated Code Review Board API",
    description="Multi-agent AI code review & fix recommendation platform (CSE476 Group 14).",
    version="1.0.0",
    lifespan=lifespan,
)

raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication Schemas
class LoginRequest(BaseModel):
    username: str = Field(..., description="Email address or username")
    password: str = Field(..., description="User password")


class UserProfile(BaseModel):
    id: str
    username: str
    name: str
    email: str
    role: str
    avatar_url: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: UserProfile


# In-memory session store
_ACTIVE_SESSIONS: dict[str, UserProfile] = {}

PRECONFIGURED_USERS = {
    "demo": {
        "password": "demo123",
        "name": "Demo Reviewer",
        "role": "Review Engineer",
        "email": "demo@cse476.edu",
    },
    "admin": {
        "password": "admin",
        "name": "Review Board Admin",
        "role": "Lead Architect",
        "email": "admin@cse476.edu",
    },
    "reviewer@cse476.edu": {
        "password": "review123",
        "name": "Dr. Sarah Chen",
        "role": "Lead Review Architect",
        "email": "reviewer@cse476.edu",
    },
    "developer@cse476.edu": {
        "password": "dev123",
        "name": "Alex Rivera",
        "role": "Senior Software Engineer",
        "email": "developer@cse476.edu",
    },
}


_FAILED_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 30


def check_rate_limit(key: str) -> None:
    """Safety net: enforce temporary account lockout after multiple consecutive failed attempts."""
    import time
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(key, [])
    valid = [t for t in attempts if now - t < 60]
    _FAILED_LOGIN_ATTEMPTS[key] = valid
    if len(valid) >= MAX_LOGIN_ATTEMPTS:
        elapsed = now - valid[-MAX_LOGIN_ATTEMPTS]
        remaining = int(LOCKOUT_SECONDS - elapsed)
        if remaining > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Safety Lockout: Too many failed login attempts. Please wait {remaining} seconds.",
            )


def record_failed_attempt(key: str) -> None:
    import time
    _FAILED_LOGIN_ATTEMPTS.setdefault(key, []).append(time.time())


def clear_failed_attempts(key: str) -> None:
    _FAILED_LOGIN_ATTEMPTS.pop(key, None)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request) -> AuthResponse:
    """Simple developer authentication endpoint supporting demo and custom accounts with safety rate-limiting."""
    u_raw = payload.username.strip()
    p_raw = payload.password.strip()

    # Safety Net 1: Length and control character sanitization
    if not u_raw or not p_raw:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    if len(u_raw) > 128 or len(p_raw) > 128:
        raise HTTPException(status_code=400, detail="Input exceeded maximum character limit (128).")
    if any(ord(c) < 32 for c in u_raw + p_raw):
        raise HTTPException(status_code=400, detail="Invalid control characters detected in credentials.")

    client_ip = request.client.host if request.client else "local"
    rate_key = f"{client_ip}:{u_raw.lower()}"
    check_rate_limit(rate_key)

    u_lower = u_raw.lower()
    if u_lower in PRECONFIGURED_USERS:
        conf = PRECONFIGURED_USERS[u_lower]
        if payload.password != conf["password"]:
            record_failed_attempt(rate_key)
            raise HTTPException(status_code=401, detail="Invalid credentials for demo account.")
        user = UserProfile(
            id=f"user_{u_lower.split('@')[0]}",
            username=u_lower,
            name=conf["name"],
            email=conf["email"],
            role=conf["role"],
        )
    else:
        # Flexible login for any student or reviewer
        clean_user = u_raw
        user = UserProfile(
            id=f"user_{clean_user.replace('@', '_').replace('.', '_')[:16]}",
            username=clean_user,
            name=clean_user.split("@")[0].replace(".", " ").title(),
            email=clean_user if "@" in clean_user else f"{clean_user}@cse476.local",
            role="Code Reviewer",
        )

    clear_failed_attempts(rate_key)
    import uuid
    token = f"crb_tok_{uuid.uuid4().hex}"
    _ACTIVE_SESSIONS[token] = user
    return AuthResponse(token=token, user=user)


@app.get("/api/auth/me", response_model=UserProfile)
def get_current_user(request: Request) -> UserProfile:
    """Return currently authenticated user profile or demo guest profile."""
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None
    if token and token in _ACTIVE_SESSIONS:
        return _ACTIVE_SESSIONS[token]

    # Return default guest/demo reviewer if not signed in
    return UserProfile(
        id="user_guest_reviewer",
        username="guest_reviewer",
        name="Guest Code Reviewer",
        email="guest@cse476.local",
        role="Guest Reviewer",
    )


@app.post("/api/auth/logout")
def logout(request: Request) -> dict[str, bool]:
    """Invalidate session token."""
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None
    if token and token in _ACTIVE_SESSIONS:
        _ACTIVE_SESSIONS.pop(token, None)
    return {"success": True}


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    """Health and LLM runtime mode check."""
    return {
        "status": "ok",
        "demo_mode_default": is_demo_mode_enabled(None),
        "framework": "semantic-kernel",
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    }


@app.get("/api/stats")
def get_stats() -> dict[str, Any]:
    """Return real aggregated dashboard statistics from SQLite."""
    return fetch_stats()


@app.post("/api/reviews", response_model=ReviewDetailResponse, status_code=202)
async def create_review(request: Request) -> ReviewDetailResponse:
    """Start a new multi-agent code review from JSON (files/diff) or multipart form upload."""
    content_type = request.headers.get("content-type", "")

    try:
        if "multipart/form-data" in content_type:
            form = await request.form()
            title = str(form.get("title") or "") or None
            description = str(form.get("description") or "")
            demo_raw = form.get("demo_mode")
            demo_mode: Optional[bool] = None
            if isinstance(demo_raw, str) and demo_raw.lower() in ("true", "false"):
                demo_mode = demo_raw.lower() == "true"

            uploaded = form.getlist("files")
            if len(uploaded) > MAX_UPLOAD_FILES:
                raise FileValidationError(f"Too many uploaded files (max {MAX_UPLOAD_FILES}).")

            raw_files: list[dict[str, Any]] = []
            for item in uploaded:
                if hasattr(item, "read"):
                    raw_bytes = await item.read()
                    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
                        raise FileValidationError(
                            f"Uploaded file '{getattr(item, 'filename', 'unknown')}' exceeds size limit."
                        )
                    try:
                        text = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise FileValidationError(
                            f"File '{getattr(item, 'filename', 'unknown')}' must be valid UTF-8 text."
                        ) from exc
                    raw_files.append(
                        {
                            "path": getattr(item, "filename", "uploaded.py"),
                            "content": text,
                            "status": "modified",
                        }
                    )

            return await start_review(
                title=title,
                description=description,
                submission_type="files",
                raw_files=raw_files,
                demo_mode=demo_mode,
                run_async=True,
            )

        body = await request.json()
        payload = ReviewCreateRequest.model_validate(body)
        return await start_review(
            title=payload.title,
            description=payload.description,
            submission_type=payload.submission_type,
            git_diff=payload.git_diff,
            raw_files=payload.files,
            demo_mode=payload.demo_mode,
            run_async=True,
        )

    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/reviews", response_model=list[ReviewSummaryItem])
def get_review_history() -> list[ReviewSummaryItem]:
    """Return persisted review history ordered newest first."""
    return list_history()


@app.get("/api/reviews/{review_id}", response_model=ReviewDetailResponse)
def get_review(review_id: str) -> ReviewDetailResponse:
    """Return complete review results."""
    detail = get_detail(review_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")
    return detail


@app.get("/api/reviews/{review_id}/status", response_model=ReviewStatusResponse)
def get_review_status(review_id: str) -> ReviewStatusResponse:
    """Return live execution status for all six agents."""
    status = get_status(review_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")
    return status


@app.get("/api/reviews/{review_id}/findings")
def get_review_findings(
    review_id: str,
    severity: Optional[str] = Query(default=None),
    agent: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Return consolidated findings with optional severity and agent filtering."""
    detail = get_detail(review_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")

    findings = detail.consolidated_findings
    if severity:
        sev_upper = severity.upper()
        findings = [f for f in findings if f.severity.value == sev_upper]
    if agent:
        agent_lower = agent.lower()
        findings = [
            f
            for f in findings
            if f.agent.lower() == agent_lower or agent_lower in [c.lower() for c in f.corroborated_by]
        ]

    return {
        "review_id": review_id,
        "total": len(findings),
        "severity_summary": detail.severity_summary,
        "findings": findings,
    }


@app.get("/api/reviews/{review_id}/patch", response_model=FixSuggestion)
def get_review_patch(review_id: str) -> FixSuggestion:
    """Return the Fix-Suggestion Agent's proposed patch."""
    patch = get_patch(review_id)
    if patch is None:
        detail = get_detail(review_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")
        return FixSuggestion(available=False, explanation="Fix-Suggestion Agent has not completed yet.")
    return patch


@app.post("/api/reviews/{review_id}/patch/approve", response_model=FixSuggestion)
def approve_review_fix_patch(review_id: str) -> FixSuggestion:
    """Explicitly approve a proposed patch before allowing download."""
    patch = approve_patch(review_id)
    if patch is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' or patch not found.")
    return patch


@app.get("/api/reviews/{review_id}/patch/download")
def download_review_patch(review_id: str) -> PlainTextResponse:
    """Download the unified diff patch ONLY after explicit user approval."""
    patch = get_patch(review_id)
    if patch is None or not patch.available:
        raise HTTPException(status_code=404, detail="No available patch found for this review.")
    if not patch.user_approved:
        raise HTTPException(
            status_code=403,
            detail="Explicit user approval is required before downloading or applying this patch.",
        )

    return PlainTextResponse(
        content=patch.proposed_patch,
        media_type="text/x-diff",
        headers={"Content-Disposition": f'attachment; filename="fix_{review_id[:8]}.patch"'},
    )


@app.get("/api/reviews/{review_id}/logs")
def get_review_logs(review_id: str) -> dict[str, Any]:
    """Return append-only JSONL execution trace for this review."""
    detail = get_detail(review_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")
    return {"review_id": review_id, "events": get_logs(review_id)}


@app.get("/api/reviews/{review_id}/events")
async def stream_review_events(review_id: str) -> StreamingResponse:
    """Server-Sent Events (SSE) stream emitting live agent progress updates."""
    status = get_status(review_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")

    async def event_generator():
        initial_payload = {"type": "status_update", "status": status.model_dump()}
        yield f"data: {json.dumps(initial_payload)}\n\n"

        if status.overall_status in ("completed", "failed"):
            yield f"data: {json.dumps({'type': 'workflow_done', 'status': status.model_dump()})}\n\n"
            return

        active = get_active_state(review_id)
        if active is None:
            return

        queue = active.subscribe()
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(msg)}\n\n"
                    if msg.get("type") == "workflow_done":
                        break
                except asyncio.TimeoutError:
                    current = get_status(review_id)
                    if current and current.overall_status in ("completed", "failed"):
                        yield f"data: {json.dumps({'type': 'workflow_done', 'status': current.model_dump()})}\n\n"
                        break
                    yield ": keepalive\n\n"
        finally:
            active.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.websocket("/ws/reviews/{review_id}")
async def websocket_review_events(websocket: WebSocket, review_id: str) -> None:
    """WebSocket alternative for real-time agent execution progress."""
    await websocket.accept()
    status = get_status(review_id)
    if status is None:
        await websocket.send_json({"type": "error", "detail": "Review not found"})
        await websocket.close()
        return

    await websocket.send_json({"type": "status_update", "status": status.model_dump()})
    if status.overall_status in ("completed", "failed"):
        await websocket.send_json({"type": "workflow_done", "status": status.model_dump()})
        await websocket.close()
        return

    active = get_active_state(review_id)
    if active is None:
        await websocket.close()
        return

    queue = active.subscribe()
    try:
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
            if msg.get("type") == "workflow_done":
                break
    except WebSocketDisconnect:
        pass
    finally:
        active.unsubscribe(queue)


@app.delete("/api/reviews/{review_id}")
def delete_review_record(review_id: str) -> dict[str, Any]:
    """Delete a persisted review record."""
    deleted = remove_review(review_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")
    return {"deleted": True, "review_id": review_id}

