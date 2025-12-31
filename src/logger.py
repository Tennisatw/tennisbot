import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def _normalize_value(v):
    """Normalize log field values.

    - Replace newlines with literal "\\n".
    - Truncate long strings to 50 chars.
    """

    if isinstance(v, str):
        if len(v) > 50:
            v = v[:50]
        v = v.replace("\r\n", "\\n").replace("\n", "\\n")
        return v
    return v


@dataclass(frozen=True)
class Logger:
    """App logger wrapper.

    Notes:
        - Use `setup()` once at startup.
        - Use `log` for structured events.
    """

    name: str = "tennisbot"

    def setup(self) -> logging.Logger:
        """Configure logging to console and logs/YYYY-MM-DD.log."""

        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

        fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s | %(agent)s"
        formatter = logging.Formatter(fmt)

        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.addFilter(_DefaultExtraFilter())
        return logger

    def log(self, event: str, *, agent: str | None = None, **fields) -> None:
        """Log a structured event."""

        extra = {"agent": agent or "-"}
        for k, v in fields.items():
            extra[k] = _normalize_value(v)
        logging.getLogger(self.name).info(event, extra=extra)


class _DefaultExtraFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "agent"):
            record.agent = "-"
        return True


logger = Logger()
