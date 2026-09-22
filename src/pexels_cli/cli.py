"""Pexels CLI - AI-Powered Pexels Command Line Interface."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import typer
from rich.console import Console

from pexels_cli._version import __version__
from pexels_cli.config import (
    AIProvider,
    Config,
    get_config_path,
    load_config,
    save_config,
)
from pexels_cli.client import PexelsClient, PexelsClientError
from pexels_cli.formatter import OutputFormatter
from pexels_cli.ai.provider import get_ai_provider, AIProviderError
from pexels_cli.ai.smart_search import (
    build_smart_photo_params,
    build_smart_video_params,
)
from pexels_cli.ai.enhancer import enhance_prompt, curate_project
from pexels_cli.state_builder import (
    VALID_DEDUPE_MODES,
    apply_fields_filter,
    build_candidate_state_item,
    deduplicate_candidates,
)


def validate_dedupe_mode(dedupe: Optional[str]) -> Optional[str]:
    if dedupe is not None and dedupe not in VALID_DEDUPE_MODES:
        raise typer.BadParameter(
            f"Invalid dedupe mode '{dedupe}'. Choices: {', '.join(VALID_DEDUPE_MODES)}"
        )
    return dedupe


APP_HELP_TEXT = """
# ✨ Pexels CLI - Advanced AI-Powered Media Toolkit

`pexels-cli` (`px`) is a high-performance, developer-friendly Command Line Interface for searching, curating, and downloading high-resolution photos and HD/4K videos from [Pexels](https://www.pexels.com/api/).

Designed with a **Dual Interface Architecture**:
- 🎨 **For Humans**: Beautiful, interactive terminal tables, colorized syntax, and progress bars powered by `rich`.
- 🤖 **For AI Agents & Automation**: Clean, deterministic, machine-readable `--json` & `--state` JSONL output for subagents, typed-decision classifiers (Laya), shell pipelines, and `jq`.

---

## 🛠 Key Features

1. **Dedicated Photo Search & AI Smart Search**
   - Standard photo search: `px search "mountains"` (or `px photos "mountains"`)
   - AI natural language photo search: `px smart-photo "Foggy pine forest at sunrise"`
2. **Dedicated Video Search & AI Smart Video Search**
   - Standard video search: `px videos "waterfall"`
   - AI natural language video search: `px smart-video "Drone footage over ocean cliffs"`
3. **Classifier-Ready JSONL Stream (`--state` & `--fields`)**
   - Stream compact candidate objects with generated `state` strings for non-generative decision models (Laya):
     `px videos --queries "black friday,online shopping" --state --dedupe > candidates.jsonl`
   - Filter JSON fields: `px search "nature" --fields id,url,photographer --json`
4. **Multi-Provider AI Engine**
   Seamless integration with **Google Gemini**, **OpenAI**, or local **Ollama** models.
5. **High-Performance Downloader**
   Directly download media by ID or URL with streaming progress indicators.

---

## 🤖 Classifier Pipeline Example (Laya / System 1 Models)

Pipe multi-query candidate streams directly into typed-decision classification pipelines:

```bash
px videos --queries "black friday shopping,christmas online shopping,checkout cart" \\
  --per-page 8 --state --dedupe > candidates.jsonl
```

Output format per candidate (`candidates.jsonl`):
```json
{"id": 5890229, "type": "video", "query": "black friday shopping", "state": "a man shopping on black friday (photographer: Pavel Danilyuk)", "url": "https://www.pexels.com/video/.../", "duration": 10, "width": 2160, "height": 3840}
```

---

## 🔑 Environment Variables Reference

- `PEXELS_API_KEY`: Pexels API authorization token.
- `GEMINI_API_KEY`: Google Gemini API Key.
- `OPENAI_API_KEY`: OpenAI API Key.
- `OLLAMA_HOST`: Host URL for local Ollama server (default: `http://localhost:11434`).
- `PX_OUTPUT_FORMAT`: Force default output mode (`rich` or `json`).
"""

app = typer.Typer(
    name="pexels-cli",
    help=APP_HELP_TEXT,
    rich_markup_mode="markdown",
    no_args_is_help=True,
)

CONFIG_HELP_TEXT = """
Manage CLI persistent configuration, API keys, AI model selection, and default output formats.

Config file is saved at OS-standard path (`~/.config/pexels-cli/config.json`).
"""
config_app = typer.Typer(
    help=CONFIG_HELP_TEXT,
    rich_markup_mode="markdown",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")

AI_HELP_TEXT = """
AI-powered tools for natural language photo & video search, prompt enhancement, and shot-list curation.

Supports **Google Gemini** (`gemini-2.5-flash`), **OpenAI** (`gpt-4o-mini`), and **Ollama** (`llama3.2`).
"""
ai_app = typer.Typer(
    help=AI_HELP_TEXT,
    rich_markup_mode="markdown",
    no_args_is_help=True,
)
app.add_typer(ai_app, name="ai")

console = Console()


def version_callback(value: bool):
    """Callback for --version / -v flag."""
    if value:
        console.print(f"✨ [bold cyan]pexels-cli[/bold cyan] version [bold green]{__version__}[/bold green]")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show package version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Root callback for global flags."""
    pass


@app.command("version")
def version_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output version info as JSON"),
):
    """
    ℹ️ **Display detailed version and environment information.**
    """
    import sys
    cfg = load_config()
    fmt = get_formatter(json_output)
    info = {
        "name": "pexels-cli",
        "version": __version__,
        "python_version": sys.version.split()[0],
        "default_output": cfg.default_output,
        "ai_provider": cfg.ai_provider,
    }
    if fmt.json_mode:
        fmt.print_data(info)
    else:
        console.print(f"✨ [bold cyan]pexels-cli[/bold cyan] v[bold green]{__version__}[/bold green] (Python {info['python_version']})")


