import json


class Settings:
    """Global app settings loaded from data/setting.json."""

    def __init__(
        self,
        *,
        name: str = "Tennisbot",
        lang: str = "zh-CN",
        default_model: str = "gpt-5-mini",
        default_temperature: float = 0.5,
        default_max_tokens: int = 2048,
        default_max_turns: int = 20,
        default_ignore: list[str] | None = None,
    ):
        self.name = name
        self.lang = lang
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
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
        default_model=data.get("default_model", "gpt-5-mini"),
        default_temperature=data.get("default_temperature", 0.5),
        default_max_tokens=data.get("default_max_tokens", 2048),
        default_max_turns=data.get("default_max_turns", 20),
        default_ignore=data.get("default_ignore"),
    )


settings = load_settings()
