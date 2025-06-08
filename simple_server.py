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
from src.unified_service import ProxmoxService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Proxmox MCP Server")

# Initialize service after environment is loaded
service = None
_service_initialization_lock = None

async def get_service():
    """Get the service (with fallback lazy initialization if pre-init failed)."""
    global service, _service_initialization_lock
    
    if service is None:
        # Fallback lazy initialization if pre-initialization failed
        import asyncio
        if _service_initialization_lock is None:
            _service_initialization_lock = asyncio.Lock()
        
        async with _service_initialization_lock:
            # Double-check pattern
            if service is None:
                logger.warning("⚠️ Service not pre-initialized, initializing now...")
                await init_service()
    
    return service

@mcp.tool()
async def list_resources() -> str:
    """List all VMs and containers in Proxmox cluster"""
    try:
        result = await (await get_service()).list_resources()
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
        result = await (await get_service()).get_resource_status(vmid, node)
        
        # Helper function to format bytes to human readable
        def format_bytes(bytes_val):
            if not bytes_val or bytes_val == 0:
                return "0 B"
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.1f} PB"
        
        # Helper function to format CPU usage
        def format_cpu(cpu_val):
            if cpu_val is None or cpu_val == 'Unknown':
                return "Unknown"
            return f"{float(cpu_val) * 100:.2f}%"
        
        # Helper function to format memory usage
        def format_memory(mem_bytes, max_mem_bytes):
            if not mem_bytes or not max_mem_bytes:
                return "Unknown"
            mem_gb = mem_bytes / (1024**3)
            max_gb = max_mem_bytes / (1024**3)
            percentage = (mem_bytes / max_mem_bytes) * 100
            return f"{mem_gb:.1f} GB / {max_gb:.1f} GB ({percentage:.1f}%)"
        
        output = f"**Status for {vmid} ({result.get('name', 'Unknown')}):**\n\n"
        output += f"• Node: {node}\n"
        output += f"• Status: {result.get('status', 'Unknown')}\n"
        output += f"• Type: {result.get('type', 'qemu')}\n"
        output += f"• CPU Usage: {format_cpu(result.get('cpu'))}\n"
        output += f"• CPU Cores: {result.get('cpus', 'Unknown')}\n"
        
        # Format memory usage
        mem_usage = format_memory(result.get('mem'), result.get('maxmem'))
        output += f"• Memory Usage: {mem_usage}\n"
        
        # Format disk usage
        disk_bytes = result.get('disk', 0)
        output += f"• Disk Usage: {format_bytes(disk_bytes)}\n"
        
        # Format uptime
        uptime = result.get('uptime', 0)
        if uptime:
            days = uptime // 86400
            hours = (uptime % 86400) // 3600
            minutes = (uptime % 3600) // 60
            if days > 0:
                uptime_str = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                uptime_str = f"{hours}h {minutes}m"
            else:
                uptime_str = f"{minutes}m"
            output += f"• Uptime: {uptime_str} ({uptime} seconds)\n"
        else:
            output += f"• Uptime: Unknown\n"
        
        return output
    except Exception as e:
        logger.error(f"Error getting status for {vmid}: {e}")
        return f"❌ Error getting status for {vmid}: {str(e)}"

@mcp.tool()
async def start_resource(vmid: str, node: str) -> str:
    """Start a VM or container"""
    try:
        result = await (await get_service()).start_resource(vmid, node)
        return f"✅ Start command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error starting {vmid}: {e}")
        return f"❌ Error starting {vmid}: {str(e)}"

@mcp.tool()
async def stop_resource(vmid: str, node: str) -> str:
    """Stop a VM or container"""
    try:
        result = await (await get_service()).stop_resource(vmid, node)
        return f"🛑 Stop command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error stopping {vmid}: {e}")
        return f"❌ Error stopping {vmid}: {str(e)}"

@mcp.tool()
async def shutdown_resource(vmid: str, node: str) -> str:
    """Gracefully shutdown a VM or container"""
    try:
        result = await (await get_service()).shutdown_resource(vmid, node)
        return f"🔽 Shutdown command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error shutting down {vmid}: {e}")
        return f"❌ Error shutting down {vmid}: {str(e)}"

