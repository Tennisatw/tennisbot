from dataclasses import dataclass
import json

@dataclass
class Settings:
    """Global app settings loaded from data/setting.json."""
    name: str
    lang: str
    default_max_turns: int
    default_ignore: list[str]
    default_prompt: str


def load_settings(path: str = "data/setting.json") -> Settings:
    """Load settings from json file."""

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Settings(
        name=data.get("name", "Tennisbot"),
        lang=data.get("lang", "zh-CN"),
        default_max_turns=data.get("default_max_turns", 20),
        default_ignore=data.get("default_ignore", []),
        default_prompt=data.get("default_prompt", ""),
    )


settings = load_settings()
