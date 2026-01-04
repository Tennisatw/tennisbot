import time
import logging
import contextvars
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

current_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_session_id", default=None
)


def _normalize_value(v, *, max_len: int | None = 100):
    """Normalize log field values.

    - Replace newlines with literal "\\n".
    - Optionally truncate long strings.
    """

    if isinstance(v, str):
        v = v.replace("\r\n", "\\n").replace("\n", "\\n")
        if max_len is not None and len(v) > max_len:
            v = v[:max_len] + "..."
        return v
    else:
        return _normalize_value(str(v))


def logged_tool(fn):
    """Decorator to auto-log tool input/output.

    Logs:
        - tool.<name>.input: args/kwargs
        - tool.<name>.output: success/elapsed_ms + output preview or error
    """

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        name = getattr(fn, "__name__", "tool")

        parts = [f"tool.{name}.input"]
        for i, arg in enumerate(args):
            parts.append(f"arg{i}={_normalize_value(arg)}")
        for k, v in kwargs.items():
            parts.append(f"{k}={_normalize_value(v)}")
        logger.log(" ".join(parts))

        logger.emit({"type": "tool_call", "name": name, "phase": "start"})

        try:
            output = await fn(*args, **kwargs)
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            logger.emit({"type": "tool_call", "name": name, "phase": "error"})
            raise

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        msgs = [f"tool.{name}.output", f"elapsed_ms={elapsed_ms}", "output:"]
        if isinstance(output, dict):
            for k, v in output.items():
                msgs.append(f"{k}={_normalize_value(v)}")
        elif isinstance(output, str):
            msgs.append(f"{_normalize_value(output)}")
        logger.log(" ".join(msgs))

        success = bool(output["success"]) if isinstance(output, dict) else False
        logger.emit({"type": "tool_call", "name": name, "phase": "end", "success": success})
        return output

    return wrapper


@dataclass()
class Logger:
    """App logger wrapper.

    Notes:
        - Use `setup()` once at startup.
        - Use `log` for structured events.
    """

    name: str = "default"
    today: str = ""

    def setup(self) -> logging.Logger:
        """Configure logging to console and logs/YYYY-MM-DD.log."""

        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = log_dir / f"{today}.log"

        fmt = "%(asctime)s | %(message)s "
        formatter = logging.Formatter(fmt)

        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)

        for h in list(logger.handlers):
            try:
                h.close()
            finally:
                logger.removeHandler(h)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)

        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        # logger.addHandler(console_handler)

        object.__setattr__(self, "today", today)
        return logger

    def _ensure_today_file(self) -> None:
        """Re-setup logger if date changed."""

        today = datetime.now().strftime("%Y-%m-%d")
        if self.today == today:
            return
        self.setup()

    def log(self, message: str) -> None:
        """Log a message."""
        self._ensure_today_file()
        logging.getLogger(self.name).info(message)
        print(message if len(message) < 80 else message[:77] + "...")

    def emit(self, payload: dict[str, Any]) -> None:
        """Emit a structured event.

        Notes:
            - Default behavior is to log it as a single line.
            - Web backends may monkey-patch this method to forward events.
        """

        sid = current_session_id.get()
        if isinstance(sid, str) and sid.isdigit() and "session_id" not in payload:
            payload = {**payload, "session_id": sid}

        self.log(f"event {payload}")


logger = Logger()
