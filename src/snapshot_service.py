"""
Snapshot management service.
"""
import logging
from typing import Dict, Any, List
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)

class SnapshotService(BaseProxmoxService):
    """Service for snapshot operations."""
    
    def create_snapshot(self, vmid: str, node: str, snapname: str,
                       description: str = "") -> Dict[str, Any]:
        """Create a snapshot of a VM."""
        try:
            config = {
                'snapname': snapname
            }
            
            if description:
                config['description'] = description
            
            task = self.proxmox.nodes(node).qemu(vmid).snapshot.create(**config)
            
            return {
                "status": "success",
                "message": f"Snapshot '{snapname}' created for VM {vmid}",
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Failed to create snapshot for VM {vmid}: {e}")
            raise
    
    def delete_snapshot(self, vmid: str, node: str, snapname: str) -> Dict[str, Any]:
        """Delete a snapshot of a VM."""
        try:
            task = self.proxmox.nodes(node).qemu(vmid).snapshot(snapname).delete()
            
            return {
                "status": "success",
                "message": f"Snapshot '{snapname}' deleted from VM {vmid}",
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Failed to delete snapshot {snapname} from VM {vmid}: {e}")
            raise
    
    def get_snapshots(self, vmid: str, node: str) -> List[Dict[str, Any]]:
        """List all snapshots for a VM."""
        try:
            snapshots = self.proxmox.nodes(node).qemu(vmid).snapshot.get()
            
            formatted_snapshots = []
            for snap in snapshots:
                formatted_snapshots.append({
                    'name': snap['name'],
                    'description': snap.get('description', ''),
                    'snaptime': snap.get('snaptime', 0),
                    'parent': snap.get('parent', ''),
                    'vmstate': snap.get('vmstate', 0)
                })
            
            return formatted_snapshots
            
        except Exception as e:
            logger.error(f"Failed to get snapshots for VM {vmid}: {e}")
            raise 