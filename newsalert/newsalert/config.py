"""Load and validate settings.yaml, sources.yaml, watchlist.yaml and .env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Category = Literal["celebrity", "anime", "manga", "tv"]
Trust = Literal["official", "major", "signal"]
SourceType = Literal["rss", "youtube", "bluesky", "x", "wikipedia"]

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


class ConfigError(RuntimeError):
    pass


def project_root() -> Path:
    return Path(os.environ.get("NEWSALERT_HOME") or _PACKAGE_ROOT)


def default_config_dir() -> Path:
    return Path(os.environ.get("NEWSALERT_CONFIG") or project_root() / "config")


# --------------------------------------------------------------------------- settings


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PollingSettings(_Strict):
    default_interval: int = 60
    min_interval: int = 30
    request_timeout: float = 10.0
    max_backoff: int = 900
    max_retry_after: int = 3600
    startup_stagger: int = 30
    user_agent: str = "newsalert/0.1 (personal breaking-news alerts; low-frequency polling)"


class PipelineSettings(_Strict):
    stale_minutes: int = 30
    text_dedupe_hours: int = 72


class Settings(_Strict):
    db_path: str = "data/newsalert.db"
    log_file: str | None = "data/newsalert.log"
    log_level: str = "INFO"
    polling: PollingSettings = Field(default_factory=PollingSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)


# --------------------------------------------------------------------------- sources


class Source(_Strict):
    name: str
    type: SourceType
    url: str | None = None
    account: str | None = None
    category: Category
    trust: Trust
    group: str | None = None
    interval: int | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def _check_access(self) -> "Source":
        if self.type in ("rss", "youtube") and not self.url:
            raise ValueError(f"source {self.name!r}: type {self.type} needs a url")
        if self.type in ("bluesky", "x") and not self.account:
            raise ValueError(f"source {self.name!r}: type {self.type} needs an account")
        return self

    @property
    def independence_group(self) -> str:
        return self.group or self.name

    def effective_interval(self, polling: PollingSettings) -> int:
        return max(self.interval or polling.default_interval, polling.min_interval)


# --------------------------------------------------------------------------- watchlist


class WatchlistEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    kind: Literal["series", "person", "studio"]
    category: Category
    roles: list[str] = Field(default_factory=list)
    works: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    wikipedia: str | None = None
    match_risk: bool = False

    @property
    def all_names(self) -> list[str]:
        return [self.name, *self.aliases]


class Watchlist(BaseModel):
    entries: list[WatchlistEntry] = Field(default_factory=list)


# --------------------------------------------------------------------------- app config


class AppConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Path
    config_dir: Path
    settings: Settings
    sources: list[Source]
    watchlist: Watchlist

    def resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.root / p

    @property
    def enabled_sources(self) -> list[Source]:
        return [s for s in self.sources if s.enabled]


def _read_yaml(path: Path):
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc


def _fmt_validation(path: Path, exc: ValidationError) -> str:
    lines = [f"{path}: invalid config"]
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"  {loc}: {err['msg']}")
    return "\n".join(lines)


def load_config(config_dir: Path | None = None) -> AppConfig:
    root = project_root()
    load_dotenv(root / ".env", override=False)
    cfg_dir = Path(config_dir) if config_dir else default_config_dir()

    settings_path = cfg_dir / "settings.yaml"
    try:
        settings = Settings.model_validate(_read_yaml(settings_path) or {})
    except ValidationError as exc:
        raise ConfigError(_fmt_validation(settings_path, exc)) from exc

    sources_path = cfg_dir / "sources.yaml"
    raw_sources = _read_yaml(sources_path) or []
    if not isinstance(raw_sources, list):
        raise ConfigError(f"{sources_path}: expected a list of sources")
    sources: list[Source] = []
    for idx, raw in enumerate(raw_sources):
        try:
            sources.append(Source.model_validate(raw))
        except ValidationError as exc:
            label = raw.get("name", f"#{idx}") if isinstance(raw, dict) else f"#{idx}"
            raise ConfigError(_fmt_validation(Path(f"{sources_path} [{label}]"), exc)) from exc
    seen: set[str] = set()
    for s in sources:
        if s.name in seen:
            raise ConfigError(f"{sources_path}: duplicate source name {s.name!r}")
        seen.add(s.name)

    watchlist_path = cfg_dir / "watchlist.yaml"
    try:
        watchlist = Watchlist.model_validate(_read_yaml(watchlist_path) or {})
    except ValidationError as exc:
        raise ConfigError(_fmt_validation(watchlist_path, exc)) from exc

    return AppConfig(
        root=root,
        config_dir=cfg_dir,
        settings=settings,
        sources=sources,
        watchlist=watchlist,
    )
