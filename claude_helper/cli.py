# cli.py

import asyncio
import hashlib
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table

from .config.settings import ConfigManager
from .utils.cache import AnalysisCache
from .utils.progress import ProgressTracker
from .analyzers.web.react import ReactAnalyzer
from .analyzers.python import PythonAnalyzer

class ClaudeHelper:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.config_manager = ConfigManager()
        self.cache = AnalysisCache(self.config_manager.config.cache)
        self.console = Console()
        
        # Initialize analyzers
        self.analyzers = {
            '.py': PythonAnalyzer(workspace_path),
            '.tsx': ReactAnalyzer(workspace_path),
            '.jsx': ReactAnalyzer(workspace_path),
            '.ts': ReactAnalyzer(workspace_path)
        }

    async def analyze_file(self, file_path: Path) -> dict:
        """Analyze a single file with caching"""
        # Get file hash for cache key
        content = self.analyzers[0].read_file(file_path)
        if not content:
            raise ValueError(f"Could not read file: {file_path}")
            
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check cache first
        cached = self.cache.get(str(file_path), content_hash)
        if cached:
            return cached

        # Get appropriate analyzer
        suffix = file_path.suffix
        analyzer = self.analyzers.get(suffix)
        if not analyzer:
            raise ValueError(f"No analyzer available for {suffix} files")

        # Run analysis
        analysis = analyzer.analyze_file(file_path)
        dependencies = analyzer.get_dependencies(analysis)
        
        # Build Claude prompt and get analysis
        prompt = self._build_analysis_prompt(analysis, dependencies)
        claude_analysis = await self._get_claude_analysis(prompt)
        
        # Prepare and cache result
        result = {
            "file": str(file_path),
            "framework": getattr(analysis, 'framework', 'unknown'),
            "analysis": claude_analysis,
            "details": analysis
        }
        
        self.cache.set(str(file_path), content_hash, result)
        return result

    async def batch_analyze(self, files: List[Path]):
        """Analyze multiple files with progress tracking"""
        tracker = ProgressTracker(len(files))
        
        for file in files:
            tracker.start_file(str(file))
            try:
                result = await self.analyze_file(file)
                tracker.complete_file("success")
                yield result
            except Exception as e:
                tracker.complete_file("error", str(e))
                self.console.print(f"[red]Error analyzing {file}: {e}[/red]")

    async def analyze_workspace(self):
        """Analyze entire workspace"""
        files = self._find_analyzable_files()
        async for result in self.batch_analyze(files):
            yield result

    def _find_analyzable_files(self) -> List[Path]:
        """Find all files that can be analyzed"""
        files = []
        for suffix in self.analyzers.keys():
            files.extend(self.workspace_path.rglob(f"*{suffix}"))
            
        return [
            f for f in files 
            if not self.config_manager.should_ignore_file(str(f))
        ]

    def display_cache_stats(self):
        """Display cache statistics"""
        stats = self.cache.get_stats()
        table = Table(title="Cache Statistics")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            table.add_row(key.replace('_', ' ').title(), str(value))
            
        self.console.print(table)

async def main():
    # Get workspace path
    workspace = Path.cwd()
    helper = ClaudeHelper(workspace)
    
    # Parse arguments and run appropriate command
    import argparse
    parser = argparse.ArgumentParser(description='Claude-assisted code analysis')
    
    parser.add_argument('--file', help='Analyze a specific file')
    parser.add_argument('--cache-stats', action='store_true', 
                       help='Display cache statistics')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Clear analysis cache')
    parser.add_argument('--batch', action='store_true',
                       help='Analyze all files in workspace')
    
    args = parser.parse_args()
    
    if args.cache_stats:
        helper.display_cache_stats()
        return
        
    if args.clear_cache:
        helper.cache.clear()
        print("Cache cleared")
        return
        
    if args.file:
        result = await helper.analyze_file(Path(args.file))
        helper.display_analysis(result)
    elif args.batch:
        async for result in helper.analyze_workspace():
            helper.display_analysis(result)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())