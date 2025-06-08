#!/usr/bin/env python3
"""
Proxmox MCP Server - Lower-Level MCP SDK Implementation
A standards-compliant MCP server for managing Proxmox VE resources using the lower-level MCP SDK
"""

import os
import sys
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dotenv import load_dotenv
from typing import Any

# MCP imports
import mcp.types as types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport

# Load environment variables
load_dotenv()

# Import our service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.service import ProxmoxService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Server lifespan context manager
@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """Manage server startup and shutdown lifecycle."""
    # Initialize Proxmox service on startup
    service = ProxmoxService()
    
    # Test connection
    try:
        await service.test_connection()
        logger.info("✅ Proxmox connection successful")
    except Exception as e:
        logger.error(f"❌ Proxmox connection failed: {e}")
        logger.error("Please check your environment variables:")
        logger.error("  PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASSWORD")
        raise
    
    try:
        yield {"service": service}
    finally:
        # Clean up on shutdown
        logger.info("🔽 Shutting down Proxmox MCP Server")

# Create server instance
server = Server("Proxmox MCP Server", lifespan=server_lifespan)

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return list of available tools"""
    return [
        types.Tool(
            name="list_resources",
            description="List all VMs and containers in Proxmox cluster",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_resource_status",
            description="Get detailed status of a specific VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM/Container ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    }
                },
                "required": ["vmid", "node"]
            }
        ),
        types.Tool(
            name="start_resource",
            description="Start a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM/Container ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    }
                },
                "required": ["vmid", "node"]
            }
        ),
        types.Tool(
            name="stop_resource",
            description="Stop a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM/Container ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    }
                },
                "required": ["vmid", "node"]
            }
        ),
        types.Tool(
            name="shutdown_resource",
            description="Gracefully shutdown a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM/Container ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    }
                },
                "required": ["vmid", "node"]
            }
        ),
        types.Tool(
            name="restart_resource",
            description="Restart a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM/Container ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    }
                },
                "required": ["vmid", "node"]
            }
        ),
        types.Tool(
            name="create_snapshot",
            description="Create a snapshot of a VM",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    },
                    "snapname": {
                        "type": "string",
                        "description": "Snapshot name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Snapshot description",
                        "default": ""
                    }
                },
                "required": ["vmid", "node", "snapname"]
            }
        ),
        types.Tool(
            name="delete_snapshot",
            description="Delete a snapshot of a VM",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    },
                    "snapname": {
                        "type": "string",
                        "description": "Snapshot name"
                    }
                },
                "required": ["vmid", "node", "snapname"]
            }
        ),
        types.Tool(
            name="get_snapshots",
            description="List all snapshots for a VM",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {
                        "type": "string",
                        "description": "VM ID"
                    },
                    "node": {
                        "type": "string",
                        "description": "Proxmox node name"
                    }
                },
                "required": ["vmid", "node"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Handle tool calls"""
    # Get service from lifespan context
    ctx = server.request_context
    service = ctx.lifespan_context["service"]
    
    if arguments is None:
        arguments = {}
    
    try:
        if name == "list_resources":
            result = await service.list_resources()
            resources = result.get('resources', [])
            
            if not resources:
                output = "No resources found in Proxmox cluster"
            else:
                output = f"Found {len(resources)} resources:\n\n"
                for r in resources:
                    output += f"• **{r['name']}** (ID: {r['vmid']})\n"
                    output += f"  - Status: {r['status']}\n"
                    output += f"  - Node: {r['node']}\n"
                    output += f"  - Type: {r.get('type', 'unknown')}\n"
                    output += f"  - Uptime: {r.get('uptime', 'unknown')} seconds\n\n"
            
            return [types.TextContent(type="text", text=output)]
        
        elif name == "get_resource_status":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            
            if not vmid or not node:
                return [types.TextContent(type="text", text="❌ Error: vmid and node are required")]
            
            result = await service.get_resource_status(vmid, node)
            
            output = f"**Status for {vmid}:**\n\n"
            output += f"• Node: {result.get('node', 'Unknown')}\n"
            output += f"• Status: {result.get('status', 'Unknown')}\n"
            output += f"• CPU Usage: {result.get('cpu', 'Unknown')}\n"
            output += f"• Memory Usage: {result.get('memory', 'Unknown')}\n"
            output += f"• Disk Usage: {result.get('disk', 'Unknown')}\n"
            output += f"• Uptime: {result.get('uptime', 'Unknown')} seconds\n"
            
            return [types.TextContent(type="text", text=output)]
        
        elif name == "start_resource":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            
            if not vmid or not node:
                return [types.TextContent(type="text", text="❌ Error: vmid and node are required")]
            
            result = await service.start_resource(vmid, node)
            return [types.TextContent(type="text", text=f"✅ Start command sent to {vmid}: {result.get('message', 'Success')}")]
        
        elif name == "stop_resource":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            
            if not vmid or not node:
                return [types.TextContent(type="text", text="❌ Error: vmid and node are required")]
            
            result = await service.stop_resource(vmid, node)
            return [types.TextContent(type="text", text=f"🛑 Stop command sent to {vmid}: {result.get('message', 'Success')}")]
        
        elif name == "shutdown_resource":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            
            if not vmid or not node:
                return [types.TextContent(type="text", text="❌ Error: vmid and node are required")]
            
            result = await service.shutdown_resource(vmid, node)
            return [types.TextContent(type="text", text=f"🔽 Shutdown command sent to {vmid}: {result.get('message', 'Success')}")]
        
        elif name == "restart_resource":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            
            if not vmid or not node:
                return [types.TextContent(type="text", text="❌ Error: vmid and node are required")]
            
            result = await service.restart_resource(vmid, node)
            return [types.TextContent(type="text", text=f"🔄 Restart command sent to {vmid}: {result.get('message', 'Success')}")]
        
        elif name == "create_snapshot":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            snapname = arguments.get("snapname")
            description = arguments.get("description", "")
            
            if not vmid or not node or not snapname:
                return [types.TextContent(type="text", text="❌ Error: vmid, node, and snapname are required")]
            
            result = await service.create_snapshot(vmid, node, snapname, description)
            return [types.TextContent(type="text", text=f"📸 Snapshot '{snapname}' created for {vmid}: {result.get('message', 'Success')}")]
        
        elif name == "delete_snapshot":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            snapname = arguments.get("snapname")
            
            if not vmid or not node or not snapname:
                return [types.TextContent(type="text", text="❌ Error: vmid, node, and snapname are required")]
            
            result = await service.delete_snapshot(vmid, node, snapname)
            return [types.TextContent(type="text", text=f"🗑️ Snapshot '{snapname}' deleted from {vmid}: {result.get('message', 'Success')}")]
        
        elif name == "get_snapshots":
            vmid = arguments.get("vmid")
            node = arguments.get("node")
            
            if not vmid or not node:
                return [types.TextContent(type="text", text="❌ Error: vmid and node are required")]
            
            result = await service.get_snapshots(vmid, node)
            
            snapshots = result.get('snapshots', [])
            if not snapshots:
                output = f"No snapshots found for {vmid}"
            else:
                output = f"**Snapshots for {vmid}:**\n\n"
                for snap in snapshots:
                    output += f"• **{snap['name']}**\n"
                    output += f"  - Description: {snap.get('description', 'No description')}\n"
                    output += f"  - Date: {snap.get('snaptime', 'Unknown')}\n\n"
            
            return [types.TextContent(type="text", text=output)]
        
        else:
            return [types.TextContent(type="text", text=f"❌ Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(type="text", text=f"❌ Error executing {name}: {str(e)}")]

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """Return list of available resources"""
    return [
        types.Resource(
            uri="proxmox://cluster/status",
            name="Cluster Status",
            description="Get Proxmox cluster status",
            mimeType="application/json"
        ),
        types.Resource(
            uri="proxmox://nodes/status",
            name="Nodes Status", 
            description="Get Proxmox nodes status",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reading"""
    # Get service from lifespan context
    ctx = server.request_context
    service = ctx.lifespan_context["service"]
    
    try:
        if uri == "proxmox://cluster/status":
            result = await service.get_cluster_status()
            return json.dumps(result, indent=2)
        elif uri == "proxmox://nodes/status":
            result = await service.get_nodes_status()
            return json.dumps(result, indent=2)
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        raise

async def run_sse_server():
    """Run the SSE server"""
    # Get configuration from environment
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))
    
    logger.info(f"🚀 Starting Proxmox MCP Server (Lower-Level SDK) on {host}:{port}")
    
    # Create initialization options
    init_options = InitializationOptions(
        server_name="Proxmox MCP Server",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
        )
    )
    
    # Create SSE transport
    sse_transport = SseServerTransport("/messages")
    
    async def handle_sse(request):
        from starlette.responses import Response
        async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], init_options)
        return Response()
    
    async def handle_messages(request):
        from starlette.responses import Response
        await sse_transport.handle_post_message(request.scope, request.receive, request._send)
        return Response()
    
    # Health check endpoint
    async def health_check(request):
        from starlette.responses import JSONResponse
        response = {
            "status": "ok",
            "server": "proxmox-mcp-server",
            "transport": "sse",
            "version": "1.0.0"
        }
        return JSONResponse(response)
    
    from starlette.applications import Starlette
    from starlette.routing import Route
    
    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
            Route("/health", endpoint=health_check, methods=["GET"]),
        ]
    )
    
    import uvicorn
    config = uvicorn.Config(
        starlette_app,
        host=host,
        port=port,
        log_level="info"
    )
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("Proxmox MCP Server - Lower-Level MCP SDK")
        print("Usage: python lowlevel_server.py")
        print()
        print("Environment variables required:")
        print("  PROXMOX_HOST       Proxmox VE host")
        print("  PROXMOX_USER       Proxmox VE username")
        print("  PROXMOX_PASSWORD   Proxmox VE password")
        print()
        print("Environment variables optional:")
        print("  MCP_PORT          Server port (default: 8001)")
        print("  MCP_HOST          Server host (default: 0.0.0.0)")
        sys.exit(0)
    
    # Run the SSE server
    try:
        asyncio.run(run_sse_server())
    except KeyboardInterrupt:
        logger.info("🔽 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1) 