def get_formatter(json_flag: bool) -> OutputFormatter:
    """Helper to determine output format."""
    cfg = load_config()
    is_json = json_flag or cfg.default_output == "json"
    return OutputFormatter(json_mode=is_json)


def resolve_query_list(
    query: Optional[str],
    queries: Optional[str],
    queries_file: Optional[Path],
) -> List[str]:
    """Helper to resolve query string, comma-separated queries, or queries file into a list of queries."""
    query_list = []
    if queries_file:
        if not queries_file.exists():
            raise PexelsClientError(f"Queries file not found: {queries_file}")
        with open(queries_file, "r", encoding="utf-8") as f:
            query_list = [line.strip() for line in f if line.strip()]
    elif queries:
        query_list = [q.strip() for q in queries.split(",") if q.strip()]
    elif query:
        query_list = [query.strip()]

    if not query_list:
        raise PexelsClientError("Please specify a search query argument, --queries, or --queries-file.")
    return query_list


# ==========================================
# CONFIG COMMANDS
# ==========================================

@config_app.command("set-pexels-key")
def config_set_pexels_key(
    key: str = typer.Argument(
        ...,
        help="Your secret Pexels API Key obtained from https://www.pexels.com/api/new/",
        show_default=False,
    ),
):
    """
    🔑 **Set and persistently store your Pexels API Key.**
    """
    cfg = load_config()
    cfg.pexels_api_key = key
    save_config(cfg)
    console.print("[bold green]✓[/bold green] Pexels API Key successfully saved!")


@config_app.command("set-ai-key")
def config_set_ai_key(
    key: str = typer.Argument(
        ...,
        help="API Key for AI Provider (or host URL for Ollama e.g. http://localhost:11434)",
        show_default=False,
    ),
    provider: AIProvider = typer.Option(
        "gemini",
        "--provider",
        "-p",
        help="Select AI Provider backend: `gemini`, `openai`, or `ollama`",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override default LLM model (e.g. `gemini-2.5-flash`, `gpt-4o-mini`, `llama3.2`)",
    ),
):
    """
    🤖 **Configure AI Provider API Key and Model.**
    """
    cfg = load_config()
    cfg.ai_provider = provider
    if provider == "gemini":
        cfg.gemini_api_key = key
        if model:
            cfg.gemini_model = model
    elif provider == "openai":
        cfg.openai_api_key = key
        if model:
            cfg.openai_model = model
    elif provider == "ollama":
        cfg.ollama_host = key
        if model:
            cfg.ollama_model = model
    save_config(cfg)
    console.print(f"[bold green]✓[/bold green] AI Provider '{provider}' API configuration successfully saved!")