@mcp.tool()
async def restart_resource(vmid: str, node: str) -> str:
    """Restart a VM or container"""
    try:
        result = await (await get_service()).restart_resource(vmid, node)
        return f"🔄 Restart command sent to {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error restarting {vmid}: {e}")
        return f"❌ Error restarting {vmid}: {str(e)}"

@mcp.tool()
async def create_snapshot(vmid: str, node: str, snapname: str, description: str = "") -> str:
    """Create a snapshot of a VM"""
    try:
        result = await (await get_service()).create_snapshot(vmid, node, snapname, description)
        return f"📸 Snapshot '{snapname}' created for {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error creating snapshot for {vmid}: {e}")
        return f"❌ Error creating snapshot for {vmid}: {str(e)}"

@mcp.tool()
async def delete_snapshot(vmid: str, node: str, snapname: str) -> str:
    """Delete a snapshot of a VM"""
    try:
        result = await (await get_service()).delete_snapshot(vmid, node, snapname)
        return f"🗑️ Snapshot '{snapname}' deleted from {vmid}: {result.get('message', 'Success')}"
    except Exception as e:
        logger.error(f"Error deleting snapshot from {vmid}: {e}")
        return f"❌ Error deleting snapshot from {vmid}: {str(e)}"

@mcp.tool()
async def get_snapshots(vmid: str, node: str) -> str:
    """List all snapshots for a VM"""
    try:
        result = await (await get_service()).get_snapshots(vmid, node)
        
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
        result = await (await get_service()).get_cluster_status()
        import json
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting cluster status: {e}")
        return f"Error getting cluster status: {str(e)}"

@mcp.resource("proxmox://nodes/status")
async def nodes_status() -> str:
    """Get Proxmox nodes status"""
    try:
        result = await (await get_service()).get_nodes_status()
        import json
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting nodes status: {e}")
        return f"Error getting nodes status: {str(e)}"

async def init_service():
    """Initialize Proxmox service with environment variables."""
    global service
    
    proxmox_host = os.getenv('PROXMOX_HOST')
    proxmox_user = os.getenv('PROXMOX_USER') 
    proxmox_password = os.getenv('PROXMOX_PASSWORD')
    
    if not all([proxmox_host, proxmox_user, proxmox_password]):
        logger.error("❌ Missing required environment variables:")
        logger.error("  PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASSWORD")
        raise ValueError("Missing required environment variables")
    
    try:
        # Run service initialization in thread pool to avoid blocking event loop
        import asyncio
        import concurrent.futures
        
        def create_service():
            return ProxmoxService(proxmox_host, proxmox_user, proxmox_password)
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            service = await loop.run_in_executor(executor, create_service)
        
        logger.info("✅ Proxmox connection successful")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Proxmox: {e}")
        logger.error("Please check your environment variables and Proxmox server")
        raise

# === VM/CT Creation and Deletion Tools ===

@mcp.tool()
async def create_vm(vmid: str, node: str, name: str, cores: int = 1, memory: int = 512, 
                   disk_size: str = "8G", storage: str = "local-lvm", iso_image: str = "", 
                   os_type: str = "l26", start_after_create: bool = False) -> str:
    """Create a new VM"""
    try:
        iso = iso_image if iso_image else None
        result = await (await get_service()).create_vm(vmid, node, name, cores, memory, disk_size, 
                                       storage, iso, os_type, start_after_create)
        
        if result.get('status') == 'pending':
            return f"🚀 VM {vmid} ({name}) creation initiated on {node}\n" \
                   f"• Cores: {cores}\n• Memory: {memory}MB\n• Disk: {disk_size}\n" \
                   f"• Storage: {storage}\n• Task ID: {result.get('task_id')}"
        else:
            return f"❌ Error creating VM {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error creating VM {vmid}: {e}")
        return f"❌ Error creating VM {vmid}: {str(e)}"

