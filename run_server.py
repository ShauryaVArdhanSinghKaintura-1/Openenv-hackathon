#!/usr/bin/env python
"""Direct server runner without uvicorn -m issues."""
import sys
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.app:app",
        host="127.0.0.1",
        port=7860,
        reload=False
    )
