#!/usr/bin/env python3
"""
Proxmox MCP Server - SSE Transport Only
A standards-compliant MCP server for managing Proxmox VE resources via Server-Sent Events
"""

import os
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Import our service
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.service import ProxmoxService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Proxmox MCP Server")

# Initialize service
service = ProxmoxService()

@mcp.tool()
async def list_resources() -> str:
    """List all VMs and containers in Proxmox cluster"""
    try:
        result = await service.list_resources()
        resources = result.get('resources', [])
        
        if not resources:
            return "No resources found in Proxmox cluster"
        
        output = f"Found {len(resources)} resources:\n\n"
        for r in resources:
            output += f"• **{r['name']}** (ID: {r['vmid']})\n"
            output += f"  - Status: {r['status']}\n"
            output += f"  - Node: {r['node']}\n"
            output += f"  - Type: {r.get('type', 'unknown')}\n"
            output += f"  - Uptime: {r.get('uptime', 'unknown')} seconds\n\n"
        
        return output
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        return f"❌ Error listing resources: {str(e)}"

@mcp.tool()
async def get_resource_status(vmid: str, node: str) -> str:
    """Get detailed status of a specific VM or container"""
    try:
        result = await service.get_resource_status(vmid, node)
        
        output = f"**Status for {vmid}:**\n\n"
        output += f"• Node: {result.get('node', 'Unknown')}\n"
        output += f"• Status: {result.get('status', 'Unknown')}\n"
        output += f"• CPU Usage: {result.get('cpu', 'Unknown')}\n"
        output += f"• Memory Usage: {result.get('memory', 'Unknown')}\n"
        output += f"• Disk Usage: {result.get('disk', 'Unknown')}\n"
        output += f"• Uptime: {result.get('uptime', 'Unknown')} seconds\n"
        
        return output
    except Exception as e:
        logger.error(f"Error getting status for {vmid}: {e}")
        return f"❌ Error getting status for {vmid}: {str(e)}"

@mcp.tool()
async def start_resource(vmid: str, node: str) -> str:
    """Start a VM or container"""
    try:
        result = await service.start_resource(vmid, node)
        return f"✅ Start command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error starting {vmid}: {e}")
        return f"❌ Error starting {vmid}: {str(e)}"

@mcp.tool()
async def stop_resource(vmid: str, node: str) -> str:
    """Stop a VM or container"""
    try:
        result = await service.stop_resource(vmid, node)
        return f"🛑 Stop command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error stopping {vmid}: {e}")
        return f"❌ Error stopping {vmid}: {str(e)}"

@mcp.tool()
async def shutdown_resource(vmid: str, node: str) -> str:
    """Gracefully shutdown a VM or container"""
    try:
        result = await service.shutdown_resource(vmid, node)
        return f"🔽 Shutdown command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error shutting down {vmid}: {e}")
        return f"❌ Error shutting down {vmid}: {str(e)}"

@mcp.tool()
async def restart_resource(vmid: str, node: str) -> str:
    """Restart a VM or container"""
    try:
        result = await service.restart_resource(vmid, node)
        return f"🔄 Restart command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error restarting {vmid}: {e}")
        return f"❌ Error restarting {vmid}: {str(e)}"

@mcp.tool()
async def create_snapshot(vmid: str, node: str, snapname: str, description: str = "") -> str:
    """Create a snapshot of a VM"""
    try:
        result = await service.create_snapshot(vmid, node, snapname, description)
        return f"📸 Snapshot '{snapname}' created for {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error creating snapshot for {vmid}: {e}")
        return f"❌ Error creating snapshot for {vmid}: {str(e)}"

@mcp.tool()
async def delete_snapshot(vmid: str, node: str, snapname: str) -> str:
    """Delete a snapshot of a VM"""
    try:
        result = await service.delete_snapshot(vmid, node, snapname)
        return f"🗑️ Snapshot '{snapname}' deleted from {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error deleting snapshot from {vmid}: {e}")
        return f"❌ Error deleting snapshot from {vmid}: {str(e)}"

@mcp.tool()
async def get_snapshots(vmid: str, node: str) -> str:
    """List all snapshots for a VM"""
    try:
        result = await service.get_snapshots(vmid, node)
        
        snapshots = result.get('snapshots', [])
        if not snapshots:
            return f"No snapshots found for {vmid}"
        
        output = f"**Snapshots for {vmid}:**\n\n"
        for snap in snapshots:
            output += f"• **{snap['name']}**\n"
            output += f"  - Description: {snap.get('description', 'No description')}\n"
            output += f"  - Date: {snap.get('snaptime', 'Unknown')}\n\n"
        
        return output
    except Exception as e:
        logger.error(f"Error getting snapshots for {vmid}: {e}")
        return f"❌ Error getting snapshots for {vmid}: {str(e)}"

@mcp.resource("proxmox://cluster/status")
async def cluster_status() -> str:
    """Get Proxmox cluster status"""
    try:
        result = await service.get_cluster_status()
        import json
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting cluster status: {e}")
        return f"Error getting cluster status: {str(e)}"

@mcp.resource("proxmox://nodes/status")
async def nodes_status() -> str:
    """Get Proxmox nodes status"""
    try:
        result = await service.get_nodes_status()
        import json
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting nodes status: {e}")
        return f"Error getting nodes status: {str(e)}"

async def test_connection():
    """Test Proxmox connection before starting server"""
    try:
        await service.test_connection()
        logger.info("✅ Proxmox connection successful")
    except Exception as e:
        logger.error(f"❌ Proxmox connection failed: {e}")
        logger.error("Please check your environment variables:")
        logger.error("  PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASSWORD")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    import asyncio
    
    # Parse command line arguments
    mount_path = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--mount-path" and i + 1 < len(sys.argv):
            mount_path = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] in ["--help", "-h"]:
            print("Proxmox MCP Server - SSE Transport")
            print("Usage: python simple_server.py [--mount-path PATH]")
            print()
            print("Options:")
            print("  --mount-path PATH  SSE mount path (optional)")
            print("  --help, -h         Show this help message")
            print()
            print("Environment variables required:")
            print("  PROXMOX_HOST       Proxmox VE host")
            print("  PROXMOX_USER       Proxmox VE username")
            print("  PROXMOX_PASSWORD   Proxmox VE password")
            print()
            print("Environment variables optional:")
            print("  MCP_PORT          Server port (default: 8000)")
            print("  MCP_HOST          Server host (default: localhost)")
            sys.exit(0)
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            sys.exit(1)
    
    # Get port from environment or use default
    port = os.getenv("MCP_PORT", "8000")
    host = os.getenv("MCP_HOST", "localhost")
    
    logger.info(f"🚀 Starting Proxmox MCP Server on {host}:{port}")
    logger.info("💡 Set MCP_PORT and MCP_HOST environment variables to customize")
    
    # Test connection first
    asyncio.run(test_connection())
    
    # Run the SSE server
    mcp.run(transport="sse", mount_path=mount_path) 