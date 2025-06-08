"""
VM and Container management service.
"""
import logging
from typing import Dict, Any
from .base_service import BaseProxmoxService
from .config import (
    DEFAULT_VM_CORES, DEFAULT_VM_MEMORY, DEFAULT_VM_DISK_SIZE, DEFAULT_VM_OS_TYPE,
    DEFAULT_SCSI_HARDWARE, DEFAULT_VM_NETWORK, DEFAULT_CONTAINER_CORES,
    DEFAULT_CONTAINER_MEMORY, DEFAULT_CONTAINER_ROOTFS_SIZE, DEFAULT_CONTAINER_NETWORK,
    get_default_storage, PREFER_SHARED_STORAGE, ALLOW_LOCAL_STORAGE
)

logger = logging.getLogger(__name__)

class VMService(BaseProxmoxService):
    """Service for VM and Container lifecycle management."""
    
    def start_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Start a VM or container."""
        try:
            # Try as VM first
            try:
                self.proxmox.nodes(node).qemu(vmid).status.start.post()
                return {"status": "success", "message": f"VM {vmid} start initiated"}
            except:
                # Try as container
                self.proxmox.nodes(node).lxc(vmid).status.start.post()
                return {"status": "success", "message": f"Container {vmid} start initiated"}
                
        except Exception as e:
            logger.error(f"Failed to start {vmid}: {e}")
            raise
    
    def stop_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Stop a VM or container."""
        try:
            # Try as VM first
            try:
                self.proxmox.nodes(node).qemu(vmid).status.stop.post()
                return {"status": "success", "message": f"VM {vmid} stop initiated"}
            except:
                # Try as container
                self.proxmox.nodes(node).lxc(vmid).status.stop.post()
                return {"status": "success", "message": f"Container {vmid} stop initiated"}
                
        except Exception as e:
            logger.error(f"Failed to stop {vmid}: {e}")
            raise
    
    def shutdown_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Gracefully shutdown a VM or container."""
        try:
            # Try as VM first
            try:
                self.proxmox.nodes(node).qemu(vmid).status.shutdown.post()
                return {"status": "success", "message": f"VM {vmid} shutdown initiated"}
            except:
                # Try as container
                self.proxmox.nodes(node).lxc(vmid).status.shutdown.post()
                return {"status": "success", "message": f"Container {vmid} shutdown initiated"}
                
        except Exception as e:
            logger.error(f"Failed to shutdown {vmid}: {e}")
            raise
    
    def restart_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Restart a VM or container."""
        try:
            # Try as VM first
            try:
                self.proxmox.nodes(node).qemu(vmid).status.reboot.post()
                return {"status": "success", "message": f"VM {vmid} restart initiated"}
            except:
                # Try as container
                self.proxmox.nodes(node).lxc(vmid).status.reboot.post()
                return {"status": "success", "message": f"Container {vmid} restart initiated"}
                
        except Exception as e:
            logger.error(f"Failed to restart {vmid}: {e}")
            raise
    
    def create_vm(self, vmid: str, node: str, name: str, cores: int = None, 
                  memory: int = None, disk_size: str = None, 
                  iso_image: str = "", storage: str = None,
                  os_type: str = None, start_after_create: bool = False) -> Dict[str, Any]:
        """Create a new VM."""
        try:
            # Use defaults from config if not specified
            cores = cores or DEFAULT_VM_CORES
            memory = memory or DEFAULT_VM_MEMORY
            disk_size = disk_size or DEFAULT_VM_DISK_SIZE
            os_type = os_type or DEFAULT_VM_OS_TYPE
            
            # Auto-detect storage if not specified
            if not storage:
                storage = get_default_storage()
                if not storage:
                    # Auto-detect suitable storage (preferring shared storage)
                    try:
                        from .storage_service import StorageService
                        storage_service = StorageService(self.proxmox)
                        suitable_storages = storage_service.get_suitable_storage(node, "images", min_free_gb=1)
                        if suitable_storages:
                            storage = suitable_storages[0]['storage']
                            storage_type = "shared" if suitable_storages[0]['shared'] else "local"
                            logger.info(f"Auto-selected {storage_type} storage '{storage}' for VM {vmid} on {node}")
                        else:
                            storage = "local-lvm"  # Ultimate fallback
                            logger.warning(f"No suitable storage found for VM {vmid}, using fallback: {storage}")
                    except Exception as e:
                        storage = "local-lvm"  # Ultimate fallback
                        logger.warning(f"Storage auto-detection failed for VM {vmid}: {e}, using fallback: {storage}")
            
            # Determine the correct disk format based on storage type
            disk_format = "raw"  # Default for LVM, ZFS, etc.
            try:
                # Get storage info to determine the best format
                storage_info = self.proxmox.nodes(node).storage(storage).get()
                storage_type = storage_info.get('type', 'unknown')
                
                # Use appropriate format based on storage type
                if storage_type in ['dir', 'nfs', 'cifs']:
                    disk_format = "qcow2"  # These support qcow2
                else:
                    disk_format = "raw"    # LVM, ZFS, etc. use raw
            except Exception:
                # If we can't determine, use raw (safer default)
                disk_format = "raw"
            
            config = {
                'vmid': int(vmid),
                'name': name,
                'cores': cores,
                'memory': memory,
                'ostype': os_type,
                'scsihw': DEFAULT_SCSI_HARDWARE,
                'scsi0': f'{storage}:{disk_size},format={disk_format}',
                'net0': DEFAULT_VM_NETWORK
            }
            
            if iso_image:
                config['cdrom'] = iso_image
            
            # Create VM
            task = self.proxmox.nodes(node).qemu.create(**config)
            
            if start_after_create:
                # Wait a moment then start
                import time
                time.sleep(2)
                self.start_resource(vmid, node)
            
            return {"status": "success", "message": f"VM {vmid} created successfully", "task": task}
            
        except Exception as e:
            logger.error(f"Failed to create VM {vmid}: {e}")
            raise
    
    def create_container(self, vmid: str, node: str, hostname: str, cores: int = None,
                        memory: int = None, rootfs_size: str = None,
                        storage: str = None, template: str = "",
                        password: str = "", unprivileged: bool = True,
                        start_after_create: bool = False) -> Dict[str, Any]:
        """Create a new LXC container."""
        try:
            # Use defaults from config if not specified
            cores = cores or DEFAULT_CONTAINER_CORES
            memory = memory or DEFAULT_CONTAINER_MEMORY
            rootfs_size = rootfs_size or DEFAULT_CONTAINER_ROOTFS_SIZE
            
            # Auto-detect storage if not specified
            if not storage:
                storage = get_default_storage()
                if not storage:
                    # Auto-detect suitable storage (preferring shared storage)
                    try:
                        from .storage_service import StorageService
                        storage_service = StorageService(self.proxmox)
                        suitable_storages = storage_service.get_suitable_storage(node, "rootdir", min_free_gb=1)
                        if suitable_storages:
                            storage = suitable_storages[0]['storage']
                            storage_type = "shared" if suitable_storages[0]['shared'] else "local"
                            logger.info(f"Auto-selected {storage_type} storage '{storage}' for container {vmid} on {node}")
                        else:
                            storage = "local-lvm"  # Ultimate fallback
                            logger.warning(f"No suitable storage found for container {vmid}, using fallback: {storage}")
                    except Exception as e:
                        storage = "local-lvm"  # Ultimate fallback
                        logger.warning(f"Storage auto-detection failed for container {vmid}: {e}, using fallback: {storage}")
            
            config = {
                'vmid': int(vmid),
                'hostname': hostname,
                'cores': cores,
                'memory': memory,
                'rootfs': f'{storage}:{rootfs_size}',
                'net0': DEFAULT_CONTAINER_NETWORK,
                'unprivileged': 1 if unprivileged else 0
            }
            
            if template:
                config['ostemplate'] = template
            
            if password:
                config['password'] = password
            
            # Create container
            task = self.proxmox.nodes(node).lxc.create(**config)
            
            if start_after_create:
                # Wait a moment then start
                import time
                time.sleep(2)
                self.start_resource(vmid, node)
            
            return {"status": "success", "message": f"Container {vmid} created successfully", "task": task}
            
        except Exception as e:
            logger.error(f"Failed to create container {vmid}: {e}")
            raise
    
    def delete_resource(self, vmid: str, node: str, force: bool = False) -> Dict[str, Any]:
        """Delete a VM or container."""
        try:
            params = {}
            if force:
                params['force'] = 1
            
            # Try as VM first
            try:
                task = self.proxmox.nodes(node).qemu(vmid).delete(**params)
                return {"status": "success", "message": f"VM {vmid} deletion initiated", "task": task}
            except:
                # Try as container
                task = self.proxmox.nodes(node).lxc(vmid).delete(**params)
                return {"status": "success", "message": f"Container {vmid} deletion initiated", "task": task}
                
        except Exception as e:
            logger.error(f"Failed to delete {vmid}: {e}")
            raise
    
    def resize_resource(self, vmid: str, node: str, cores: int = 0, 
                       memory: int = 0, disk_size: str = "") -> Dict[str, Any]:
        """Resize VM/container resources."""
        try:
            # Try as VM first
            try:
                config = {}
                if cores > 0:
                    config['cores'] = cores
                if memory > 0:
                    config['memory'] = memory
                if disk_size:
                    # For VMs, we need to resize the disk differently
                    self.proxmox.nodes(node).qemu(vmid).resize.put(disk='scsi0', size=disk_size)
                
                if config:
                    self.proxmox.nodes(node).qemu(vmid).config.put(**config)
                
                return {"status": "success", "message": f"VM {vmid} resized successfully"}
                
            except:
                # Try as container
                config = {}
                if cores > 0:
                    config['cores'] = cores
                if memory > 0:
                    config['memory'] = memory
                if disk_size:
                    # Try to detect storage or use default
                    default_storage = get_default_storage() or "local-lvm"
                    config['rootfs'] = f"{default_storage}:{disk_size}"
                
                if config:
                    self.proxmox.nodes(node).lxc(vmid).config.put(**config)
                
                return {"status": "success", "message": f"Container {vmid} resized successfully"}
                
        except Exception as e:
            logger.error(f"Failed to resize {vmid}: {e}")
            raise 