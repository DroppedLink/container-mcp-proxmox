"""
Template and cloning service.
"""
import logging
from typing import Dict, Any, List
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)

class TemplateService(BaseProxmoxService):
    """Service for template and cloning operations."""
    
    def create_template(self, vmid: str, node: str) -> Dict[str, Any]:
        """Convert a VM to a template."""
        try:
            self.proxmox.nodes(node).qemu(vmid).template.post()
            
            return {
                "status": "success",
                "message": f"VM {vmid} converted to template successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create template from VM {vmid}: {e}")
            raise
    
    def clone_vm(self, vmid: str, newid: str, node: str, name: str = "",
                 target_node: str = "", storage: str = "",
                 full_clone: bool = True) -> Dict[str, Any]:
        """Clone a VM or template."""
        try:
            config = {
                'newid': int(newid),
                'full': 1 if full_clone else 0
            }
            
            if name:
                config['name'] = name
            
            if target_node:
                config['target'] = target_node
            
            if storage:
                config['storage'] = storage
            
            task = self.proxmox.nodes(node).qemu(vmid).clone.post(**config)
            
            return {
                "status": "success",
                "message": f"VM {vmid} cloned to {newid} successfully",
                "task": task
            }
            
        except Exception as e:
            logger.error(f"Failed to clone VM {vmid}: {e}")
            raise
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all VM templates and LXC container templates in the cluster."""
        try:
            templates = []
            
            # Get all nodes
            nodes = self.proxmox.nodes.get()
            
            for node in nodes:
                node_name = node['node']
                
                # Get VM templates (QEmu templates)
                vms = self.proxmox.nodes(node_name).qemu.get()
                for vm in vms:
                    if vm.get('template', 0) == 1:
                        templates.append({
                            'vmid': vm['vmid'],
                            'name': vm.get('name', f"Template-{vm['vmid']}"),
                            'node': node_name,
                            'type': 'vm',
                            'description': vm.get('description', '')
                        })
                
                # Get LXC container templates from storage
                try:
                    storages = self.proxmox.nodes(node_name).storage.get()
                    for storage in storages:
                        storage_name = storage['storage']
                        try:
                            content = self.proxmox.nodes(node_name).storage(storage_name).content.get()
                            for item in content:
                                if item.get('content') == 'vztmpl':
                                    # Extract template name from volid (e.g., 'local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst')
                                    volid = item['volid']
                                    if ':vztmpl/' in volid:
                                        template_name = volid.split(':vztmpl/')[1]
                                        # Remove file extension
                                        if '.' in template_name:
                                            template_name = template_name.rsplit('.tar.', 1)[0]
                                        
                                        templates.append({
                                            'volid': volid,
                                            'name': template_name,
                                            'node': node_name,
                                            'storage': storage_name,
                                            'type': 'lxc',
                                            'size': item.get('size', 0),
                                            'description': f"LXC template ({item.get('format', 'unknown')} format)"
                                        })
                        except Exception as storage_e:
                            # Skip storages that don't support content listing
                            logger.debug(f"Skipping storage {storage_name} on {node_name}: {storage_e}")
                            continue
                except Exception as node_e:
                    logger.debug(f"Skipping storage enumeration for node {node_name}: {node_e}")
                    continue
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            raise 