@mcp.tool()
async def create_container(vmid: str, node: str, hostname: str, cores: int = 1, memory: int = 512,
                          rootfs_size: str = "8G", storage: str = "local-lvm", template: str = "",
                          password: str = "", unprivileged: bool = True, start_after_create: bool = False) -> str:
    """Create a new LXC container"""
    try:
        tpl = template if template else None
        pwd = password if password else None
        result = await (await get_service()).create_container(vmid, node, hostname, cores, memory, 
                                              rootfs_size, storage, tpl, pwd, unprivileged, start_after_create)
        
        if result.get('status') == 'pending':
            return f"📦 Container {vmid} ({hostname}) creation initiated on {node}\n" \
                   f"• Cores: {cores}\n• Memory: {memory}MB\n• RootFS: {rootfs_size}\n" \
                   f"• Storage: {storage}\n• Template: {template or 'None'}\n• Task ID: {result.get('task_id')}"
        else:
            return f"❌ Error creating container {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error creating container {vmid}: {e}")
        return f"❌ Error creating container {vmid}: {str(e)}"

@mcp.tool()
async def delete_resource(vmid: str, node: str, force: bool = False) -> str:
    """Delete a VM or container"""
    try:
        result = await (await get_service()).delete_resource(vmid, node, force)
        
        if result.get('status') == 'pending':
            force_text = " (forced)" if force else ""
            return f"🗑️ Deletion{force_text} initiated for {vmid} on {node}\n" \
                   f"• Task ID: {result.get('task_id')}"
        else:
            return f"❌ Error deleting {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error deleting {vmid}: {e}")
        return f"❌ Error deleting {vmid}: {str(e)}"

# === Resource Resizing Tools ===

@mcp.tool()
async def resize_resource(vmid: str, node: str, cores: int = 0, memory: int = 0, disk_size: str = "") -> str:
    """Resize VM/container resources (CPU, RAM, disk). Use 0 to skip a parameter."""
    try:
        cores_val = cores if cores > 0 else None
        memory_val = memory if memory > 0 else None
        disk_val = disk_size if disk_size else None
        
        if not any([cores_val, memory_val, disk_val]):
            return "❌ At least one resource parameter must be specified (cores > 0, memory > 0, or disk_size)"
        
        result = await (await get_service()).resize_resource(vmid, node, cores_val, memory_val, disk_val)
        
        if result.get('status') == 'pending':
            changes = []
            if cores_val:
                changes.append(f"CPU: {cores_val} cores")
            if memory_val:
                changes.append(f"RAM: {memory_val}MB")
            if disk_val:
                changes.append(f"Disk: {disk_val}")
                
            return f"📏 Resource resize initiated for {vmid} on {node}\n" \
                   f"• Changes: {', '.join(changes)}\n" \
                   f"• Message: {result.get('message')}"
        else:
            return f"❌ Error resizing {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error resizing {vmid}: {e}")
        return f"❌ Error resizing {vmid}: {str(e)}"

# === Backup and Restore Tools ===

@mcp.tool()
async def create_backup(vmid: str, node: str, storage: str = "local", mode: str = "snapshot", 
                       compress: str = "zstd", notes: str = "") -> str:
    """Create a backup of a VM or container"""
    try:
        result = await (await get_service()).create_backup(vmid, node, storage, mode, compress, notes)
        
        if result.get('status') == 'pending':
            return f"💾 Backup initiated for {vmid} on {node}\n" \
                   f"• Storage: {storage}\n• Mode: {mode}\n• Compression: {compress}\n" \
                   f"• Notes: {notes or 'None'}\n• Task ID: {result.get('task_id')}"
        else:
            return f"❌ Error creating backup for {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error creating backup for {vmid}: {e}")
        return f"❌ Error creating backup for {vmid}: {str(e)}"

@mcp.tool()
async def list_backups(node: str = "", storage: str = "") -> str:
    """List available backups"""
    try:
        node_val = node if node else None
        storage_val = storage if storage else None
        result = await (await get_service()).list_backups(node_val, storage_val)
        
        backups = result.get('backups', [])
        if not backups:
            return "No backups found"
        
        output = f"**Available Backups:**\n\n"
        for backup in backups:
            output += f"• **{backup.get('volid', 'Unknown')}**\n"
            output += f"  - Size: {backup.get('size', 'Unknown')}\n"
            output += f"  - Format: {backup.get('format', 'Unknown')}\n"
            output += f"  - Created: {backup.get('ctime', 'Unknown')}\n\n"
        
        return output
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        return f"❌ Error listing backups: {str(e)}"

