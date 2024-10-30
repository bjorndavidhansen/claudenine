# claude_helper.toml

[cache]
enabled = true
path = "~/.cache/claude_helper"
ttl = 60  # minutes
max_size = 100  # MB

[analyzer]
max_file_size = 1048576  # 1MB
ignored_dirs = [".git", "__pycache__", "node_modules", "venv", ".env"]
ignored_files = [".DS_Store", "*.pyc", "*.pyo", "*.pyd", ".env"]
python_enabled = true
react_enabled = true

[claude]
model = "claude-3-5-sonnet-20241022"
max_tokens = 4096
temperature = 0.7
timeout = 30

debug = false