@config_app.command("set-output")
def config_set_output(
    format: str = typer.Argument(
        ...,
        help="Default CLI output format: `rich` (human-readable tables) or `json` (AI agent machine mode)",
    ),
):
    """
    🎨 **Set default CLI output presentation mode.**
    """
    if format not in ("rich", "json"):
        console.print("[bold red]Invalid format. Use 'rich' or 'json'.[/bold red]")
        raise typer.Exit(code=1)
    cfg = load_config()
    cfg.default_output = format  # type: ignore
    save_config(cfg)
    console.print(f"[bold green]✓[/bold green] Default output format set to '{format}'.")


@config_app.command("show")
def config_show():
    """
    📋 **Display current configuration state and active parameters.**
    """
    cfg = load_config()
    fmt = OutputFormatter(json_mode=False)
    masked_cfg = cfg.model_dump()
    if masked_cfg.get("pexels_api_key"):
        masked_cfg["pexels_api_key"] = masked_cfg["pexels_api_key"][:4] + "..." + masked_cfg["pexels_api_key"][-4:]
    if masked_cfg.get("gemini_api_key"):
        masked_cfg["gemini_api_key"] = masked_cfg["gemini_api_key"][:4] + "..." + masked_cfg["gemini_api_key"][-4:]
    if masked_cfg.get("openai_api_key"):
        masked_cfg["openai_api_key"] = masked_cfg["openai_api_key"][:4] + "..." + masked_cfg["openai_api_key"][-4:]

    fmt.print_data(masked_cfg, title="Pexels CLI Configuration")


@config_app.command("path")
def config_path():
    """
    📁 **Print absolute filesystem path to configuration JSON file.**
    """
    console.print(str(get_config_path()))


# ==========================================
# 🖼️ PHOTO SEARCH COMMANDS (DEDICATED PHOTO)
# ==========================================