@mcp.tool()
async def restore_backup(archive: str, vmid: str, node: str, storage: str = "", force: bool = False) -> str:
    """Restore a VM/container from backup"""
    try:
        storage_val = storage if storage else None
        result = await (await get_service()).restore_backup(archive, vmid, node, storage_val, force)
        
        if result.get('status') == 'pending':
            force_text = " (forced)" if force else ""
            return f"🔄 Restore{force_text} initiated for {vmid} on {node}\n" \
                   f"• Archive: {archive}\n• Storage: {storage or 'Default'}\n" \
                   f"• Task ID: {result.get('task_id')}"
        else:
            return f"❌ Error restoring {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error restoring {vmid}: {e}")
        return f"❌ Error restoring {vmid}: {str(e)}"

# === Template and Clone Tools ===

@mcp.tool()
async def create_template(vmid: str, node: str) -> str:
    """Convert a VM to a template"""
    try:
        result = await (await get_service()).create_template(vmid, node)
        
        if result.get('status') == 'pending':
            return f"📄 Template creation initiated for VM {vmid} on {node}\n" \
                   f"• Task ID: {result.get('task_id')}"
        else:
            return f"❌ Error creating template from {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error creating template from {vmid}: {e}")
        return f"❌ Error creating template from {vmid}: {str(e)}"

@mcp.tool()
async def clone_vm(vmid: str, newid: str, node: str, name: str = "", target_node: str = "",
                  full_clone: bool = True, storage: str = "") -> str:
    """Clone a VM or template"""
    try:
        name_val = name if name else None
        target_val = target_node if target_node else None
        storage_val = storage if storage else None
        
        result = await (await get_service()).clone_vm(vmid, newid, node, name_val, target_val, full_clone, storage_val)
        
        if result.get('status') == 'pending':
            clone_type = "Full clone" if full_clone else "Linked clone"
            return f"👥 {clone_type} initiated: {vmid} → {newid}\n" \
                   f"• Source node: {node}\n• Target node: {target_node or node}\n" \
                   f"• New name: {name or 'Same as source'}\n• Task ID: {result.get('task_id')}"
        else:
            return f"❌ Error cloning {vmid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error cloning {vmid}: {e}")
        return f"❌ Error cloning {vmid}: {str(e)}"

@mcp.tool()
async def list_templates() -> str:
    """List all VM templates and LXC container templates in the cluster"""
    try:
        result = await (await get_service()).list_templates()
        
        templates = result.get('templates', [])
        if not templates:
            return "No templates found"
        
        # Separate VM and LXC templates
        vm_templates = [t for t in templates if t.get('type') == 'vm']
        lxc_templates = [t for t in templates if t.get('type') == 'lxc']
        
        output = f"**Available Templates ({len(templates)} total):**\n\n"
        
        if vm_templates:
            output += f"**VM Templates ({len(vm_templates)}):**\n"
            for template in vm_templates:
                output += f"• **{template['name']}** (ID: {template['vmid']})\n"
                output += f"  - Node: {template['node']}\n"
                output += f"  - Type: VM Template\n"
                output += f"  - Description: {template.get('description', 'None')}\n\n"
        
        if lxc_templates:
            output += f"**LXC Container Templates ({len(lxc_templates)}):**\n"
            for template in lxc_templates:
                # Format size
                size_mb = template.get('size', 0) / (1024 * 1024)
                output += f"• **{template['name']}**\n"
                output += f"  - Node: {template['node']}\n"
                output += f"  - Type: LXC Template\n"
                output += f"  - Storage: {template.get('storage', 'Unknown')}\n"
                output += f"  - Size: {size_mb:.1f} MB\n"
                output += f"  - Volume ID: {template.get('volid', 'Unknown')}\n"
                output += f"  - Description: {template.get('description', 'None')}\n\n"
        
        return output
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return f"❌ Error listing templates: {str(e)}"

