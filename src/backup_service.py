"""
Backup and restore service.
"""
import logging
from typing import Dict, Any, List
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)

class BackupService(BaseProxmoxService):
    """Service for backup and restore operations."""
    
    def create_backup(self, vmid: str, node: str, storage: str = "local",
                     compress: str = "zstd", mode: str = "snapshot",
                     notes: str = "") -> Dict[str, Any]:
        """Create a backup of a VM or container."""
        try:
            config = {
                'vmid': vmid,
                'storage': storage,
                'compress': compress,
                'mode': mode
            }
            
            if notes:
                config['notes'] = notes
            
            task = self.proxmox.nodes(node).vzdump.create(**config)
            
            return {
                "status": "success", 
                "message": f"Backup of {vmid} initiated",
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Failed to create backup for {vmid}: {e}")
            raise
    
    def list_backups(self, node: str = "", storage: str = "") -> List[Dict[str, Any]]:
        """List available backups."""
        try:
            backups = []
            
            # If specific node provided, check only that node
            if node:
                nodes_to_check = [node]
            else:
                # Get all nodes
                nodes_list = self.proxmox.nodes.get()
                nodes_to_check = [n['node'] for n in nodes_list]
            
            for node_name in nodes_to_check:
                try:
                    # Get storage list for this node
                    if storage:
                        storages_to_check = [storage]
                    else:
                        storages = self.proxmox.nodes(node_name).storage.get()
                        storages_to_check = [s['storage'] for s in storages if s.get('content', '').find('backup') >= 0]
                    
                    for storage_name in storages_to_check:
                        try:
                            storage_backups = self.proxmox.nodes(node_name).storage(storage_name).content.get(content='backup')
                            for backup in storage_backups:
                                backups.append({
                                    'node': node_name,
                                    'storage': storage_name,
                                    'volid': backup['volid'],
                                    'size': backup.get('size', 0),
                                    'format': backup.get('format', 'unknown'),
                                    'ctime': backup.get('ctime', 0)
                                })
                        except Exception:
                            # Storage might not support backups or be unavailable
                            continue
                            
                except Exception:
                    # Node might be unavailable
                    continue
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            raise
    
    def restore_backup(self, archive: str, vmid: str, node: str,
                      storage: str = "", force: bool = False) -> Dict[str, Any]:
        """Restore a VM/container from backup."""
        try:
            config = {
                'archive': archive,
                'vmid': int(vmid)
            }
            
            if storage:
                config['storage'] = storage
            
            if force:
                config['force'] = 1
            
            # Determine if it's a VM or container backup based on archive name
            if 'qemu' in archive.lower():
                task = self.proxmox.nodes(node).qemu.create(**config)
            else:
                task = self.proxmox.nodes(node).lxc.create(**config)
            
            return {
                "status": "success",
                "message": f"Restore of {vmid} from {archive} initiated",
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Failed to restore backup {archive}: {e}")
            raise 