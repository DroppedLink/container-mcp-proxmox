#!/usr/bin/env python3
"""
Standards-compliant MCP Proxmox server using official Python SDK
"""

import asyncio
import logging
import os
import json
import sys
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route

# Import service and models
from .service import ProxmoxService
from .models import CreateSnapshotParams, DeleteSnapshotParams

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create MCP server instance
app = Server("proxmox-mcp-server")

# Global service instance
proxmox_service = None

@asynccontextmanager
async def server_lifespan(server: Server):
    """Manage server startup and shutdown lifecycle"""
    global proxmox_service
    
    # Initialize Proxmox service on startup
    logger.info("Initializing Proxmox service...")
    proxmox_service = ProxmoxService()
    
    # Test connection
    try:
        await proxmox_service.test_connection()
        logger.info("Proxmox connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Proxmox: {e}")
        # Continue anyway, let individual operations handle errors
    
    try:
        yield {"proxmox": proxmox_service}
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Proxmox service...")
        if proxmox_service:
            await proxmox_service.cleanup()

# Set lifespan manager
app._lifespan = server_lifespan

@app.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available Proxmox management tools"""
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
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"}
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
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"}
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
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"}
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
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"}
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
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"}
                },
                "required": ["vmid", "node"]
            }
        ),
        types.Tool(
            name="create_snapshot",
            description="Create a snapshot of a VM or container",
            inputSchema={
                "type": "object", 
                "properties": {
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"},
                    "snapname": {"type": "string", "description": "Snapshot name"},
                    "description": {"type": "string", "description": "Snapshot description", "default": ""}
                },
                "required": ["vmid", "node", "snapname"]
            }
        ),
        types.Tool(
            name="delete_snapshot",
            description="Delete a snapshot of a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"},
                    "snapname": {"type": "string", "description": "Snapshot name to delete"}
                },
                "required": ["vmid", "node", "snapname"]
            }
        ),
        types.Tool(
            name="get_snapshots",
            description="List all snapshots for a VM or container",
            inputSchema={
                "type": "object",
                "properties": {
                    "vmid": {"type": "string", "description": "VM/Container ID"},
                    "node": {"type": "string", "description": "Proxmox node name"}
                },
                "required": ["vmid", "node"]
            }
        )
    ]

@app.call_tool()
async def call_tool(
    name: str, 
    arguments: Dict[str, Any]
) -> List[types.TextContent]:
    """Handle tool execution"""
    global proxmox_service
    
    if not proxmox_service:
        return [types.TextContent(
            type="text",
            text="Proxmox service not initialized"
        )]
    
    try:
        logger.info(f"Executing tool: {name} with arguments: {arguments}")
        
        if name == "list_resources":
            result = await proxmox_service.list_resources()
            resources = result.get('resources', [])
            
            if not resources:
                return [types.TextContent(
                    type="text",
                    text="No resources found in Proxmox cluster"
                )]
            
            output = f"Found {len(resources)} resources:\n\n"
            for r in resources:
                output += f"• **{r['name']}** (ID: {r['vmid']})\n"
                output += f"  - Status: {r['status']}\n"
                output += f"  - Node: {r['node']}\n"
                output += f"  - Type: {r.get('type', 'unknown')}\n"
                output += f"  - Uptime: {r.get('uptime', 'unknown')} seconds\n\n"
            
            return [types.TextContent(type="text", text=output)]
            
        elif name == "get_resource_status":
            vmid = arguments["vmid"]
            node = arguments["node"]
            result = await proxmox_service.get_resource_status(vmid, node)
            
            output = f"**Status for {vmid}:**\n\n"
            output += f"• Node: {result.get('node', 'Unknown')}\n"
            output += f"• Status: {result.get('status', 'Unknown')}\n"
            output += f"• CPU Usage: {result.get('cpu', 'Unknown')}\n"
            output += f"• Memory Usage: {result.get('memory', 'Unknown')}\n"
            output += f"• Disk Usage: {result.get('disk', 'Unknown')}\n"
            output += f"• Uptime: {result.get('uptime', 'Unknown')} seconds\n"
            
            return [types.TextContent(type="text", text=output)]
            
        elif name == "start_resource":
            vmid = arguments["vmid"]
            node = arguments["node"]
            result = await proxmox_service.start_resource(vmid, node)
            return [types.TextContent(
                type="text",
                text=f"✅ Start command sent to {vmid}: {result.get('message', 'Success')}"
            )]
            
        elif name == "stop_resource":
            vmid = arguments["vmid"]
            node = arguments["node"]
            result = await proxmox_service.stop_resource(vmid, node)
            return [types.TextContent(
                type="text",
                text=f"🛑 Stop command sent to {vmid}: {result.get('message', 'Success')}"
            )]
            
        elif name == "shutdown_resource":
            vmid = arguments["vmid"]
            node = arguments["node"]
            result = await proxmox_service.shutdown_resource(vmid, node)
            return [types.TextContent(
                type="text",
                text=f"🔽 Shutdown command sent to {vmid}: {result.get('message', 'Success')}"
            )]
            
        elif name == "restart_resource":
            vmid = arguments["vmid"]
            node = arguments["node"]
            result = await proxmox_service.restart_resource(vmid, node)
            return [types.TextContent(
                type="text",
                text=f"🔄 Restart command sent to {vmid}: {result.get('message', 'Success')}"
            )]
            
        elif name == "create_snapshot":
            vmid = arguments["vmid"]
            node = arguments["node"]
            snapname = arguments["snapname"]
            description = arguments.get("description", "")
            
            result = await proxmox_service.create_snapshot(vmid, node, snapname, description)
            return [types.TextContent(
                type="text",
                text=f"📸 Snapshot '{snapname}' created for {vmid}: {result.get('message', 'Success')}"
            )]
            
        elif name == "delete_snapshot":
            vmid = arguments["vmid"]
            node = arguments["node"]
            snapname = arguments["snapname"]
            
            result = await proxmox_service.delete_snapshot(vmid, node, snapname)
            return [types.TextContent(
                type="text",
                text=f"🗑️ Snapshot '{snapname}' deleted from {vmid}: {result.get('message', 'Success')}"
            )]
            
        elif name == "get_snapshots":
            vmid = arguments["vmid"]
            node = arguments["node"]
            result = await proxmox_service.get_snapshots(vmid, node)
            
            snapshots = result.get('snapshots', [])
            if not snapshots:
                return [types.TextContent(
                    type="text",
                    text=f"No snapshots found for {vmid}"
                )]
            
            output = f"**Snapshots for {vmid}:**\n\n"
            for snap in snapshots:
                output += f"• **{snap['name']}**\n"
                output += f"  - Description: {snap.get('description', 'No description')}\n"
                output += f"  - Date: {snap.get('snaptime', 'Unknown')}\n\n"
            
            return [types.TextContent(type="text", text=output)]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ Error executing {name}: {str(e)}"
        )]

@app.list_resources()
async def list_resources() -> List[types.Resource]:
    """List available Proxmox resources"""
    return [
        types.Resource(
            uri="proxmox://cluster/status",
            name="Cluster Status",
            description="Real-time Proxmox cluster status and health information",
            mimeType="application/json"
        ),
        types.Resource(
            uri="proxmox://nodes/status",
            name="Node Status",
            description="Status and resource usage of all Proxmox nodes",
            mimeType="application/json"
        ),
        types.Resource(
            uri="proxmox://cluster/resources",
            name="All Resources",
            description="Complete list of all VMs and containers",
            mimeType="application/json"
        )
    ]

@app.read_resource()
async def read_resource(uri: types.AnyUrl) -> str:
    """Read resource content"""
    global proxmox_service
    
    if not proxmox_service:
        return "Proxmox service not initialized"
    
    uri_str = str(uri)
    logger.info(f"Reading resource: {uri_str}")
    
    try:
        if uri_str == "proxmox://cluster/status":
            status = await proxmox_service.get_cluster_status()
            return json.dumps(status, indent=2)
            
        elif uri_str == "proxmox://nodes/status":
            nodes = await proxmox_service.get_nodes_status()
            return json.dumps(nodes, indent=2)
            
        elif uri_str == "proxmox://cluster/resources":
            result = await proxmox_service.list_resources()
            return json.dumps(result, indent=2)
            
        else:
            raise ValueError(f"Unknown resource: {uri}")
            
    except Exception as e:
        logger.error(f"Resource read error: {e}")
        return f"Error reading resource {uri}: {str(e)}"

# Transport implementations

async def run_stdio():
    """Run server with STDIO transport (for CLI clients)"""
    logger.info("Starting MCP server with STDIO transport")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

async def run_sse(host: str = "0.0.0.0", port: int = 8001):
    """Run server with SSE transport (for web clients like Cursor)"""
    logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
    
    sse_transport = SseServerTransport("/messages")
    
    async def handle_sse(scope, receive, send):
        async with sse_transport.connect_sse(scope, receive, send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    
    async def handle_messages(scope, receive, send):
        await sse_transport.handle_post_message(scope, receive, send)
    
    # Health check endpoint
    async def health_check(scope, receive, send):
        response = {
            "status": "ok",
            "server": "proxmox-mcp-server",
            "transport": "sse",
            "version": "1.0.0"
        }
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
                [b'access-control-allow-origin', b'*'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': json.dumps(response).encode(),
        })
    
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
    server = uvicorn.Server(config)
    await server.serve()

# Main execution
async def main():
    """Main entry point"""
    import sys
    
    # Parse command line arguments
    transport = "stdio"  # default
    host = "0.0.0.0"
    port = 8001
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--transport" and i + 1 < len(sys.argv):
            transport = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--host" and i + 1 < len(sys.argv):
            host = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    logger.info(f"Starting Proxmox MCP Server with transport: {transport}")
    
    if transport == "sse":
        await run_sse(host, port)
    else:
        await run_stdio()

if __name__ == "__main__":
    asyncio.run(main()) 