# === User and Role Management Tools ===

@mcp.tool()
async def create_user(userid: str, password: str = "", email: str = "", firstname: str = "",
                     lastname: str = "", groups: str = "", enable: bool = True) -> str:
    """Create a new Proxmox user"""
    try:
        pwd = password if password else None
        email_val = email if email else None
        first_val = firstname if firstname else None
        last_val = lastname if lastname else None
        groups_list = groups.split(',') if groups else None
        
        result = await (await get_service()).create_user(userid, pwd, email_val, first_val, last_val, groups_list, enable)
        
        if result.get('status') == 'success':
            return f"👤 User created successfully: {userid}\n" \
                   f"• Email: {email or 'None'}\n• Groups: {groups or 'None'}\n" \
                   f"• Enabled: {'Yes' if enable else 'No'}"
        else:
            return f"❌ Error creating user {userid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error creating user {userid}: {e}")
        return f"❌ Error creating user {userid}: {str(e)}"

@mcp.tool()
async def delete_user(userid: str) -> str:
    """Delete a Proxmox user"""
    try:
        result = await (await get_service()).delete_user(userid)
        
        if result.get('status') == 'success':
            return f"🗑️ User deleted successfully: {userid}"
        else:
            return f"❌ Error deleting user {userid}: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error deleting user {userid}: {e}")
        return f"❌ Error deleting user {userid}: {str(e)}"

@mcp.tool()
async def list_users() -> str:
    """List all Proxmox users"""
    try:
        result = await (await get_service()).list_users()
        
        users = result.get('users', [])
        if not users:
            return "No users found"
        
        output = f"**Proxmox Users:**\n\n"
        for user in users:
            output += f"• **{user.get('userid', 'Unknown')}**\n"
            output += f"  - Enabled: {'Yes' if user.get('enable', 1) else 'No'}\n"
            output += f"  - Email: {user.get('email', 'None')}\n"
            output += f"  - Groups: {user.get('groups', 'None')}\n\n"
        
        return output
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return f"❌ Error listing users: {str(e)}"

@mcp.tool()
async def set_permissions(path: str, roleid: str, userid: str = "", groupid: str = "", 
                         propagate: bool = True) -> str:
    """Set permissions for a user or group on a path"""
    try:
        user_val = userid if userid else None
        group_val = groupid if groupid else None
        
        if not user_val and not group_val:
            return "❌ Either userid or groupid must be specified"
        
        result = await (await get_service()).set_permissions(path, roleid, user_val, group_val, propagate)
        
        if result.get('status') == 'success':
            target = userid or groupid
            return f"🔐 Permissions set successfully for {target}\n" \
                   f"• Path: {path}\n• Role: {roleid}\n• Propagate: {'Yes' if propagate else 'No'}"
        else:
            return f"❌ Error setting permissions: {result.get('message')}"
    except Exception as e:
        logger.error(f"Error setting permissions: {e}")
        return f"❌ Error setting permissions: {str(e)}"

@mcp.tool()
async def list_roles() -> str:
    """List all available Proxmox roles"""
    try:
        result = await (await get_service()).list_roles()
        
        roles = result.get('roles', [])
        if not roles:
            return "No roles found"
        
        output = f"**Available Roles:**\n\n"
        for role in roles:
            role_name = role.get('roleid', 'Unknown')
            output += f"• **{role_name}**\n"
            if role.get('privs'):
                output += f"  - Privileges: {role.get('privs')}\n"
            output += "\n"
        
        return output
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        return f"❌ Error listing roles: {str(e)}"

@mcp.tool()
async def list_permissions() -> str:
    """List all ACL permissions"""
    try:
        result = await (await get_service()).list_permissions()
        
        permissions = result.get('permissions', [])
        if not permissions:
            return "No permissions found"
        
        output = f"**Current Permissions:**\n\n"
        for perm in permissions:
            output += f"• **Path:** {perm.get('path', 'Unknown')}\n"
            output += f"  - Type: {perm.get('type', 'Unknown')}\n"
            output += f"  - User/Group: {perm.get('ugid', 'Unknown')}\n"
            output += f"  - Role: {perm.get('roleid', 'Unknown')}\n"
            output += f"  - Propagate: {'Yes' if perm.get('propagate') else 'No'}\n\n"
        
        return output
    except Exception as e:
        logger.error(f"Error listing permissions: {e}")
        return f"❌ Error listing permissions: {str(e)}"


