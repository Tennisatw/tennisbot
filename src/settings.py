import json


class Settings:
    """Global app settings loaded from data/setting.json."""

    def __init__(
        self,
        *,
        name: str,
        lang: str,
        default_max_turns: int,
        default_ignore: list[str],
    ):
        self.name = name
        self.lang = lang
        self.default_max_turns = default_max_turns
        self.default_ignore = default_ignore


def load_settings(path: str = "data/setting.json") -> Settings:
    """Load settings from json file."""

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Settings(
        name=data.get("name", "Tennisbot"),
        lang=data.get("lang", "zh-CN"),
        default_max_turns=data.get("default_max_turns", 20),
        default_ignore=data.get("default_ignore", []),
    )


settings = load_settings()
