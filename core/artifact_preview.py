"""Artifact Previewer for displaying interactive previews of generated artifacts."""

import os
import subprocess
from typing import Optional
# pyrefly: ignore [missing-import]
from rich.console import Console
# pyrefly: ignore [missing-import]
from rich.panel import Panel
# pyrefly: ignore [missing-import]
from rich.markdown import Markdown

console = Console()

class ArtifactPreview:
    """Provides file statistics and markdown previews for generated artifacts."""
    
    @staticmethod
    def display(file_path: str, preview_lines: int = 15, console: Optional[Console] = None) -> None:
        """Displays a preview of the artifact and prompts to open it.
        
        Args:
            file_path: Path to the artifact file.
            preview_lines: Number of lines to preview.
            console: Optional rich Console instance to use.
        """
        c = console or Console()
        if not os.path.exists(file_path):
            c.print(f"[red]Cannot preview artifact, file not found: {file_path}[/red]")
            return
            
        file_name = os.path.basename(file_path)
        dir_name = os.path.dirname(file_path)
        
        # Calculate stats
        size_bytes = os.path.getsize(file_path)
        size_str = f"{size_bytes / 1024:.1f} KB"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
                line_count = len(lines)
                preview_content = "\n".join(lines[:preview_lines])
                if line_count > preview_lines:
                    preview_content += "\n\n..."
        except Exception as e:
            c.print(f"[red]Error reading artifact {file_path}: {e}[/red]")
            return

        # Render output
        c.print("──────────────────────────────")
        c.print(f"[bold cyan]{file_name}[/bold cyan]")
        c.print("\n[bold]Location[/bold]")
        c.print(f"{dir_name}/")
        c.print("\n[bold]Lines[/bold]")
        c.print(str(line_count))
        c.print("\n[bold]Size[/bold]")
        c.print(size_str)
        c.print("\n[bold]Preview[/bold]")
        c.print(Panel(Markdown(preview_content), title=file_name, border_style="cyan"))
        c.print("──────────────────────────────\n")
        
        # Prompt to open
        if "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("DEMO_MODE") == "1" or not __import__("sys").stdin.isatty():
            return
        try:
            choice = input(f"Open this artifact? [Y] Yes / [N] No: ").strip().lower()
            if choice == "y":
                ArtifactPreview.open_file(file_path, console=c)
        except (KeyboardInterrupt, EOFError):
            pass

    @staticmethod
    def open_file(file_path: str, console: Optional[Console] = None) -> None:
        """Opens the file in the default system editor/viewer.
        
        Args:
            file_path: Path to the file.
            console: Optional rich Console instance.
        """
        c = console or Console()
        try:
            # macOS
            if os.uname().sysname == 'Darwin':
                subprocess.call(('open', file_path))
            # Linux
            elif os.uname().sysname == 'Linux':
                subprocess.call(('xdg-open', file_path))
            # Windows fallback
                # pyrefly: ignore [missing-attribute]
            else:
                # pyrefly: ignore [missing-attribute]
                os.startfile(file_path)
        except Exception as e:
            c.print(f"[red]Failed to open file: {e}[/red]")
