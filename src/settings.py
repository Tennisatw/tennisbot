import json


class Settings:
    """Global app settings loaded from data/setting.json."""

    def __init__(
        self,
        *,
        name: str = "Tennisbot",
        lang: str = "zh-CN",
        default_max_turns: int = 20,
        default_ignore: list[str] | None = None,
    ):
        self.name = name
        self.lang = lang
        self.default_max_turns = default_max_turns
        self.default_ignore = default_ignore or [
            ".git",
            "__pycache__",
            ".venv",
            "logs",
            "session.db",
        ]


def load_settings(path: str = "data/setting.json") -> Settings:
    """Load settings from json file."""

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Settings(
        name=data.get("name", "Tennisbot"),
        lang=data.get("lang", "zh-CN"),
        default_max_turns=data.get("default_max_turns", 20),
        default_ignore=data.get("default_ignore"),
    )


settings = load_settings()
