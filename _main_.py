# claude_helper/__main__.py

import asyncio
from .cli import main

if __name__ == "__main__":
    asyncio.run(main())