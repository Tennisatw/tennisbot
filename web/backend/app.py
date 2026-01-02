import asyncio
import json
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Tennisbot Web UI")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    """WebSocket placeholder.

    MVP behavior:
    - Accept JSON messages.
    - If message type is `user_message`, reply with an `ack`.
    - Otherwise, echo back an `error`.
    """

    await ws.accept()
    lock = asyncio.Lock()

    async def send(payload: dict[str, Any]) -> None:
        async with lock:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))

    while True:
        try:
            raw = await ws.receive_text()
        except Exception:
            return

        try:
            msg = json.loads(raw)
        except Exception:
            await send({"type": "error", "message": "invalid_json"})
            continue

        if not isinstance(msg, dict):
            await send({"type": "error", "message": "invalid_message"})
            continue

        msg_type = msg.get("type")
        if msg_type != "user_message":
            await send({"type": "error", "message": "unsupported_type"})
            continue

        message_id = msg.get("message_id")
        await send({"type": "ack", "message_id": message_id, "queue_pos": 0})
