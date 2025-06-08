#!/usr/bin/env python3
"""
Proxmox MCP Server Entry Point
A standards-compliant MCP server for managing Proxmox VE resources
"""

import asyncio
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.mcp_server import main

if __name__ == "__main__":
    asyncio.run(main()) 