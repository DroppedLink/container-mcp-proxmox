#!/usr/bin/env python3
"""
Test MCP SSE with proper session handling
"""

import asyncio
import aiohttp
import json
import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def test_mcp_with_session():
    """Test the full MCP SSE flow with session ID"""
    print("🧪 Testing MCP SSE with Session ID...")
    
    # Build URL from environment variables
    host = os.getenv("MCP_SERVER_HOST", "localhost")
    port = os.getenv("MCP_SERVER_PORT", "8001")
    sse_url = f"http://{host}:{port}/sse"
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"📡 Step 1: Getting session ID from {sse_url}...")
            
            # Step 1: Get the session ID from SSE endpoint
            async with session.get(sse_url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache'
            }) as resp:
                print(f"Status: {resp.status}")
                
                session_id = None
                async for line in resp.content:
                    line_str = line.decode('utf-8').strip()
                    if line_str:
                        print(f"Received: {line_str}")
                        if "data: /messages/" in line_str:
                            # Extract session ID from the messages endpoint URL
                            match = re.search(r'session_id=([a-f0-9]+)', line_str)
                            if match:
                                session_id = match.group(1)
                                print(f"✅ Found session ID: {session_id}")
                                break
                
                if not session_id:
                    print("❌ Could not extract session ID")
                    return
            
            # Step 2: Use the session ID to send MCP messages
            messages_url = f"http://{host}:{port}/messages/?session_id={session_id}"
            
            print(f"\n📡 Step 2: Testing messages endpoint with session...")
            
            # Send initialize message
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
            
            async with session.post(messages_url,
                                   json=init_message,
                                   headers={'Content-Type': 'application/json'}) as resp:
                print(f"Initialize Status: {resp.status}")
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Initialize Response: {json.dumps(result, indent=2)}")
                    
                    # Step 3: Send initialized notification
                    initialized_message = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized"
                    }
                    
                    async with session.post(messages_url,
                                           json=initialized_message,
                                           headers={'Content-Type': 'application/json'}) as resp2:
                        print(f"Initialized Status: {resp2.status}")
                        
                        # Step 4: List tools
                        list_tools_message = {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/list"
                        }
                        
                        async with session.post(messages_url,
                                               json=list_tools_message,
                                               headers={'Content-Type': 'application/json'}) as resp3:
                            print(f"List Tools Status: {resp3.status}")
                            if resp3.status == 200:
                                tools_result = await resp3.json()
                                print(f"✅ Tools: {json.dumps(tools_result, indent=2)}")
                            else:
                                error_text = await resp3.text()
                                print(f"❌ Tools Error: {error_text}")
                else:
                    error_text = await resp.text()
                    print(f"❌ Initialize Error: {error_text}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_with_session()) 