# === Storage Management Tools ===

@mcp.tool()
async def list_storage(node: str = "") -> str:
    """List all available storage across nodes or specific node"""
    try:
        result = await (await get_service()).list_storage(node)
        storage_list = result.get('storage', [])
        
        if not storage_list:
            return "💾 No storage found"
        
        output = [f"💾 **Storage Overview** {f'(Node: {node})' if node else '(All Nodes)'}", ""]
        
        # Group by node
        nodes = {}
        for storage in storage_list:
            node_name = storage['node']
            if node_name not in nodes:
                nodes[node_name] = []
            nodes[node_name].append(storage)
        
        for node_name, storages in nodes.items():
            output.append(f"🖥️ **Node: {node_name}**")
            for storage in storages:
                name = storage['storage']
                storage_type = storage['type']
                enabled = "✅" if storage['enabled'] else "❌"
                active = "🟢" if storage['active'] else "🔴"
                shared = "🔗" if storage['shared'] else "📁"
                
                # Storage capacity info
                if storage.get('total_gb', 0) > 0:
                    usage = f"{storage['used_gb']:.1f}GB / {storage['total_gb']:.1f}GB ({storage['usage_percent']:.1f}%)"
                    avail = f"{storage['avail_gb']:.1f}GB available"
                else:
                    usage = "No capacity info"
                    avail = ""
                
                content_types = ", ".join(storage.get('content_types', []))
                
                output.append(f"  📦 **{name}** ({storage_type}) {enabled} {active} {shared}")
                output.append(f"      💾 {usage}")
                if avail:
                    output.append(f"      🆓 {avail}")
                output.append(f"      📂 Content: {content_types}")
                output.append("")
            output.append("")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error listing storage: {e}")
        return f"❌ Error listing storage: {str(e)}"


@mcp.tool()
async def get_storage_status(storage_name: str, node: str) -> str:
    """Get detailed status of a specific storage"""
    try:
        result = await (await get_service()).get_storage_status(storage_name, node)
        
        name = result['storage']
        storage_type = result['type']
        enabled = "✅ Enabled" if result['enabled'] else "❌ Disabled"
        active = "🟢 Active" if result.get('active', False) else "🔴 Inactive"
        shared = "🔗 Shared" if result['shared'] else "📁 Local"
        
        output = [f"💾 **Storage: {name}** (Node: {node})", ""]
        output.append(f"📋 **Basic Info**")
        output.append(f"   Type: {storage_type}")
        output.append(f"   Status: {enabled}, {active}")
        output.append(f"   Scope: {shared}")
        output.append("")
        
        # Capacity information
        if result.get('total_gb', 0) > 0:
            output.append(f"💾 **Capacity**")
            output.append(f"   Total: {result['total_gb']:.2f} GB")
            output.append(f"   Used: {result['used_gb']:.2f} GB ({result['usage_percent']:.1f}%)")
            output.append(f"   Available: {result['avail_gb']:.2f} GB")
            output.append("")
        
        # Content types
        content_types = result.get('content_types', [])
        if content_types:
            output.append(f"📂 **Supported Content Types**")
            output.append(f"   {', '.join(content_types)}")
            output.append("")
        
        # Type-specific configuration
        if storage_type == 'dir' and result.get('path'):
            output.append(f"📁 **Directory Config**")
            output.append(f"   Path: {result['path']}")
        elif storage_type == 'nfs' and result.get('server'):
            output.append(f"🌐 **NFS Config**")
            output.append(f"   Server: {result['server']}")
            output.append(f"   Export: {result.get('export', '')}")
        elif storage_type == 'cifs' and result.get('server'):
            output.append(f"🌐 **CIFS Config**")
            output.append(f"   Server: {result['server']}")
            output.append(f"   Share: {result.get('share', '')}")
        elif storage_type in ['lvm', 'lvmthin'] and result.get('vgname'):
            output.append(f"💿 **LVM Config**")
            output.append(f"   Volume Group: {result['vgname']}")
            if result.get('thinpool'):
                output.append(f"   Thin Pool: {result['thinpool']}")
        elif storage_type == 'zfspool' and result.get('pool'):
            output.append(f"🏊 **ZFS Config**")
            output.append(f"   Pool: {result['pool']}")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error getting storage status for {storage_name}: {e}")
        return f"❌ Error getting storage status: {str(e)}"


