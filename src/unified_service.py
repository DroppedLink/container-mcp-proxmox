"""
Unified Proxmox service combining all domain-specific services.
"""
import logging
from typing import Dict, Any, List
from .base_service import BaseProxmoxService
from .vm_service import VMService
from .backup_service import BackupService
from .template_service import TemplateService
from .snapshot_service import SnapshotService
from .user_service import UserService
from .storage_service import StorageService

logger = logging.getLogger(__name__)

class ProxmoxService(BaseProxmoxService):
    """
    Unified Proxmox service that provides all functionality.
    This class inherits from the base service and delegates to domain-specific services.
    """
    
    def __init__(self, host: str, user: str, password: str, verify_ssl: bool = False):
        """Initialize all domain services with the same connection."""
        super().__init__(host, user, password, verify_ssl)
        
        # Initialize domain-specific services with shared connection
        self.vm_service = VMService(proxmox_api=self.proxmox)
        self.backup_service = BackupService(proxmox_api=self.proxmox)
        self.template_service = TemplateService(proxmox_api=self.proxmox)
        self.snapshot_service = SnapshotService(proxmox_api=self.proxmox)
        self.user_service = UserService(proxmox_api=self.proxmox)
        self.storage_service = StorageService(proxmox_api=self.proxmox)
    
    # Core functionality - async wrappers
    async def list_resources(self) -> Dict[str, Any]:
        """List all VMs and containers."""
        resources = super().list_resources()
        return {'resources': resources}
    
    async def get_resource_status(self, vmid: str, node: str) -> Dict[str, Any]:
        """Get detailed status of a VM or container."""
        return super().get_resource_status(vmid, node)
    
    # VM Management - async wrappers
    async def start_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Start a VM or container."""
        return self.vm_service.start_resource(vmid, node)
    
    async def stop_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Stop a VM or container."""
        return self.vm_service.stop_resource(vmid, node)
    
    async def shutdown_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Gracefully shutdown a VM or container."""
        return self.vm_service.shutdown_resource(vmid, node)
    
    async def restart_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Restart a VM or container."""
        return self.vm_service.restart_resource(vmid, node)
    
    async def create_vm(self, vmid: str, node: str, name: str, cores: int = 1, 
                  memory: int = 512, disk_size: str = "8G", 
                  iso_image: str = "", storage: str = "local-lvm",
                  os_type: str = "l26", start_after_create: bool = False) -> Dict[str, Any]:
        """Create a new VM."""
        return self.vm_service.create_vm(
            vmid, node, name, cores, memory, disk_size, 
            iso_image, storage, os_type, start_after_create
        )
    
    async def create_container(self, vmid: str, node: str, hostname: str, cores: int = 1,
                        memory: int = 512, rootfs_size: str = "8G",
                        storage: str = "local-lvm", template: str = "",
                        password: str = "", unprivileged: bool = True,
                        start_after_create: bool = False) -> Dict[str, Any]:
        """Create a new LXC container."""
        return self.vm_service.create_container(
            vmid, node, hostname, cores, memory, rootfs_size,
            storage, template, password, unprivileged, start_after_create
        )
    
    async def delete_resource(self, vmid: str, node: str, force: bool = False) -> Dict[str, Any]:
        """Delete a VM or container."""
        return self.vm_service.delete_resource(vmid, node, force)
    
    async def resize_resource(self, vmid: str, node: str, cores: int = 0, 
                       memory: int = 0, disk_size: str = "") -> Dict[str, Any]:
        """Resize VM/container resources."""
        return self.vm_service.resize_resource(vmid, node, cores, memory, disk_size)
    
    # Backup Management - async wrappers
    async def create_backup(self, vmid: str, node: str, storage: str = "local",
                     compress: str = "zstd", mode: str = "snapshot",
                     notes: str = "") -> Dict[str, Any]:
        """Create a backup of a VM or container."""
        return self.backup_service.create_backup(vmid, node, storage, compress, mode, notes)
    
    async def list_backups(self, node: str = "", storage: str = "") -> Dict[str, Any]:
        """List available backups."""
        backups = self.backup_service.list_backups(node, storage)
        return {'backups': backups}
    
    async def restore_backup(self, archive: str, vmid: str, node: str,
                      storage: str = "", force: bool = False) -> Dict[str, Any]:
        """Restore a VM/container from backup."""
        return self.backup_service.restore_backup(archive, vmid, node, storage, force)
    
    # Template Management - async wrappers
    async def create_template(self, vmid: str, node: str) -> Dict[str, Any]:
        """Convert a VM to a template."""
        return self.template_service.create_template(vmid, node)
    
    async def clone_vm(self, vmid: str, newid: str, node: str, name: str = "",
                 target_node: str = "", storage: str = "",
                 full_clone: bool = True) -> Dict[str, Any]:
        """Clone a VM or template."""
        return self.template_service.clone_vm(vmid, newid, node, name, target_node, storage, full_clone)
    
    async def list_templates(self) -> Dict[str, Any]:
        """List all VM templates in the cluster."""
        templates = self.template_service.list_templates()
        return {'templates': templates}
    
    # Snapshot Management - async wrappers
    async def create_snapshot(self, vmid: str, node: str, snapname: str,
                       description: str = "") -> Dict[str, Any]:
        """Create a snapshot of a VM."""
        return self.snapshot_service.create_snapshot(vmid, node, snapname, description)
    
    async def delete_snapshot(self, vmid: str, node: str, snapname: str) -> Dict[str, Any]:
        """Delete a snapshot of a VM."""
        return self.snapshot_service.delete_snapshot(vmid, node, snapname)
    
    async def get_snapshots(self, vmid: str, node: str) -> Dict[str, Any]:
        """List all snapshots for a VM."""
        snapshots = self.snapshot_service.get_snapshots(vmid, node)
        return {'snapshots': snapshots}
    
    # User Management - async wrappers
    async def create_user(self, userid: str, password: str = "", email: str = "",
                   firstname: str = "", lastname: str = "", groups: List[str] = None,
                   enable: bool = True) -> Dict[str, Any]:
        """Create a new Proxmox user."""
        # Convert groups list to string for the service
        groups_str = ','.join(groups) if groups else ""
        return self.user_service.create_user(userid, password, email, firstname, lastname, groups_str, enable)
    
    async def delete_user(self, userid: str) -> Dict[str, Any]:
        """Delete a Proxmox user."""
        return self.user_service.delete_user(userid)
    
    async def list_users(self) -> Dict[str, Any]:
        """List all Proxmox users."""
        users = self.user_service.list_users()
        return {'users': users}
    
    async def set_permissions(self, path: str, roleid: str, userid: str = "",
                       groupid: str = "", propagate: bool = True) -> Dict[str, Any]:
        """Set permissions for a user or group on a path."""
        return self.user_service.set_permissions(path, roleid, userid, groupid, propagate)
    
    async def list_roles(self) -> Dict[str, Any]:
        """List all available Proxmox roles."""
        roles = self.user_service.list_roles()
        return {'roles': roles}
    
    async def list_permissions(self) -> Dict[str, Any]:
        """List all ACL permissions."""
        permissions = self.user_service.list_permissions()
        return {'permissions': permissions}
    
    # Storage Management - async wrappers
    async def list_storage(self, node: str = "") -> Dict[str, Any]:
        """List all available storage across nodes or specific node."""
        storage_list = self.storage_service.list_storage(node)
        return {'storage': storage_list}
    
    async def get_storage_status(self, storage_name: str, node: str) -> Dict[str, Any]:
        """Get detailed status of a specific storage."""
        return self.storage_service.get_storage_status(storage_name, node)
    
    async def list_storage_content(self, storage_name: str, node: str, content_type: str = "") -> Dict[str, Any]:
        """List content in a specific storage."""
        content_list = self.storage_service.list_storage_content(storage_name, node, content_type)
        return {'content': content_list}
    
    async def get_suitable_storage(self, node: str, content_type: str, min_free_gb: float = 0) -> Dict[str, Any]:
        """Find storage suitable for specific content type with optional minimum free space."""
        suitable_storage = self.storage_service.get_suitable_storage(node, content_type, min_free_gb)
        return {'suitable_storage': suitable_storage}
    
    # Resource helper methods for compatibility
    async def _get_resource_type(self, vmid: str, node: str) -> str:
        """Helper to determine if resource is qemu or lxc."""
        try:
            self.proxmox.nodes(node).qemu(vmid).status.current.get()
            return 'qemu'
        except:
            try:
                self.proxmox.nodes(node).lxc(vmid).status.current.get()
                return 'lxc'
            except:
                raise ValueError(f"Resource {vmid} not found on node {node}")
    
    # Additional methods for compatibility
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status."""
        try:
            cluster_status = self.proxmox.cluster.status.get()
            return {'cluster_status': cluster_status}
        except Exception as e:
            logger.error(f"Failed to get cluster status: {e}")
            raise
    
    async def get_nodes_status(self) -> Dict[str, Any]:
        """Get nodes status."""
        try:
            nodes = self.proxmox.nodes.get()
            return {'nodes': nodes}
        except Exception as e:
            logger.error(f"Failed to get nodes status: {e}")
            raise 