# analyzers/python.py

import ast
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

from .base import BaseAnalyzer
from ..types.common import (
    AnalysisResult,
    CodeBlock,
    Dependency,
    FileLocation,
    LanguageType
)

@dataclass
class PythonFunction:
    """Python function details"""
    name: str
    args: List[str]
    returns: Optional[str]
    decorators: List[str]
    docstring: Optional[str]
    is_async: bool
    complexity: int

@dataclass
class PythonClass:
    """Python class details"""
    name: str
    bases: List[str]
    methods: List[PythonFunction]
    decorators: List[str]
    docstring: Optional[str]

class PythonAnalyzer(BaseAnalyzer):
    def __init__(self, workspace_path: Path):
        super().__init__(workspace_path)
        self._import_cache: Dict[str, Set[str]] = {}

    def get_language_type(self) -> LanguageType:
        return LanguageType.PYTHON

    def analyze_file(self, file_path: Path) -> AnalysisResult:
        """Analyze Python file"""
        content = self.read_file(file_path)
        if not content:
            raise ValueError(f"Could not read file: {file_path}")

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return AnalysisResult(
                file_path=file_path,
                language=self.get_language_type(),
                blocks=[],
                dependencies=[],
                errors=[f"Syntax error: {str(e)}"],
                warnings=[],
                metrics={}
            )

        # Analyze components
        imports = self._analyze_imports(tree)
        functions = self._analyze_functions(tree)
        classes = self._analyze_classes(tree)
        
        # Extract blocks
        blocks = self._create_code_blocks(content, functions, classes)
        
        # Collect metrics
        metrics = self._collect_python_metrics(tree, functions, classes)
        
        # Build dependencies
        dependencies = self._build_dependencies(imports)

        return AnalysisResult(
            file_path=file_path,
            language=self.get_language_type(),
            blocks=blocks,
            dependencies=dependencies,
            errors=[],
            warnings=self._collect_warnings(tree),
            metrics=metrics
        )

    def _analyze_imports(self, tree: ast.AST) -> List[Tuple[str, str, FileLocation]]:
        """Analyze Python imports"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append((
                        name.name,
                        name.asname or name.name,
                        FileLocation(node.lineno, node.col_offset)
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for name in node.names:
                    full_name = f"{module}.{name.name}" if module else name.name
                    imports.append((
                        full_name,
                        name.asname or name.name,
                        FileLocation(node.lineno, node.col_offset)
                    ))
        
        return imports

    def _analyze_functions(self, tree: ast.AST) -> List[PythonFunction]:
        """Analyze Python functions"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                args = [arg.arg for arg in node.args.args]
                returns = self._get_return_annotation(node)
                decorators = [self._get_decorator_name(d) for d in node.decorator_list]
                docstring = ast.get_docstring(node)
                
                functions.append(PythonFunction(
                    name=node.name,
                    args=args,
                    returns=returns,
                    decorators=decorators,
                    docstring=docstring,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    complexity=self._calculate_complexity(node)
                ))
        
        return functions

    def _analyze_classes(self, tree: ast.AST) -> List[PythonClass]:
        """Analyze Python classes"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [self._get_base_name(b) for b in node.bases]
                methods = []
                
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [arg.arg for arg in child.args.args]
                        returns = self._get_return_annotation(child)
                        decorators = [self._get_decorator_name(d) for d in child.decorator_list]
                        docstring = ast.get_docstring(child)
                        
                        methods.append(PythonFunction(
                            name=child.name,
                            args=args,
                            returns=returns,
                            decorators=decorators,
                            docstring=docstring,
                            is_async=isinstance(child, ast.AsyncFunctionDef),
                            complexity=self._calculate_complexity(child)
                        ))
                
                classes.append(PythonClass(
                    name=node.name,
                    bases=bases,
                    methods=methods,
                    decorators=[self._get_decorator_name(d) for d in node.decorator_list],
                    docstring=ast.get_docstring(node)
                ))
        
        return classes

    def _create_code_blocks(
        self, 
        content: str, 
        functions: List[PythonFunction], 
        classes: List[PythonClass]
    ) -> List[CodeBlock]:
        """Create code blocks from analyzed components"""
        blocks = []
        lines = content.splitlines()
        
        # Add function blocks
        for func in functions:
            block_content = self._extract_block_content(lines, func.name)
            if block_content:
                blocks.append(CodeBlock(
                    content=block_content,
                    location=FileLocation(0, 0),  # TODO: Add proper location tracking
                    block_type="function"
                ))
        
        # Add class blocks
        for cls in classes:
            block_content = self._extract_block_content(lines, cls.name)
            if block_content:
                blocks.append(CodeBlock(
                    content=block_content,
                    location=FileLocation(0, 0),  # TODO: Add proper location tracking
                    block_type="class"
                ))
        
        return blocks

    def _collect_python_metrics(
        self, 
        tree: ast.AST, 
        functions: List[PythonFunction], 
        classes: List[PythonClass]
    ) -> Dict[str, Any]:
        """Collect Python-specific metrics"""
        metrics = super().collect_metrics("", [])  # Get base metrics
        
        # Add Python-specific metrics
        metrics.update({
            'num_functions': len(functions),
            'num_classes': len(classes),
            'num_methods': sum(len(c.methods) for c in classes),
            'avg_function_complexity': sum(f.complexity for f in functions) / len(functions) if functions else 0,
            'documented_items': len([f for f in functions if f.docstring]) + 
                              len([c for c in classes if c.docstring]),
            'async_functions': len([f for f in functions if f.is_async])
        })
        
        return metrics

    def _build_dependencies(
        self, 
        imports: List[Tuple[str, str, FileLocation]]
    ) -> List[Dependency]:
        """Build dependency list from imports"""
        dependencies = []
        
        for imp_name, alias, location in imports:
            is_local = '.' in imp_name and not any(
                imp_name.startswith(pkg) 
                for pkg in ['django', 'flask', 'fastapi']  # Common package prefixes
            )
            
            dependencies.append(Dependency(
                name=imp_name,
                is_local=is_local,
                import_path=imp_name.replace('.', '/') + '.py' if is_local else None,
                used_in=[location]
            ))
        
        return dependencies

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try,
                                ast.ExceptHandler, ast.With, ast.Assert,
                                ast.Raise)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            
        return complexity

    @staticmethod
    def _get_decorator_name(node: ast.expr) -> str:
        """Get decorator name from node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return f"{node.func.value.id}.{node.func.attr}"
        return ""

    @staticmethod
    def _get_return_annotation(node: ast.FunctionDef) -> Optional[str]:
        """Get return type annotation"""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return str(node.returns.value)
        return None

    @staticmethod
    def _get_base_name(node: ast.expr) -> str:
        """Get base class name from node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{node.value.id}.{node.attr}"
        return ""

    def _extract_block_content(self, lines: List[str], name: str) -> Optional[str]:
        """Extract block content from source lines"""
        # Simple implementation - could be improved with ast locations
        try:
            for i, line in enumerate(lines):
                if f"def {name}" in line or f"class {name}" in line:
                    block_lines = []
                    indent = len(line) - len(line.lstrip())
                    block_lines.append(line)
                    
                    for next_line in lines[i+1:]:
                        if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= indent:
                            break
                        block_lines.append(next_line)
                        
                    return "\n".join(block_lines)
        except Exception:
            pass
        return None

    def _collect_warnings(self, tree: ast.AST) -> List[str]:
        """Collect code warnings"""
        warnings = []
        
        for node in ast.walk(tree):
            # Check for broad except clauses
            if isinstance(node, ast.ExceptHandler):
                if node.type is None or (
                    isinstance(node.type, ast.Name) and 
                    node.type.id == 'Exception'
                ):
                    warnings.append(f"Broad exception handler at line {node.lineno}")
            
            # Check for mutable default arguments
            elif isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        warnings.append(
                            f"Mutable default argument in function {node.name} "
                            f"at line {node.lineno}"
                        )
        
        return warnings