@mcp.tool()
async def list_storage_content(storage_name: str, node: str, content_type: str = "") -> str:
    """List content in a specific storage"""
    try:
        result = await (await get_service()).list_storage_content(storage_name, node, content_type)
        content_list = result.get('content', [])
        
        if not content_list:
            filter_text = f" (filtered by: {content_type})" if content_type else ""
            return f"📦 No content found in storage '{storage_name}'{filter_text}"
        
        filter_text = f" - {content_type.upper()}" if content_type else ""
        output = [f"📦 **Storage Content: {storage_name}**{filter_text} (Node: {node})", ""]
        
        # Group by content type
        content_groups = {}
        for item in content_list:
            ctype = item['content']
            if ctype not in content_groups:
                content_groups[ctype] = []
            content_groups[ctype].append(item)
        
        for ctype, items in content_groups.items():
            icon = {
                'images': '💿',
                'iso': '📀',
                'vztmpl': '📦',
                'backup': '💾',
                'snippets': '📝'
            }.get(ctype, '📄')
            
            output.append(f"{icon} **{ctype.upper()}** ({len(items)} items)")
            for item in items:
                filename = item.get('filename', item['volid'])
                size = item.get('size_human', '0 B')
                vmid = item.get('vmid')
                
                if vmid:
                    output.append(f"   📄 {filename} ({size}) - VM/CT: {vmid}")
                else:
                    output.append(f"   📄 {filename} ({size})")
            output.append("")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error listing storage content for {storage_name}: {e}")
        return f"❌ Error listing storage content: {str(e)}"


@mcp.tool()
async def get_suitable_storage(node: str, content_type: str, min_free_gb: float = 0) -> str:
    """Find storage suitable for specific content type with optional minimum free space"""
    try:
        result = await (await get_service()).get_suitable_storage(node, content_type, min_free_gb)
        suitable_storage = result.get('suitable_storage', [])
        
        if not suitable_storage:
            min_text = f" with at least {min_free_gb}GB free" if min_free_gb > 0 else ""
            return f"❌ No suitable storage found for '{content_type}' on node '{node}'{min_text}"
        
        min_text = f" (min {min_free_gb}GB free)" if min_free_gb > 0 else ""
        output = [f"💾 **Suitable Storage for '{content_type}'** on {node}{min_text}", ""]
        
        for i, storage in enumerate(suitable_storage, 1):
            name = storage['storage']
            storage_type = storage['type']
            avail = storage['avail_gb']
            usage = storage['usage_percent']
            shared = "🔗 Shared" if storage['shared'] else "📁 Local"
            
            # Recommendation based on available space and usage
            if i == 1:
                rec = "🌟 **RECOMMENDED**"
            elif usage < 80:
                rec = "✅ Good choice"
            elif usage < 90:
                rec = "⚠️ Nearly full"
            else:
                rec = "🔴 Almost no space"
            
            output.append(f"{i}. **{name}** ({storage_type}) {shared}")
            output.append(f"   💾 Available: {avail:.1f}GB (Usage: {usage:.1f}%)")
            output.append(f"   {rec}")
            output.append("")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error finding suitable storage: {e}")
        return f"❌ Error finding suitable storage: {str(e)}"

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
    
    # Pre-initialize service to avoid MCP protocol race condition
    logger.info("🔄 Initializing Proxmox service...")
    try:
        # Use asyncio to pre-initialize the service
        import asyncio
        asyncio.run(init_service())
        logger.info("✅ Service pre-initialized successfully")
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        logger.error("The server will start but tools may not work until service initializes")
    
    # Run the SSE server
    mcp.run(transport="sse", mount_path=mount_path) 