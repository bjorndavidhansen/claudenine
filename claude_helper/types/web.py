# types/web.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
from .common import AnalysisResult, CodeBlock, Dependency, LanguageType

class ReactComponentType(Enum):
    """Types of React components"""
    FUNCTIONAL = "functional"
    CLASS = "class"
    HOOK = "hook"
    HOC = "higher_order_component"
    PURE = "pure_component"

class ImportType(Enum):
    """Types of imports in React/TypeScript files"""
    DEFAULT = "default"
    NAMED = "named"
    NAMESPACE = "namespace"
    DYNAMIC = "dynamic"

@dataclass
class ReactComponent:
    """Represents a React component"""
    name: str
    component_type: ReactComponentType
    props: List[Dict[str, str]]  # List of prop names and types
    state: Optional[List[Dict[str, str]]]  # State variables and types
    hooks: List[str]  # Used hooks
    jsx_elements: List[str]  # Child JSX elements
    code_block: CodeBlock
    
@dataclass
class ReactHook:
    """Represents a React hook"""
    name: str
    dependencies: List[str]
    effect_type: Optional[str]  # e.g., "mount", "update", "cleanup"
    code_block: CodeBlock

@dataclass
class TypeScriptType:
    """Represents a TypeScript type definition"""
    name: str
    definition: str
    is_interface: bool = False
    extends: Optional[List[str]] = None
    implements: Optional[List[str]] = None
    code_block: CodeBlock

@dataclass
class WebAnalysisResult(AnalysisResult):
    """Analysis results specific to web technologies"""
    framework: str  # e.g., "react", "vue", "angular"
    components: List[ReactComponent]
    hooks: List[ReactHook]
    types: List[TypeScriptType]
    styles: Dict[str, str]  # CSS/styling information
    imports: Dict[str, ImportType]
    
    def __init__(self, file_path, **kwargs):
        super().__init__(
            file_path=file_path,
            language=LanguageType.REACT,
            blocks=[],
            dependencies=[],
            errors=[],
            warnings=[],
            metrics={}
        )
        self.components = []
        self.hooks = []
        self.types = []
        self.styles = {}
        self.imports = {}
        for key, value in kwargs.items():
            setattr(self, key, value)