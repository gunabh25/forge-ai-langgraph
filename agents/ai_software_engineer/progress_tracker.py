from typing import List
from rich.console import Console
from config.logging import get_logger

logger = get_logger("agents.ai_software_engineer.progress_tracker")

class ProgressTracker:
    """Tracks and displays real-time progress of file generation."""
    
    def __init__(self, total_files: int):
        self.total_files = total_files
        self.completed_files: List[str] = []
        self.failed_files: List[str] = []
        self.skipped_files: List[str] = []
        self.pending_files: List[str] = []
        self.console = Console()
        
    def set_pending(self, files: List[str]):
        self.pending_files = files.copy()
        
    def mark_completed(self, file_path: str):
        if file_path in self.pending_files:
            self.pending_files.remove(file_path)
        self.completed_files.append(file_path)
        self._display_progress(file_path, "✅ Generated")
        
    def mark_failed(self, file_path: str):
        if file_path in self.pending_files:
            self.pending_files.remove(file_path)
        self.failed_files.append(file_path)
        self._display_progress(file_path, "❌ Failed")
        
    def mark_skipped(self, file_path: str):
        if file_path in self.pending_files:
            self.pending_files.remove(file_path)
        self.skipped_files.append(file_path)
        self._display_progress(file_path, "⏭️  Skipped (Cached)")
        
    def _display_progress(self, current_file: str, status: str):
        """Displays real-time progress updates safely."""
        total_done = len(self.completed_files) + len(self.skipped_files) + len(self.failed_files)
        pct = 0
        if self.total_files > 0:
            pct = int((total_done / self.total_files) * 100)
            
        # Logging standard
        logger.info(f"{status}: {current_file} [{total_done}/{self.total_files} | {pct}%]")
        
        # We can also print a nice line. If this runs inside a rich Live display, 
        # print() is safely redirected above the dashboard.
        self.console.print(f"[cyan]AI Software Engineer[/cyan] | {status} [bold]{current_file}[/bold] ({pct}%)")
