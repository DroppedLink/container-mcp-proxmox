#!/usr/bin/env python3
"""
Test MCP SSE protocol to debug Cursor IDE issues
"""

import asyncio
import aiohttp
import json
import os
import sys

async def test_mcp_sse():
    """Test the MCP SSE protocol like Cursor IDE would"""
    print("🧪 Testing MCP SSE Protocol...")
    
    url = os.getenv("MCP_SERVER_URL", "http://localhost:8001") + "/sse"
    
    # MCP initialization message
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {
                    "listChanged": True
                },
                "sampling": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"📡 Connecting to {url}...")
            
            # Test SSE connection
            async with session.get(url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache'
            }) as resp:
                print(f"✅ Connected! Status: {resp.status}")
                print(f"Headers: {dict(resp.headers)}")
                
                if resp.status == 200:
                    print("\n📨 Reading SSE stream...")
                    async for line in resp.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            print(f"Received: {line_str}")
                            # Only read a few lines to avoid hanging
                            if "data:" in line_str:
                                break
                else:
                    print(f"❌ Failed with status {resp.status}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_messages_endpoint():
    """Test the messages POST endpoint"""
    print("\n🧪 Testing Messages POST endpoint...")
    
                url = os.getenv("MCP_SERVER_URL", "http://localhost:8001") + "/messages"
    
    # MCP initialization message
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"📡 Posting to {url}...")
            
            async with session.post(url, 
                                   json=init_message,
                                   headers={'Content-Type': 'application/json'}) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Response: {json.dumps(result, indent=2)}")
                else:
                    text = await resp.text()
                    print(f"❌ Error response: {text}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 MCP SSE Debug Test\n")
    asyncio.run(test_mcp_sse())
    asyncio.run(test_messages_endpoint()) 