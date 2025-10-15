#!/usr/bin/env python3
"""
Entry point for running the FastAPI server.
"""

import uvicorn
from backend.utils.config import Config

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.server:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )
