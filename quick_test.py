#!/usr/bin/env python3
"""
Quick test for the Proxmox MCP Server (SSE-only)
"""

import asyncio
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def test_sse_server(host=None, port=None):
    """Test the SSE MCP server connectivity"""
    # Use environment variables if not provided
    if host is None:
        host = os.getenv("MCP_SERVER_HOST", "localhost")
    if port is None:
        port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    
    print(f"🧪 Testing Proxmox MCP Server at {host}:{port}...\n")
    
    try:
        # Try to import aiohttp for testing
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Test basic connectivity
            print("📡 Testing server connectivity...")
            try:
                # Test the SSE endpoint which should respond
                async with session.get(f"http://{host}:{port}/sse") as resp:
                    if resp.status == 200:
                        print("✅ Server is responding!")
                        print(f"   Status: {resp.status}")
                        print(f"   Content-Type: {resp.headers.get('content-type', 'unknown')}")
                        return True
                    else:
                        print(f"⚠️  Server returned status {resp.status}")
                        return False
            except aiohttp.ClientConnectorError:
                print(f"❌ Cannot connect to server at {host}:{port}")
                print("   Make sure the server is running:")
                print(f"   python simple_server.py --host {host} --port {port}")
                return False
                
    except ImportError:
        print("⚠️  aiohttp not available for HTTP testing")
        print("📝 To test the server manually:")
        print(f"   1. Start server: python simple_server.py --port {port}")
        print(f"   2. Check: curl http://{host}:{port}")
        print("   3. Configure in Cursor IDE MCP settings")
        return None

async def test_proxmox_connection():
    """Test if Proxmox environment variables are set"""
    print("🔧 Checking Proxmox configuration...")
    
    required_vars = ["PROXMOX_HOST", "PROXMOX_USER", "PROXMOX_PASSWORD"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * 8}...")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Create a .env file with:")
        for var in missing_vars:
            print(f"   {var}=your-value")
        return False
    
    print("✅ All environment variables are set")
    return True

async def main():
    """Main test function"""
    print("🚀 Proxmox MCP Server Test Suite\n")
    print("=" * 50)
    
    # Check environment
    env_ok = await test_proxmox_connection()
    print()
    
    # Test server if environment is OK
    if env_ok:
        print("=" * 50)
        server_ok = await test_sse_server()
        print()
        
        if server_ok:
            print("=" * 50)
            print("🎉 SUCCESS: Your Proxmox MCP Server is ready!")
            print("\n🔧 Available Tools:")
            print("  Core Management:")
            core_tools = [
                "list_resources - List all VMs and containers",
                "get_resource_status - Get VM/container details",
                "start_resource - Start a VM/container",
                "stop_resource - Stop a VM/container", 
                "shutdown_resource - Gracefully shutdown",
                "restart_resource - Restart a VM/container"
            ]
            for tool in core_tools:
                print(f"    • {tool}")
                
            print("  Creation & Deletion:")
            creation_tools = [
                "create_vm - Create new VMs",
                "create_container - Create new containers", 
                "delete_resource - Delete VMs/containers"
            ]
            for tool in creation_tools:
                print(f"    • {tool}")
                
            print("  Resource Management:")
            resource_tools = [
                "resize_resource - Resize CPU/RAM/disk"
            ]
            for tool in resource_tools:
                print(f"    • {tool}")
                
            print("  Backup & Restore:")
            backup_tools = [
                "create_backup - Create backups",
                "list_backups - List available backups",
                "restore_backup - Restore from backup"
            ]
            for tool in backup_tools:
                print(f"    • {tool}")
                
            print("  Templates & Cloning:")
            template_tools = [
                "create_template - Convert VM to template",
                "clone_vm - Clone VMs/templates",
                "list_templates - List available templates"
            ]
            for tool in template_tools:
                print(f"    • {tool}")
                
            print("  Snapshots:")
            snapshot_tools = [
                "create_snapshot - Create VM snapshot",
                "delete_snapshot - Delete VM snapshot",
                "get_snapshots - List VM snapshots"
            ]
            for tool in snapshot_tools:
                print(f"    • {tool}")
                
            print("  User Management:")
            user_tools = [
                "create_user - Create new users",
                "delete_user - Delete users",
                "list_users - List all users",
                "set_permissions - Set user permissions",
                "list_roles - List available roles",
                "list_permissions - List current permissions"
            ]
            for tool in user_tools:
                print(f"    • {tool}")
                
            print("\n📚 Available Resources:")
            resources = [
                "proxmox://cluster/status - Cluster information",
                "proxmox://nodes/status - Node status"
            ]
            for resource in resources:
                print(f"  • {resource}")
                
            print("\n🎯 Next Steps:")
            print("  1. Keep the server running:")
            print("     python simple_server.py --port 8001")
            print("  2. Configure in Cursor IDE MCP settings:")
            print("     URL: http://localhost:8001")
            print("     Transport: SSE")
            
        elif server_ok is False:
            print("=" * 50)
            print("❌ Server test failed")
            print("🔧 Troubleshooting:")
            print("  1. Start the server first:")
            print("     python simple_server.py")
            print("  2. Check if port 8001 is available")
            print("  3. Check server logs for errors")
        else:
            print("=" * 50) 
            print("⚠️  Could not test server connectivity")
            print("📝 Manual testing steps:")
            print("  1. Start: python simple_server.py")
            print("  2. Test: curl http://localhost:8001")
            print("  3. Configure in Cursor IDE")
    else:
        print("🔧 Please fix environment configuration first")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1) 