"""Formatter module for human-friendly (rich) and machine-friendly (json) CLI output."""

import json
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax


console = Console()
error_console = Console(stderr=True)


class OutputFormatter:
    """Output formatter supporting rich terminal presentation and AI agent JSON mode."""

    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode

    def print_data(self, data: Any, title: Optional[str] = None) -> None:
        """Print data as JSON or rich output based on mode."""
        if self.json_mode:
            if isinstance(data, BaseModel):
                data_dict = data.model_dump()
            elif hasattr(data, "to_dict"):
                data_dict = data.to_dict()
            else:
                data_dict = data
            sys.stdout.write(json.dumps(data_dict, indent=2, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        else:
            if title:
                console.print(f"[bold cyan]=== {title} ===[/bold cyan]")

            if isinstance(data, BaseModel):
                data_dict = data.model_dump()
                json_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
                console.print(Syntax(json_str, "json", theme="monokai", word_wrap=True))
            elif isinstance(data, dict):
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                console.print(Syntax(json_str, "json", theme="monokai", word_wrap=True))
            else:
                console.print(data)

    def print_photos_table(self, photos: List[Dict[str, Any]], title: str = "Pexels Photos") -> None:
        """Print a rich table of photos."""
        if self.json_mode:
            self.print_data(photos)
            return

        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Photographer", style="green")
        table.add_column("Dimensions", style="yellow")
        table.add_column("Original URL / Link", style="blue", overflow="fold")

        for p in photos:
            table.add_row(
                str(p.get("id", "")),
                p.get("photographer", "N/A"),
                f"{p.get('width', '')}x{p.get('height', '')}",
                p.get("src", {}).get("original") or p.get("url", ""),
            )

        console.print(table)

    def print_videos_table(self, videos: List[Dict[str, Any]], title: str = "Pexels Videos") -> None:
        """Print a rich table of videos."""
        if self.json_mode:
            self.print_data(videos)
            return

        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("User", style="green")
        table.add_column("Duration (s)", style="yellow")
        table.add_column("Dimensions", style="dim")
        table.add_column("Video Link", style="blue", overflow="fold")

        for v in videos:
            table.add_row(
                str(v.get("id", "")),
                v.get("user", {}).get("name", "N/A"),
                str(v.get("duration", "N/A")),
                f"{v.get('width', '')}x{v.get('height', '')}",
                v.get("url", ""),
            )

        console.print(table)

    def print_info(self, message: str) -> None:
        """Print info message."""
        if not self.json_mode:
            console.print(f"[bold blue]i[/bold blue] {message}")

    def print_success(self, message: str) -> None:
        """Print success message."""
        if not self.json_mode:
            console.print(f"[bold green]✓[/bold green] {message}")

    def print_error(self, message: str) -> None:
        """Print error message to stderr."""
        if self.json_mode:
            err_dict = {"error": True, "message": message}
            sys.stderr.write(json.dumps(err_dict, ensure_ascii=False) + "\n")
        else:
            error_console.print(f"[bold red]✗ ERROR:[/bold red] {message}")
