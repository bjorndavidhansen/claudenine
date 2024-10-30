# utils/progress.py

import time
from typing import List, Optional
from dataclasses import dataclass
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    SpinnerColumn
)
from rich.console import Console
from rich.table import Table

@dataclass
class AnalysisTask:
    file_path: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "pending"
    error: Optional[str] = None

class ProgressTracker:
    def __init__(self, total_files: int):
        self.console = Console()
        self.total_files = total_files
        self.tasks: List[AnalysisTask] = []
        self.current_task: Optional[AnalysisTask] = None
        self.start_time = time.time()
        
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        
        self.task_id = self.progress.add_task(
            "[cyan]Analyzing files...",
            total=total_files
        )

    def start_file(self, file_path: str):
        """Start tracking a new file analysis"""
        self.current_task = AnalysisTask(
            file_path=file_path,
            start_time=time.time()
        )
        self.tasks.append(self.current_task)
        
        # Update progress display
        self.progress.update(
            self.task_id,
            description=f"[cyan]Analyzing {file_path}...",
            advance=0
        )

    def complete_file(self, status: str = "success", error: Optional[str] = None):
        """Mark current file as complete"""
        if self.current_task:
            self.current_task.end_time = time.time()
            self.current_task.status = status
            self.current_task.error = error
            
            # Update progress
            self.progress.update(
                self.task_id,
                advance=1
            )
            
            completed = len([t for t in self.tasks if t.end_time is not None])
            if completed == self.total_files:
                self.progress.stop()
                self.display_summary()

    def display_summary(self):
        """Display analysis summary"""
        total_time = time.time() - self.start_time
        successful = len([t for t in self.tasks if t.status == "success"])
        failed = len([t for t in self.tasks if t.status == "error"])
        
        table = Table(title="Analysis Summary")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Files", str(self.total_files))
        table.add_row("Successful", str(successful))
        table.add_row("Failed", str(failed))
        table.add_row("Total Time", f"{total_time:.2f}s")
        
        if self.tasks:
            avg_time = sum(
                (t.end_time - t.start_time) 
                for t in self.tasks 
                if t.end_time
            ) / len(self.tasks)
            table.add_row("Average Time per File", f"{avg_time:.2f}s")
        
        self.console.print("\n")
        self.console.print(table)
        
        if failed > 0:
            self.display_errors()

    def display_errors(self):
        """Display error summary"""
        error_table = Table(title="Analysis Errors", style="red")
        
        error_table.add_column("File", style="cyan")
        error_table.add_column("Error", style="red")
        
        for task in self.tasks:
            if task.status == "error" and task.error:
                error_table.add_row(task.file_path, task.error)
        
        self.console.print("\n")
        self.console.print(error_table)

    def get_estimated_time(self) -> float:
        """Get estimated time remaining"""
        completed_tasks = [t for t in self.tasks if t.end_time is not None]
        if not completed_tasks:
            return 0
            
        avg_time = sum(
            t.end_time - t.start_time for t in completed_tasks
        ) / len(completed_tasks)
        
        remaining = self.total_files - len(completed_tasks)
        return avg_time * remaining