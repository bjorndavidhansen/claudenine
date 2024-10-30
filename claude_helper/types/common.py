# types/common.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from pathlib import Path
from enum import Enum

class LanguageType(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    REACT = "react"

class AnalysisType(Enum):
    """Types of analysis that can be performed"""
    CODE_STRUCTURE = "code_structure"
    DEPENDENCIES = "dependencies"
    COMPLEXITY = "complexity"
    DOCUMENTATION = "documentation"
    TYPE_HINTS = "type_hints"

@dataclass
class FileLocation:
    """Represents a location in a source file"""
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None

@dataclass
class CodeBlock:
    """Represents a block of code with location information"""
    content: str
    location: FileLocation
    block_type: str  # e.g., "function", "class", "method"

@dataclass
class Dependency:
    """Represents a code dependency"""
    name: str
    version: Optional[str] = None
    is_local: bool = False
    import_path: Optional[str] = None
    used_in: Optional[List[FileLocation]] = None

@dataclass
class AnalysisResult:
    """Base class for analysis results"""
    file_path: Path
    language: LanguageType
    blocks: List[CodeBlock]
    dependencies: List[Dependency]
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]  # Flexible metrics storage

@dataclass
class AnalysisOptions:
    """Configuration options for analysis"""
    max_file_size: int = 1024 * 1024  # 1MB default
    ignore_patterns: List[str] = None
    analysis_types: List[AnalysisType] = None
    include_metrics: bool = True
    include_documentation: bool = True
    max_depth: int = 3  # For recursive analysis