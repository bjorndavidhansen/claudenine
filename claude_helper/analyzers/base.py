# analyzers/base.py

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from ..types.common import (
    AnalysisResult, 
    AnalysisOptions,
    CodeBlock,
    Dependency,
    LanguageType
)

class BaseAnalyzer(ABC):
    """Base class for all code analyzers"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.options = AnalysisOptions()
        self._file_cache: Dict[str, str] = {}
        self._dependency_cache: Dict[str, Set[str]] = {}
        
    def read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with caching"""
        str_path = str(file_path)
        
        if str_path in self._file_cache:
            return self._file_cache[str_path]
            
        if not file_path.exists():
            return None
            
        if file_path.stat().st_size > self.options.max_file_size:
            raise ValueError(
                f"File {file_path} exceeds maximum size "
                f"({self.options.max_file_size} bytes)"
            )
            
        try:
            content = file_path.read_text(encoding='utf-8')
            self._file_cache[str_path] = content
            return content
        except Exception as e:
            raise ValueError(f"Failed to read {file_path}: {str(e)}")

    def get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file content"""
        content = self.read_file(file_path)
        if content is None:
            raise ValueError(f"Cannot hash nonexistent file: {file_path}")
        return hashlib.md5(content.encode()).hexdigest()

    @abstractmethod
    def analyze_file(self, file_path: Path) -> AnalysisResult:
        """Analyze a single file"""
        pass
        
    @abstractmethod
    def get_language_type(self) -> LanguageType:
        """Get the language type this analyzer handles"""
        pass

    def get_dependencies(self, analysis: AnalysisResult) -> List[Dependency]:
        """Extract dependencies from analysis result"""
        return analysis.dependencies

    def analyze_dependencies(self, file_path: Path, depth: int = 1) -> Set[str]:
        """Analyze file dependencies recursively up to specified depth"""
        if depth < 1:
            return set()
            
        str_path = str(file_path)
        if str_path in self._dependency_cache:
            return self._dependency_cache[str_path]
            
        analysis = self.analyze_file(file_path)
        dependencies = set()
        
        for dep in analysis.dependencies:
            if dep.is_local and dep.import_path:
                dep_path = (self.workspace_path / dep.import_path).resolve()
                if dep_path.exists():
                    dependencies.add(str(dep_path))
                    if depth > 1:
                        nested_deps = self.analyze_dependencies(
                            dep_path, 
                            depth - 1
                        )
                        dependencies.update(nested_deps)
                        
        self._dependency_cache[str_path] = dependencies
        return dependencies

    def extract_code_blocks(self, content: str) -> List[CodeBlock]:
        """Extract code blocks from file content"""
        # This is a placeholder - subclasses should implement
        # language-specific extraction
        return []

    def collect_metrics(self, content: str, blocks: List[CodeBlock]) -> Dict[str, Any]:
        """Collect code metrics"""
        lines = content.splitlines()
        return {
            'total_lines': len(lines),
            'code_lines': len([l for l in lines if l.strip()]),
            'comment_lines': len([l for l in lines if l.strip().startswith('#')]),
            'empty_lines': len([l for l in lines if not l.strip()]),
            'blocks': len(blocks),
            'avg_block_size': sum(len(b.content.splitlines()) for b in blocks) / len(blocks) if blocks else 0
        }

    def validate_file(self, file_path: Path) -> bool:
        """Validate if file can be analyzed"""
        if not file_path.exists():
            return False
            
        if file_path.stat().st_size > self.options.max_file_size:
            return False
            
        if self.options.ignore_patterns:
            str_path = str(file_path)
            for pattern in self.options.ignore_patterns:
                if pattern in str_path:
                    return False
                    
        return True

    def clear_caches(self):
        """Clear internal caches"""
        self._file_cache.clear()
        self._dependency_cache.clear()