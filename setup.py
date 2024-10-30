# setup.py

from setuptools import setup, find_packages

setup(
    name="claude_helper",
    version="0.1.0",
    description="A helper tool for code analysis using Claude AI",
    author="Your Name",
    packages=find_packages(),
    python_requires=">=3.8",  # For typing and async features
    install_requires=[
        'rich>=13.0.0',
        'anthropic>=0.3.0',
        'tomli>=2.0.0',
        'aiohttp>=3.8.0',  # For async HTTP requests
        'ast-analyzer>=0.1.0',  # For Python code analysis
        'tree-sitter>=0.20.0',  # For parsing various languages
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'black>=22.0.0',
            'isort>=5.0.0',
            'mypy>=1.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'claude-helper=claude_helper.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)