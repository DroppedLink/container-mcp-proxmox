# src/service.py

import os
import logging
import sys
from proxmoxer import ProxmoxAPI
from typing import List, Optional, Dict, Any

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import (
    ResourceIdentifier, CreateSnapshotParams, DeleteSnapshotParams, ProxmoxResource,
    ListResourcesResult, ResourceStatusResult, OperationStatus
)

class ProxmoxService:
    """Service class for Proxmox VE operations"""
    
    def __init__(self):
        self.proxmox_api = None
        
    def get_proxmox_api(self) -> ProxmoxAPI:
        """Initializes and returns a ProxmoxAPI client instance."""
        if self.proxmox_api is None:
            host = os.getenv("PROXMOX_HOST")
            user = os.getenv("PROXMOX_USER")
            password = os.getenv("PROXMOX_PASSWORD")
            verify_ssl = os.getenv("PROXMOX_VERIFY_SSL", "true").lower() == "true"

            logging.debug(f"Proxmox API - Host: {host}, User: {user}, Password Set: {bool(password)}, Verify SSL: {verify_ssl}")

            if not all([host, user, password]):
                logging.error("Proxmox API environment variables (PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASSWORD) are not fully set.")
                raise ValueError("Proxmox API environment variables are not fully set.")

            try:
                logging.debug(f"Attempting to initialize ProxmoxAPI with host={host}, user={user}, verify_ssl={verify_ssl}")
                self.proxmox_api = ProxmoxAPI(host, user=user, password=password, verify_ssl=verify_ssl)
                logging.debug("ProxmoxAPI object initialized successfully.")
            except Exception as e:
                logging.error(f"Error initializing ProxmoxAPI: {e}", exc_info=True)
                raise
                
        return self.proxmox_api

    async def test_connection(self) -> bool:
        """Test connection to Proxmox server"""
        try:
            proxmox = self.get_proxmox_api()
            # Try to get version to test connection
            version = proxmox.version.get()
            logging.info(f"Successfully connected to Proxmox VE {version.get('version', 'unknown')}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to Proxmox: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        self.proxmox_api = None
        logging.info("Proxmox service cleaned up")

    async def list_resources(self) -> Dict[str, Any]:
        """Lists all VMs and Containers in the cluster."""
        proxmox = self.get_proxmox_api()
        
        cluster_resources = proxmox.cluster.resources.get()
        
        processed_resources: List[Dict[str, Any]] = []
        for res_data in cluster_resources:
            if res_data.get('type') in ['qemu', 'lxc']:
                try:
                    resource = {
                        'vmid': str(res_data.get('vmid')),
                        'name': res_data.get('name', str(res_data.get('vmid'))),
                        'type': res_data.get('type'),
                        'status': res_data.get('status', 'unknown'),
                        'node': res_data.get('node'),
                        'uptime': res_data.get('uptime', 0)
                    }
                    processed_resources.append(resource)
                except Exception as e:
                    logging.error(f"Error processing resource {res_data.get('vmid')}: {e}")
                    continue

        return {'resources': processed_resources}

    async def get_resource_status(self, vmid: str, node: str) -> Dict[str, Any]:
        """Fetches detailed status and resource usage for a specific VM or CT."""
        proxmox = self.get_proxmox_api()
        node_api = proxmox.nodes(node)
        
        # Try to determine resource type by checking both qemu and lxc
        resource_type = None
        current_status = None
        
        try:
            # Try qemu first
            current_status = node_api.qemu(vmid).status.current.get()
            resource_type = 'qemu'
        except:
            try:
                # Try lxc
                current_status = node_api.lxc(vmid).status.current.get()
                resource_type = 'lxc'
            except Exception as e:
                raise ValueError(f"Resource {vmid} not found on node {node}")

        return {
            'vmid': current_status.get('vmid'),
            'name': current_status.get('name', str(current_status.get('vmid'))),
            'type': resource_type,
            'status': current_status.get('status'),
            'node': node,
            'uptime': current_status.get('uptime', 0),
            'cpu': current_status.get('cpu', 0),
            'memory': current_status.get('mem', 0),
            'disk': current_status.get('disk', 0)
        }

    async def start_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Starts a specific VM or Container."""
        proxmox = self.get_proxmox_api()
        node_api = proxmox.nodes(node)
        
        # Determine resource type
        resource_type = await self._get_resource_type(vmid, node)
        
        try:
            if resource_type == 'qemu':
                task_id = node_api.qemu(vmid).status.start.post()
            elif resource_type == 'lxc':
                task_id = node_api.lxc(vmid).status.start.post()
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")
                
            return {'status': 'pending', 'message': f'{resource_type.capitalize()} start task initiated.', 'task_id': task_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def stop_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Performs a hard power-off of a specific VM or stops a CT."""
        proxmox = self.get_proxmox_api()
        node_api = proxmox.nodes(node)
        
        resource_type = await self._get_resource_type(vmid, node)
        
        try:
            if resource_type == 'qemu':
                task_id = node_api.qemu(vmid).status.stop.post()
            elif resource_type == 'lxc':
                task_id = node_api.lxc(vmid).status.stop.post()
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

            return {'status': 'pending', 'message': f'{resource_type.capitalize()} stop task initiated.', 'task_id': task_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def shutdown_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Sends a graceful shutdown command to the guest OS of a VM or CT."""
        proxmox = self.get_proxmox_api()
        node_api = proxmox.nodes(node)
        
        resource_type = await self._get_resource_type(vmid, node)
        
        try:
            if resource_type == 'qemu':
                task_id = node_api.qemu(vmid).status.shutdown.post()
            elif resource_type == 'lxc':
                task_id = node_api.lxc(vmid).status.shutdown.post()
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

            return {'status': 'pending', 'message': f'{resource_type.capitalize()} shutdown task initiated.', 'task_id': task_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def restart_resource(self, vmid: str, node: str) -> Dict[str, Any]:
        """Restarts a specific VM or Container."""
        proxmox = self.get_proxmox_api()
        node_api = proxmox.nodes(node)
        
        resource_type = await self._get_resource_type(vmid, node)
        
        try:
            if resource_type == 'qemu':
                task_id = node_api.qemu(vmid).status.reboot.post()
            elif resource_type == 'lxc':
                task_id = node_api.lxc(vmid).status.reboot.post()
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

            return {'status': 'pending', 'message': f'{resource_type.capitalize()} restart task initiated.', 'task_id': task_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def create_snapshot(self, vmid: str, node: str, snapname: str, description: str = "") -> Dict[str, Any]:
        """Creates a new snapshot for a specific VM."""
        proxmox = self.get_proxmox_api()
        
        # Snapshots are typically for QEMU VMs
        snapshot_data = {'snapname': snapname}
        if description:
            snapshot_data['description'] = description
        
        try:
            task_id = proxmox.nodes(node).qemu(vmid).snapshot.post(**snapshot_data)
            return {'status': 'pending', 'message': 'Create snapshot task initiated.', 'task_id': task_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def delete_snapshot(self, vmid: str, node: str, snapname: str) -> Dict[str, Any]:
        """Removes a specific snapshot from a VM."""
        proxmox = self.get_proxmox_api()
        
        try:
            task_id = proxmox.nodes(node).qemu(vmid).snapshot(snapname).delete()
            return {'status': 'pending', 'message': 'Delete snapshot task initiated.', 'task_id': task_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def get_snapshots(self, vmid: str, node: str) -> Dict[str, Any]:
        """List all snapshots for a VM."""
        proxmox = self.get_proxmox_api()
        
        try:
            snapshots = proxmox.nodes(node).qemu(vmid).snapshot.get()
            processed_snapshots = []
            
            for snap in snapshots:
                processed_snapshots.append({
                    'name': snap.get('name'),
                    'description': snap.get('description', 'No description'),
                    'snaptime': snap.get('snaptime', 'Unknown'),
                    'vmstate': snap.get('vmstate', False)
                })
            
            return {'snapshots': processed_snapshots}
        except Exception as e:
            return {'snapshots': [], 'error': str(e)}

    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information."""
        proxmox = self.get_proxmox_api()
        
        try:
            status = proxmox.cluster.status.get()
            return {'cluster_status': status}
        except Exception as e:
            return {'error': str(e)}

    async def get_nodes_status(self) -> Dict[str, Any]:
        """Get status of all nodes."""
        proxmox = self.get_proxmox_api()
        
        try:
            nodes = proxmox.nodes.get()
            return {'nodes': nodes}
        except Exception as e:
            return {'error': str(e)}

    async def _get_resource_type(self, vmid: str, node: str) -> str:
        """Determine if a resource is qemu or lxc."""
        proxmox = self.get_proxmox_api()
        node_api = proxmox.nodes(node)
        
        try:
            # Try qemu first
            node_api.qemu(vmid).status.current.get()
            return 'qemu'
        except:
            try:
                # Try lxc
                node_api.lxc(vmid).status.current.get()
                return 'lxc'
            except:
                raise ValueError(f"Resource {vmid} not found on node {node}")