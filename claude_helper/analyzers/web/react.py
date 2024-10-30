# analyzers/web/react.py

import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass

from ..base import BaseAnalyzer
from ...types.common import (
    AnalysisResult,
    CodeBlock,
    Dependency,
    FileLocation,
    LanguageType
)
from ...types.web import (
    ReactComponentType,
    ImportType,
    ReactComponent,
    ReactHook,
    TypeScriptType,
    WebAnalysisResult
)

@dataclass
class JSImport:
    """JavaScript/TypeScript import details"""
    module: str
    items: List[str]
    import_type: ImportType
    location: FileLocation

class ReactAnalyzer(BaseAnalyzer):
    def __init__(self, workspace_path: Path):
        super().__init__(workspace_path)
        self._component_cache: Dict[str, List[ReactComponent]] = {}
        self._import_patterns = {
            'default': re.compile(r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'),
            'named': re.compile(r'import\s*{([^}]+)}\s*from\s*[\'"]([^\'"]+)[\'"]'),
            'namespace': re.compile(r'import\s*\*\s*as\s*(\w+)\s*from\s*[\'"]([^\'"]+)[\'"]'),
            'dynamic': re.compile(r'import\([\'"]([^\'"]+)[\'"]\)')
        }
        self._hook_pattern = re.compile(r'use[A-Z]\w+')
        self._component_pattern = re.compile(r'function\s+(\w+)\s*\([^)]*\)\s*{|class\s+(\w+)\s+extends\s+React\.Component')

    def get_language_type(self) -> LanguageType:
        return LanguageType.REACT

    def analyze_file(self, file_path: Path) -> WebAnalysisResult:
        """Analyze React/TypeScript file"""
        content = self.read_file(file_path)
        if not content:
            raise ValueError(f"Could not read file: {file_path}")

        # Analyze components
        imports = self._analyze_imports(content)
        components = self._analyze_components(content)
        hooks = self._analyze_hooks(content)
        types = self._analyze_types(content) if file_path.suffix in {'.tsx', '.ts'} else []
        
        # Extract blocks
        blocks = self._create_code_blocks(content, components, hooks)
        
        # Build dependencies
        dependencies = self._build_dependencies(imports)
        
        # Analyze styles
        styles = self._analyze_styles(content)
        
        # Collect metrics
        metrics = self._collect_react_metrics(content, components, hooks, types)

        return WebAnalysisResult(
            file_path=file_path,
            framework="react",
            components=components,
            hooks=hooks,
            types=types,
            styles=styles,
            imports=self._categorize_imports(imports)
        )

    def _analyze_imports(self, content: str) -> List[JSImport]:
        """Analyze JavaScript/TypeScript imports"""
        imports = []
        
        # Default imports
        for match in self._import_patterns['default'].finditer(content):
            name, module = match.groups()
            imports.append(JSImport(
                module=module,
                items=[name],
                import_type=ImportType.DEFAULT,
                location=self._get_location(content, match.start())
            ))
        
        # Named imports
        for match in self._import_patterns['named'].finditer(content):
            items, module = match.groups()
            imports.append(JSImport(
                module=module,
                items=[item.strip() for item in items.split(',')],
                import_type=ImportType.NAMED,
                location=self._get_location(content, match.start())
            ))
        
        # Namespace imports
        for match in self._import_patterns['namespace'].finditer(content):
            name, module = match.groups()
            imports.append(JSImport(
                module=module,
                items=[name],
                import_type=ImportType.NAMESPACE,
                location=self._get_location(content, match.start())
            ))
        
        # Dynamic imports
        for match in self._import_patterns['dynamic'].finditer(content):
            module = match.group(1)
            imports.append(JSImport(
                module=module,
                items=[],
                import_type=ImportType.DYNAMIC,
                location=self._get_location(content, match.start())
            ))
            
        return imports

    def _analyze_components(self, content: str) -> List[ReactComponent]:
        """Analyze React components"""
        components = []
        
        # Find component definitions
        for match in self._component_pattern.finditer(content):
            name = match.group(1) or match.group(2)
            if name:
                component_type = (
                    ReactComponentType.CLASS if match.group(2)
                    else ReactComponentType.FUNCTIONAL
                )
                
                # Extract component block
                block_start = match.start()
                block_end = self._find_closing_brace(content, block_start)
                block_content = content[block_start:block_end]
                
                # Analyze props and state
                props = self._analyze_props(block_content)
                hooks = self._find_hooks(block_content)
                jsx_elements = self._find_jsx_elements(block_content)
                
                components.append(ReactComponent(
                    name=name,
                    component_type=component_type,
                    props=props,
                    state=self._analyze_state(block_content) if component_type == ReactComponentType.CLASS else None,
                    hooks=hooks,
                    jsx_elements=jsx_elements,
                    code_block=CodeBlock(
                        content=block_content,
                        location=self._get_location(content, block_start),
                        block_type="component"
                    )
                ))
        
        return components

    def _analyze_hooks(self, content: str) -> List[ReactHook]:
        """Analyze React hooks"""
        hooks = []
        
        for match in self._hook_pattern.finditer(content):
            hook_name = match.group()
            
            # Find hook definition
            block_start = match.start()
            block_end = self._find_closing_brace(content, block_start)
            block_content = content[block_start:block_end]
            
            # Analyze dependencies
            dependencies = self._find_dependencies(block_content)
            effect_type = self._determine_effect_type(block_content)
            
            hooks.append(ReactHook(
                name=hook_name,
                dependencies=dependencies,
                effect_type=effect_type,
                code_block=CodeBlock(
                    content=block_content,
                    location=self._get_location(content, block_start),
                    block_type="hook"
                )
            ))
        
        return hooks

    def _analyze_types(self, content: str) -> List[TypeScriptType]:
        """Analyze TypeScript types and interfaces"""
        types = []
        
        # Find type definitions
        type_pattern = re.compile(r'(type|interface)\s+(\w+)')
        for match in type_pattern.finditer(content):
            kind, name = match.groups()
            
            # Extract type definition
            block_start = match.start()
            block_end = self._find_closing_brace(content, block_start)
            block_content = content[block_start:block_end]
            
            extends = self._find_extends(block_content)
            implements = self._find_implements(block_content)
            
            types.append(TypeScriptType(
                name=name,
                definition=block_content,
                is_interface=kind == 'interface',
                extends=extends,
                implements=implements,
                code_block=CodeBlock(
                    content=block_content,
                    location=self._get_location(content, block_start),
                    block_type="type"
                )
            ))
        
        return types

    def _analyze_styles(self, content: str) -> Dict[str, str]:
        """Analyze CSS-in-JS and other styling approaches"""
        styles = {}
        
        # Find styled-components
        styled_pattern = re.compile(r'const\s+(\w+)\s*=\s*styled\.[^`]*`([^`]*)`')
        for match in styled_pattern.finditer(content):
            component_name, style_content = match.groups()
            styles[component_name] = style_content.strip()
        
        # Find CSS imports
        css_import_pattern = re.compile(r'import\s+[\'"]([^\'"]*.css)[\'"]')
        for match in css_import_pattern.finditer(content):
            css_file = match.group(1)
            styles[css_file] = "imported"
        
        return styles

    def _build_dependencies(self, imports: List[JSImport]) -> List[Dependency]:
        """Build dependency list from imports"""
        dependencies = []
        
        for imp in imports:
            is_local = (
                imp.module.startswith('.') or 
                imp.module.startswith('/')
            )
            
            dependencies.append(Dependency(
                name=imp.module,
                is_local=is_local,
                import_path=imp.module if is_local else None,
                used_in=[imp.location]
            ))
        
        return dependencies

    def _collect_react_metrics(
        self,
        content: str,
        components: List[ReactComponent],
        hooks: List[ReactHook],
        types: List[TypeScriptType]
    ) -> Dict[str, Any]:
        """Collect React-specific metrics"""
        metrics = super().collect_metrics("", [])  # Get base metrics
        
        # Add React-specific metrics
        metrics.update({
            'num_components': len(components),
            'num_hooks': len(hooks),
            'num_types': len(types),
            'functional_components': len([c for c in components if c.component_type == ReactComponentType.FUNCTIONAL]),
            'class_components': len([c for c in components if c.component_type == ReactComponentType.CLASS]),
            'avg_props_per_component': sum(len(c.props) for c in components) / len(components) if components else 0,
            'components_with_hooks': len([c for c in components if c.hooks])
        })
        
        return metrics

    @staticmethod
    def _get_location(content: str, offset: int) -> FileLocation:
        """Convert string offset to line and column"""
        lines = content[:offset].splitlines()
        return FileLocation(
            line=len(lines),
            column=len(lines[-1]) if lines else 0
        )

    @staticmethod
    def _find_closing_brace(content: str, start: int) -> int:
        """Find matching closing brace"""
        stack = []
        for i, char in enumerate(content[start:], start):
            if char == '{':
                stack.append(char)
            elif char == '}':
                stack.pop()
                if not stack:
                    return i + 1
        return len(content)

    def _analyze_props(self, content: str) -> List[Dict[str, str]]:
        """Analyze component props"""
        props = []
        prop_pattern = re.compile(r'props\.(\w+)|{\s*(\w+)\s*}')
        
        for match in prop_pattern.finditer(content):
            prop_name = match.group(1) or match.group(2)
            if prop_name:
                props.append({'name': prop_name, 'type': 'any'})  # Type inference could be improved
        
        return props

    def _analyze_state(self, content: str) -> List[Dict[str, str]]:
        """Analyze component state"""
        state = []
        state_pattern = re.compile(r'this\.state\.(\w+)|state\s*=\s*{([^}]+)}')
        
        for match in state_pattern.finditer(content):
            if match.group(1):
                state.append({'name': match.group(1), 'type': 'any'})
            elif match.group(2):
                for item in match.group(2).split(','):
                    if ':' in item:
                        name, _ = item.split(':')
                        state.append({'name': name.strip(), 'type': 'any'})
        
        return state

    def _find_hooks(self, content: str) -> List[str]:
        """Find React hooks used in component"""
        return list(set(self._hook_pattern.findall(content)))

    def _find_jsx_elements(self, content: str) -> List[str]:
        """Find JSX elements in component"""
        jsx_pattern = re.compile(r'<(\w+)[^>]*>')
        return list(set(jsx_pattern.findall(content)))

    def _find_dependencies(self, content: str) -> List[str]:
        """Find hook dependencies"""
        deps_pattern = re.compile(r'\[\s*([^\]]+)\s*\]')
        deps = []
        
        for match in deps_pattern.finditer(content):
            deps.extend(d.strip() for d in match.group(1).split(','))
        
        return [d for d in deps if d]

    def _determine_effect_type(self, content: str) -> Optional[str]:
        """Determine type of effect hook"""
        if 'componentDidMount' in content or '[]' in content:
            return "mount"
        elif 'componentDidUpdate' in content:
            return "update"
        elif 'return' in content and ('cleanup' in content or 'unmount' in content):
            return "cleanup"
        return None

    def _find_extends(self, content: str) -> Optional[List[str]]:
        """Find extended types/interfaces"""
        extends_pattern = re.compile(r'extends\s+([^{]+)')
        match = extends_pattern.search(content)
        if match:
            return [t.strip() for t in match.group(1).split(',')]
        return None

    def _find_implements(self, content: str) -> Optional[List[str]]:
        """Find implemented interfaces"""
        implements_pattern = re.compile(r'implements\s+([^{]+)')
        match = implements_pattern.search(content)
        if match:
            return [t.strip() for t in match.group(1).split(',')]
        return None

    def _create_code_blocks(
        self,
        content: str,
        components: List[ReactComponent],
        hooks: List[ReactHook]
    ) -> List[CodeBlock]:
        """Create code blocks from components and hooks"""
        blocks = []
        
        # Add component blocks
        for component in components:
            blocks.append(component.code_block)
        
        # Add hook blocks
        for hook in hooks:
            blocks.append(hook.code_block)
        
        return blocks

    def _categorize_imports(self, imports: List[JSImport]) -> Dict[str, ImportType]:
        """Categorize imports by type"""
        categorized = {}
        for imp in imports:
            for item in imp.items:
                categorized[item] = imp.import_type
        return categorized