@app.command("search")
@app.command("photos")
def search_photos_cmd(
    query: Optional[str] = typer.Argument(
        None,
        help="Search query term for photos (e.g., 'mountains', 'cyberpunk city')",
    ),
    queries: Optional[str] = typer.Option(
        None,
        "--queries",
        help="Comma-separated list of queries for batch execution (e.g. 'mountains,forest,ocean')",
    ),
    queries_file: Optional[Path] = typer.Option(
        None,
        "--queries-file",
        help="Path to text file containing one search query per line",
    ),
    orientation: Optional[str] = typer.Option(
        None,
        "--orientation",
        "-o",
        help="Filter orientation: `landscape`, `portrait`, or `square`",
    ),
    size: Optional[str] = typer.Option(
        None,
        "--size",
        "-s",
        help="Filter minimum resolution: `large`, `medium`, `small`",
    ),
    color: Optional[str] = typer.Option(
        None,
        "--color",
        "-c",
        help="Filter dominant color: Hex code `#FF0000` or color name `red`, `blue`, etc.",
    ),
    locale: Optional[str] = typer.Option(
        None,
        "--locale",
        "-l",
        help="Locale string (e.g. `en-US`, `uk-UA`)",
    ),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    per_page: int = typer.Option(15, "--per-page", "-n", help="Results per page (1-80)"),
    fields: Optional[str] = typer.Option(
        None,
        "--fields",
        help="Comma-separated list of keys to keep in JSON output (e.g. `id,url,photographer,width,height`)",
    ),
    state: bool = typer.Option(
        False,
        "--state",
        help="Output compact candidate objects in JSONL format with generated candidate 'state' for decision classifiers (Laya)",
    ),
    dedupe: Optional[str] = typer.Option(
        None,
        "--dedupe",
        help="Deduplicate candidates by ID across queries. Modes: 'keep-first' (default) or 'keep-all-queries'",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
):
    """
    🖼️ **Search Photos strictly (Pexels Stock Photos).**

    Supports single queries, multi-queries (`--queries`), field filtering (`--fields`), and classifier-ready JSONL (`--state`).

    ### Examples:
    ```bash
    px search "cyberpunk city" --color blue
    px search --queries "mountains,forest,sunset" --state --dedupe > candidates.jsonl
    px photos "landscape" --fields id,url,photographer --json
    ```
    """
    cfg = load_config()
    is_json = json_output or state or bool(fields) or (cfg.default_output == "json")
    fmt = OutputFormatter(json_mode=is_json)
    client = PexelsClient(cfg.pexels_api_key or "")

    try:
        validate_dedupe_mode(dedupe)
        query_list = resolve_query_list(query, queries, queries_file)
        fields_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else []

        if state:
            all_candidates = []
            for q in query_list:
                res = asyncio.run(
                    client.search_photos(
                        query=q,
                        orientation=orientation,
                        size=size,
                        color=color,
                        locale=locale,
                        page=page,
                        per_page=per_page,
                    )
                )
                for item in res.get("photos", []):
                    cand = build_candidate_state_item(item, media_type="photo", query=q)
                    all_candidates.append(cand)

            if dedupe is not None:
                all_candidates = deduplicate_candidates(all_candidates, mode=dedupe)

            if fields_list:
                all_candidates = apply_fields_filter(all_candidates, fields_list)

            fmt.print_jsonl(all_candidates)

        else:
            # Standard output mode
            all_results = []
            for q in query_list:
                res = asyncio.run(
                    client.search_photos(
                        query=q,
                        orientation=orientation,
                        size=size,
                        color=color,
                        locale=locale,
                        page=page,
                        per_page=per_page,
                    )
                )
                if fields_list:
                    res = apply_fields_filter(res, fields_list)
                all_results.append((q, res))

            if fmt.json_mode:
                if len(all_results) == 1:
                    fmt.print_data(all_results[0][1])
                else:
                    fmt.print_data([r[1] for r in all_results])
            else:
                for q, res in all_results:
                    photos = res.get("photos", [])
                    fmt.print_photos_table(
                        photos,
                        title=f"Photos matching '{q}' (Total: {res.get('total_results', 0)})"
                    )

    except PexelsClientError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


@app.command("curated")
def curated_photos_cmd(
    page: int = typer.Option(1, "--page", "-p", help="Page number of result set"),
    per_page: int = typer.Option(15, "--per-page", "-n", help="Number of results per page (1-80)"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
):
    """
    ⭐ **Get hand-picked Curated Photos selected daily by Pexels editors.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)
    try:
        client = PexelsClient(cfg.pexels_api_key or "")
        res = asyncio.run(client.curated_photos(page=page, per_page=per_page))
        if fmt.json_mode:
            fmt.print_data(res)
        else:
            fmt.print_photos_table(res.get("photos", []), title="Curated Photos")
    except PexelsClientError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


@app.command("photo")
def get_photo_cmd(
    photo_id: int = typer.Argument(..., help="Unique numeric ID of Pexels Photo (e.g., 33999682)"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
):
    """
    🔍 **Get detailed metadata for a single photo by ID.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)
    try:
        client = PexelsClient(cfg.pexels_api_key or "")
        res = asyncio.run(client.get_photo(photo_id))
        fmt.print_data(res, title=f"Photo #{photo_id}")
    except PexelsClientError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


# ==========================================
# 🎥 VIDEO SEARCH COMMANDS (DEDICATED VIDEO)
# ==========================================

@app.command("videos")
def search_videos_cmd(
    query: Optional[str] = typer.Argument(
        None,
        help="Search query term for videos (e.g. 'waterfall', 'city traffic')",
    ),
    queries: Optional[str] = typer.Option(
        None,
        "--queries",
        help="Comma-separated list of queries for batch execution (e.g. 'waterfall,ocean waves,drone footage')",
    ),
    queries_file: Optional[Path] = typer.Option(
        None,
        "--queries-file",
        help="Path to text file containing one search query per line",
    ),
    orientation: Optional[str] = typer.Option(None, "--orientation", "-o", help="Filter orientation: `landscape`, `portrait`, `square`"),
    size: Optional[str] = typer.Option(None, "--size", "-s", help="Filter minimum size: `large` (4K/HD), `medium`, `small`"),
    locale: Optional[str] = typer.Option(None, "--locale", "-l", help="Locale string"),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    per_page: int = typer.Option(15, "--per-page", "-n", help="Results per page (1-80)"),
    fields: Optional[str] = typer.Option(
        None,
        "--fields",
        help="Comma-separated list of keys to keep in JSON output (e.g. `id,url,duration,width,height`)",
    ),
    state: bool = typer.Option(
        False,
        "--state",
        help="Output compact candidate objects in JSONL format with generated candidate 'state' for decision classifiers (Laya)",
    ),
    dedupe: Optional[str] = typer.Option(
        None,
        "--dedupe",
        help="Deduplicate candidates by ID across queries. Modes: 'keep-first' (default) or 'keep-all-queries'",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
):
    """
    🎥 **Search Videos strictly (HD and 4K Pexels Stock Videos).**

    Supports single queries, multi-queries (`--queries`), field filtering (`--fields`), and classifier-ready JSONL (`--state`).

    ### Examples:
    ```bash
    px videos "drone sunset ocean" --orientation landscape
    px videos --queries "black friday shopping,christmas shopping,checkout cart" --per-page 8 --state --dedupe > candidates.jsonl
    px videos "city traffic" --fields id,url,duration,width,height --json
    ```
    """
    cfg = load_config()
    is_json = json_output or state or bool(fields) or (cfg.default_output == "json")
    fmt = OutputFormatter(json_mode=is_json)
    client = PexelsClient(cfg.pexels_api_key or "")

    try:
        validate_dedupe_mode(dedupe)
        query_list = resolve_query_list(query, queries, queries_file)
        fields_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else []

        if state:
            all_candidates = []
            for q in query_list:
                res = asyncio.run(
                    client.search_videos(
                        query=q,
                        orientation=orientation,
                        size=size,
                        locale=locale,
                        page=page,
                        per_page=per_page,
                    )
                )
                for item in res.get("videos", []):
                    cand = build_candidate_state_item(item, media_type="video", query=q)
                    all_candidates.append(cand)

            if dedupe is not None:
                all_candidates = deduplicate_candidates(all_candidates, mode=dedupe)

            if fields_list:
                all_candidates = apply_fields_filter(all_candidates, fields_list)

            fmt.print_jsonl(all_candidates)

        else:
            all_results = []
            for q in query_list:
                res = asyncio.run(
                    client.search_videos(
                        query=q,
                        orientation=orientation,
                        size=size,
                        locale=locale,
                        page=page,
                        per_page=per_page,
                    )
                )
                if fields_list:
                    res = apply_fields_filter(res, fields_list)
                all_results.append((q, res))

            if fmt.json_mode:
                if len(all_results) == 1:
                    fmt.print_data(all_results[0][1])
                else:
                    fmt.print_data([r[1] for r in all_results])
            else:
                for q, res in all_results:
                    videos = res.get("videos", [])
                    fmt.print_videos_table(
                        videos,
                        title=f"Videos matching '{q}'"
                    )

    except PexelsClientError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


@app.command("popular-videos")
def popular_videos_cmd(
    min_width: Optional[int] = typer.Option(None, "--min-width"),
    min_height: Optional[int] = typer.Option(None, "--min-height"),
    min_duration: Optional[int] = typer.Option(None, "--min-duration"),
    max_duration: Optional[int] = typer.Option(None, "--max-duration"),
    page: int = typer.Option(1, "--page", "-p"),
    per_page: int = typer.Option(15, "--per-page", "-n"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    🔥 **Browse popular and trending stock videos.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)
    try:
        client = PexelsClient(cfg.pexels_api_key or "")
        res = asyncio.run(
            client.popular_videos(
                min_width=min_width,
                min_height=min_height,
                min_duration=min_duration,
                max_duration=max_duration,
                page=page,
                per_page=per_page,
            )
        )
        if fmt.json_mode:
            fmt.print_data(res)
        else:
            fmt.print_videos_table(res.get("videos", []), title="Popular Videos")
    except PexelsClientError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


@app.command("video")
def get_video_cmd(
    video_id: int = typer.Argument(..., help="Unique numeric ID of Pexels Video"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    📼 **Get metadata and file links for a video by ID.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)
    try:
        client = PexelsClient(cfg.pexels_api_key or "")
        res = asyncio.run(client.get_video(video_id))
        fmt.print_data(res, title=f"Video #{video_id}")
    except PexelsClientError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


# ==========================================
# DOWNLOAD COMMAND
# ==========================================

@app.command("download")
def download_cmd(
    url_or_id: str = typer.Argument(
        ...,
        help="Direct file HTTP URL or numeric Pexels ID",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output filepath (e.g. `./wallpaper.jpg` or `./video.mp4`)",
    ),
    media_type: str = typer.Option(
        "photo",
        "--type",
        "-t",
        help="Media type if ID is passed: `photo` or `video`",
    ),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    ⬇️ **Download photos or videos directly to local storage.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)
    client = PexelsClient(cfg.pexels_api_key or "")

    target_url = url_or_id
    filename = "downloaded_media.jpg"

    if url_or_id.isdigit():
        media_id = int(url_or_id)
        if media_type == "video":
            res = asyncio.run(client.get_video(media_id))
            video_files = res.get("video_files", [])
            if not video_files:
                fmt.print_error(f"No video files found for video #{media_id}")
                raise typer.Exit(code=1)
            target_url = video_files[0].get("link", "")
            filename = f"pexels_video_{media_id}.mp4"
        else:
            res = asyncio.run(client.get_photo(media_id))
            target_url = res.get("src", {}).get("original", "")
            filename = f"pexels_photo_{media_id}.jpg"

    out_path = output or Path(cfg.download_dir) / filename

    if not fmt.json_mode:
        console.print(f"⬇️ Downloading [cyan]{target_url}[/cyan] -> [bold green]{out_path}[/bold green]...")

    try:
        saved_path = asyncio.run(client.download_file(target_url, out_path))
        if fmt.json_mode:
            fmt.print_data({"status": "success", "file": str(saved_path)})
        else:
            fmt.print_success(f"Successfully downloaded to {saved_path}")
    except Exception as e:
        fmt.print_error(f"Failed to download: {e}")
        raise typer.Exit(code=1)


# ==========================================
# 🤖 AI SMART SEARCH COMMANDS (SEPARATE PHOTO & VIDEO)
# ==========================================

@app.command("smart-photo")
@ai_app.command("photo")
@ai_app.command("search-photo")
def smart_photo_cmd(
    prompt: str = typer.Argument(
        ...,
        help="Natural language photo request (e.g. 'Cozy aesthetic autumn coffee shop on a rainy day')",
    ),
    per_page: int = typer.Option(10, "--per-page", "-n", help="Number of photo results"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
):
    """
    🖼️🤖 **Smart AI Photo Search.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)

    try:
        ai_provider = get_ai_provider(cfg)
        if not fmt.json_mode:
            console.print(f"🤖 [bold magenta]AI Processing natural language photo request...[/bold magenta]")

        params = asyncio.run(build_smart_photo_params(ai_provider, prompt))

        if not fmt.json_mode:
            console.print(f"🎯 [bold green]Inferred Photo Query:[/bold green] '{params.search_query}'")
            if params.orientation:
                console.print(f"📐 [bold yellow]Orientation:[/bold yellow] {params.orientation}")
            if params.color:
                console.print(f"🎨 [bold cyan]Color:[/bold cyan] {params.color}")
            console.print(f"💡 [dim]{params.explanation}[/dim]\n")

        client = PexelsClient(cfg.pexels_api_key or "")
        search_res = asyncio.run(
            client.search_photos(
                query=params.search_query,
                orientation=params.orientation,
                color=params.color,
                size=params.size,
                per_page=per_page,
            )
        )

        if fmt.json_mode:
            fmt.print_data({
                "ai_params": params.model_dump(),
                "results": search_res,
            })
        else:
            fmt.print_photos_table(
                search_res.get("photos", []),
                title=f"Smart Photo Results for '{params.search_query}'"
            )

    except (AIProviderError, PexelsClientError) as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


@app.command("smart-video")
@ai_app.command("video")
@ai_app.command("search-video")
def smart_video_cmd(
    prompt: str = typer.Argument(
        ...,
        help="Natural language video request (e.g. 'Slow motion rain drops falling on city pavement')",
    ),
    per_page: int = typer.Option(10, "--per-page", "-n", help="Number of video results"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
):
    """
    🎥🤖 **Smart AI Video Search.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)

    try:
        ai_provider = get_ai_provider(cfg)
        if not fmt.json_mode:
            console.print(f"🤖 [bold magenta]AI Processing natural language video request...[/bold magenta]")

        params = asyncio.run(build_smart_video_params(ai_provider, prompt))

        if not fmt.json_mode:
            console.print(f"🎯 [bold green]Inferred Video Query:[/bold green] '{params.search_query}'")
            if params.orientation:
                console.print(f"📐 [bold yellow]Orientation:[/bold yellow] {params.orientation}")
            console.print(f"💡 [dim]{params.explanation}[/dim]\n")

        client = PexelsClient(cfg.pexels_api_key or "")
        search_res = asyncio.run(
            client.search_videos(
                query=params.search_query,
                orientation=params.orientation,
                size=params.size,
                per_page=per_page,
            )
        )

        if fmt.json_mode:
            fmt.print_data({
                "ai_params": params.model_dump(),
                "results": search_res,
            })
        else:
            fmt.print_videos_table(
                search_res.get("videos", []),
                title=f"Smart Video Results for '{params.search_query}'"
            )

    except (AIProviderError, PexelsClientError) as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


@ai_app.command("enhance")
def enhance_cmd(
    prompt: str = typer.Argument(..., help="Prompt to enhance"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    🚀 **AI Prompt Enhancer.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)
    try:
        ai_provider = get_ai_provider(cfg)
        res = asyncio.run(enhance_prompt(ai_provider, prompt))
        fmt.print_data(res, title="Enhanced Search Prompt")
    except AIProviderError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


@ai_app.command("curate")
def curate_cmd(
    brief: str = typer.Argument(..., help="Project creative brief"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    📋 **AI Curation.**
    """
    cfg = load_config()
    fmt = get_formatter(json_output)
    try:
        ai_provider = get_ai_provider(cfg)
        res = asyncio.run(curate_project(ai_provider, brief))
        fmt.print_data(res, title=f"Project Media Curation: {res.project_title}")
    except AIProviderError as e:
        fmt.print_error(str(e))
        raise typer.Exit(code=1)


def preprocess_args(args: List[str]) -> List[str]:
    """Preprocess CLI arguments to expand standalone '--dedupe' flags into '--dedupe=keep-first'."""
    new_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--dedupe":
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                new_args.append("--dedupe=keep-first")
                i += 1
                continue
            else:
                new_args.append(arg)
                new_args.append(args[i + 1])
                i += 2
                continue
        new_args.append(arg)
        i += 1
    return new_args


def main():
    """CLI Entry point."""
    import sys
    sys.argv = preprocess_args(sys.argv)
    app()


if __name__ == "__main__":
    main()
