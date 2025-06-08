"""
Base Proxmox service with core connection functionality.
"""
import logging
from typing import Dict, Any, List
from proxmoxer import ProxmoxAPI

logger = logging.getLogger(__name__)

class BaseProxmoxService:
    """Base service class for Proxmox operations with core connection functionality."""
    
    def __init__(self, host: str = None, user: str = None, password: str = None, verify_ssl: bool = False, proxmox_api=None):
        """Initialize Proxmox connection or use existing one."""
        if proxmox_api:
            # Use existing connection
            self.proxmox = proxmox_api
            self.host = None
            self.user = None
            self.password = None
            self.verify_ssl = verify_ssl
        else:
            # Create new connection
            self.host = host
            self.user = user
            self.password = password
            self.verify_ssl = verify_ssl
            self.proxmox = None
            self.connect()
    
    def connect(self):
        """Establish connection to Proxmox VE."""
        try:
            self.proxmox = ProxmoxAPI(
                self.host,
                user=self.user,
                password=self.password,
                verify_ssl=self.verify_ssl
            )
            
            # Test connection
            version = self.proxmox.version.get()
            logger.info(f"Successfully connected to Proxmox VE {version['version']}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox: {e}")
            raise
    
    def list_resources(self) -> List[Dict[str, Any]]:
        """List all VMs and containers."""
        try:
            resources = []
            
            # Get all nodes
            nodes = self.proxmox.nodes.get()
            
            for node in nodes:
                node_name = node['node']
                
                # Get VMs (QEMU)
                vms = self.proxmox.nodes(node_name).qemu.get()
                for vm in vms:
                    resources.append({
                        'vmid': vm['vmid'],
                        'name': vm.get('name', f"VM-{vm['vmid']}"),
                        'status': vm['status'],
                        'node': node_name,
                        'type': 'qemu',
                        'uptime': vm.get('uptime', 0)
                    })
                
                # Get Containers (LXC)
                containers = self.proxmox.nodes(node_name).lxc.get()
                for container in containers:
                    resources.append({
                        'vmid': container['vmid'],
                        'name': container.get('name', f"CT-{container['vmid']}"),
                        'status': container['status'],
                        'node': node_name,
                        'type': 'lxc',
                        'uptime': container.get('uptime', 0)
                    })
            
            return resources
            
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            raise
    
    def get_resource_status(self, vmid: str, node: str) -> Dict[str, Any]:
        """Get detailed status of a VM or container."""
        try:
            # Try to get as VM first
            try:
                status = self.proxmox.nodes(node).qemu(vmid).status.current.get()
                return status
            except:
                # If failed, try as container
                status = self.proxmox.nodes(node).lxc(vmid).status.current.get()
                return status
                
        except Exception as e:
            logger.error(f"Failed to get status for {vmid}: {e}")
            raise 