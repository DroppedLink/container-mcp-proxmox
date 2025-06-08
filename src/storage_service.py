"""Storage management service for Proxmox."""

import logging
from typing import List, Dict, Any, Optional
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)


class StorageService(BaseProxmoxService):
    """Service for managing Proxmox storage operations."""

    def list_storage(self, node: str = "") -> List[Dict[str, Any]]:
        """List all available storage across nodes or specific node."""
        try:
            storage_list = []
            
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
                    storages = self.proxmox.nodes(node_name).storage.get()
                    
                    for storage in storages:
                        storage_info = {
                            'node': node_name,
                            'storage': storage['storage'],
                            'type': storage.get('type', 'unknown'),
                            'content': storage.get('content', ''),
                            'enabled': storage.get('enabled', 1) == 1,
                            'shared': storage.get('shared', 0) == 1,
                            'active': storage.get('active', 1) == 1,
                            'total': storage.get('total', 0),
                            'used': storage.get('used', 0),
                            'avail': storage.get('avail', 0),
                            'used_fraction': storage.get('used_fraction', 0.0)
                        }
                        
                        # Calculate usage percentage
                        if storage_info['total'] > 0:
                            storage_info['usage_percent'] = round((storage_info['used'] / storage_info['total']) * 100, 1)
                        else:
                            storage_info['usage_percent'] = 0.0
                        
                        # Format sizes for human readability
                        storage_info['total_gb'] = round(storage_info['total'] / (1024**3), 2) if storage_info['total'] > 0 else 0
                        storage_info['used_gb'] = round(storage_info['used'] / (1024**3), 2) if storage_info['used'] > 0 else 0
                        storage_info['avail_gb'] = round(storage_info['avail'] / (1024**3), 2) if storage_info['avail'] > 0 else 0
                        
                        # Parse content types
                        content_types = storage_info['content'].split(',') if storage_info['content'] else []
                        storage_info['content_types'] = [ct.strip() for ct in content_types]
                        
                        storage_list.append(storage_info)
                        
                except Exception as e:
                    logger.error(f"Error getting storage for node {node_name}: {e}")
                    continue
            
            return storage_list
            
        except Exception as e:
            logger.error(f"Failed to list storage: {e}")
            raise

    def get_storage_status(self, storage_name: str, node: str) -> Dict[str, Any]:
        """Get detailed status of a specific storage."""
        try:
            # Get storage configuration
            storage_config = self.proxmox.nodes(node).storage(storage_name).get()
            
            # Get storage status
            storage_status = {}
            try:
                storages = self.proxmox.nodes(node).storage.get()
                for storage in storages:
                    if storage['storage'] == storage_name:
                        storage_status = storage
                        break
            except Exception:
                pass
            
            # Combine config and status
            result = {
                'storage': storage_name,
                'node': node,
                'type': storage_config.get('type', 'unknown'),
                'content': storage_config.get('content', ''),
                'enabled': storage_config.get('disable', 0) == 0,
                'shared': storage_config.get('shared', 0) == 1,
            }
            
            # Add status information if available
            if storage_status:
                result.update({
                    'active': storage_status.get('active', 0) == 1,
                    'total': storage_status.get('total', 0),
                    'used': storage_status.get('used', 0),
                    'avail': storage_status.get('avail', 0),
                    'used_fraction': storage_status.get('used_fraction', 0.0)
                })
                
                # Calculate usage percentage and human-readable sizes
                if result['total'] > 0:
                    result['usage_percent'] = round((result['used'] / result['total']) * 100, 1)
                    result['total_gb'] = round(result['total'] / (1024**3), 2)
                    result['used_gb'] = round(result['used'] / (1024**3), 2)
                    result['avail_gb'] = round(result['avail'] / (1024**3), 2)
                else:
                    result['usage_percent'] = 0.0
                    result['total_gb'] = 0
                    result['used_gb'] = 0
                    result['avail_gb'] = 0
            
            # Parse content types
            content_types = result['content'].split(',') if result['content'] else []
            result['content_types'] = [ct.strip() for ct in content_types]
            
            # Add type-specific configuration
            storage_type = result['type']
            if storage_type == 'dir':
                result['path'] = storage_config.get('path', '')
            elif storage_type == 'nfs':
                result['server'] = storage_config.get('server', '')
                result['export'] = storage_config.get('export', '')
            elif storage_type == 'cifs':
                result['server'] = storage_config.get('server', '')
                result['share'] = storage_config.get('share', '')
            elif storage_type == 'iscsi':
                result['portal'] = storage_config.get('portal', '')
                result['target'] = storage_config.get('target', '')
            elif storage_type == 'lvm':
                result['vgname'] = storage_config.get('vgname', '')
            elif storage_type == 'lvmthin':
                result['vgname'] = storage_config.get('vgname', '')
                result['thinpool'] = storage_config.get('thinpool', '')
            elif storage_type == 'zfspool':
                result['pool'] = storage_config.get('pool', '')
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get storage status for {storage_name} on {node}: {e}")
            raise

    def list_storage_content(self, storage_name: str, node: str, content_type: str = "") -> List[Dict[str, Any]]:
        """List content in a specific storage."""
        try:
            content_list = []
            
            # Get content from storage
            if content_type:
                content = self.proxmox.nodes(node).storage(storage_name).content.get(content=content_type)
            else:
                content = self.proxmox.nodes(node).storage(storage_name).content.get()
            
            for item in content:
                content_info = {
                    'volid': item['volid'],
                    'content': item.get('content', 'unknown'),
                    'format': item.get('format', 'unknown'),
                    'size': item.get('size', 0),
                    'used': item.get('used', 0),
                    'vmid': item.get('vmid'),
                    'ctime': item.get('ctime', 0),
                }
                
                # Format size for human readability
                if content_info['size'] > 0:
                    if content_info['size'] >= 1024**3:  # GB
                        content_info['size_human'] = f"{content_info['size'] / (1024**3):.2f} GB"
                    elif content_info['size'] >= 1024**2:  # MB
                        content_info['size_human'] = f"{content_info['size'] / (1024**2):.2f} MB"
                    elif content_info['size'] >= 1024:  # KB
                        content_info['size_human'] = f"{content_info['size'] / 1024:.2f} KB"
                    else:
                        content_info['size_human'] = f"{content_info['size']} B"
                else:
                    content_info['size_human'] = "0 B"
                
                # Extract filename for templates and ISOs
                if ':' in content_info['volid']:
                    _, filename = content_info['volid'].split(':', 1)
                    if '/' in filename:
                        content_info['filename'] = filename.split('/')[-1]
                    else:
                        content_info['filename'] = filename
                else:
                    content_info['filename'] = content_info['volid']
                
                content_list.append(content_info)
            
            return content_list
            
        except Exception as e:
            logger.error(f"Failed to list content for storage {storage_name} on {node}: {e}")
            raise

    def get_suitable_storage(self, node: str, content_type: str, min_free_gb: float = 0) -> List[Dict[str, Any]]:
        """Find storage suitable for specific content type with optional minimum free space."""
        try:
            suitable_storage = []
            
            # Get all storage for the node
            storages = self.list_storage(node)
            
            for storage in storages:
                # Check if storage is active and enabled
                if not storage.get('active', False) or not storage.get('enabled', False):
                    continue
                
                # Check if storage supports the content type
                if content_type not in storage.get('content_types', []):
                    continue
                
                # Check minimum free space requirement
                if min_free_gb > 0 and storage.get('avail_gb', 0) < min_free_gb:
                    continue
                
                suitable_storage.append({
                    'storage': storage['storage'],
                    'type': storage['type'],
                    'avail_gb': storage.get('avail_gb', 0),
                    'usage_percent': storage.get('usage_percent', 0),
                    'shared': storage.get('shared', False)
                })
            
            # Sort by available space (descending)
            suitable_storage.sort(key=lambda x: x['avail_gb'], reverse=True)
            
            return suitable_storage
            
        except Exception as e:
            logger.error(f"Failed to find suitable storage for {content_type} on {node}: {e}")
            raise 