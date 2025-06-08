"""Cluster and node management service for Proxmox."""

import logging
from typing import List, Dict, Any, Optional
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)


class ClusterService(BaseProxmoxService):
    """Service for managing Proxmox cluster and node operations."""

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster health and status."""
        try:
            # Get cluster status
            cluster_status = self.proxmox.cluster.status.get()
            
            # Process cluster nodes and quorum info
            nodes = []
            quorum_info = {}
            
            for item in cluster_status:
                if item.get('type') == 'node':
                    node_info = {
                        'name': item.get('name', 'unknown'),
                        'id': item.get('id', 0),
                        'online': item.get('online', 0) == 1,
                        'local': item.get('local', 0) == 1,
                        'nodeid': item.get('nodeid', 0),
                        'ip': item.get('ip', ''),
                        'level': item.get('level', '')
                    }
                    nodes.append(node_info)
                elif item.get('type') == 'quorum':
                    quorum_info = {
                        'quorate': item.get('quorate', 0) == 1,
                        'nodes': item.get('nodes', 0),
                        'expected_votes': item.get('expected_votes', 0),
                        'total_votes': item.get('total_votes', 0)
                    }
            
            # Get cluster resources summary
            try:
                resources = self.proxmox.cluster.resources.get()
                resource_summary = self._summarize_cluster_resources(resources)
            except Exception as e:
                logger.warning(f"Could not get cluster resources: {e}")
                resource_summary = {}
            
            return {
                'cluster_name': self._get_cluster_name(),
                'quorum': quorum_info,
                'nodes': nodes,
                'nodes_online': len([n for n in nodes if n['online']]),
                'nodes_total': len(nodes),
                'resources': resource_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster status: {e}")
            raise

    def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get detailed status of a specific node."""
        try:
            # Get node status
            node_status = self.proxmox.nodes(node).status.get()
            
            # Get node version info
            try:
                version_info = self.proxmox.nodes(node).version.get()
            except Exception:
                version_info = {}
            
            # Get node network info
            try:
                network_info = self.proxmox.nodes(node).network.get()
            except Exception:
                network_info = []
            
            # Get node storage info
            try:
                storage_info = self.proxmox.nodes(node).storage.get()
            except Exception:
                storage_info = []
            
            # Process the status
            result = {
                'node': node,
                'status': node_status.get('pveversion', 'unknown'),
                'uptime': node_status.get('uptime', 0),
                'loadavg': node_status.get('loadavg', []),
                'cpu': {
                    'user': node_status.get('cpu', 0),
                    'cores': node_status.get('cpuinfo', {}).get('cpus', 0),
                    'model': node_status.get('cpuinfo', {}).get('model', 'unknown'),
                    'flags': node_status.get('cpuinfo', {}).get('flags', '')
                },
                'memory': {
                    'used': node_status.get('memory', {}).get('used', 0),
                    'total': node_status.get('memory', {}).get('total', 0),
                    'free': node_status.get('memory', {}).get('free', 0)
                },
                'rootfs': {
                    'used': node_status.get('rootfs', {}).get('used', 0),
                    'total': node_status.get('rootfs', {}).get('total', 0),
                    'avail': node_status.get('rootfs', {}).get('avail', 0)
                },
                'swap': {
                    'used': node_status.get('swap', {}).get('used', 0),
                    'total': node_status.get('swap', {}).get('total', 0),
                    'free': node_status.get('swap', {}).get('free', 0)
                },
                'kversion': node_status.get('kversion', 'unknown'),
                'pveversion': node_status.get('pveversion', 'unknown'),
                'version_info': version_info,
                'network_interfaces': len(network_info),
                'storage_count': len(storage_info)
            }
            
            # Calculate percentages
            if result['memory']['total'] > 0:
                result['memory']['usage_percent'] = round((result['memory']['used'] / result['memory']['total']) * 100, 1)
            else:
                result['memory']['usage_percent'] = 0
            
            if result['rootfs']['total'] > 0:
                result['rootfs']['usage_percent'] = round((result['rootfs']['used'] / result['rootfs']['total']) * 100, 1)
            else:
                result['rootfs']['usage_percent'] = 0
            
            # Format uptime
            result['uptime_human'] = self._format_uptime(result['uptime'])
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get node status for {node}: {e}")
            raise

    def list_cluster_resources(self, resource_type: str = "") -> List[Dict[str, Any]]:
        """List and categorize cluster resources."""
        try:
            resources = self.proxmox.cluster.resources.get(type=resource_type if resource_type else None)
            
            processed_resources = []
            
            for resource in resources:
                resource_info = {
                    'id': resource.get('id', ''),
                    'type': resource.get('type', 'unknown'),
                    'node': resource.get('node', ''),
                    'status': resource.get('status', 'unknown'),
                    'name': resource.get('name', ''),
                    'vmid': resource.get('vmid'),
                    'maxcpu': resource.get('maxcpu'),
                    'cpu': resource.get('cpu'),
                    'maxmem': resource.get('maxmem'),
                    'mem': resource.get('mem'),
                    'maxdisk': resource.get('maxdisk'),
                    'disk': resource.get('disk'),
                    'uptime': resource.get('uptime'),
                    'level': resource.get('level', ''),
                    'pool': resource.get('pool', '')
                }
                
                # Calculate usage percentages
                if resource_info['maxcpu'] and resource_info['cpu']:
                    resource_info['cpu_percent'] = round((resource_info['cpu'] * 100), 2)
                
                if resource_info['maxmem'] and resource_info['mem']:
                    resource_info['mem_percent'] = round((resource_info['mem'] / resource_info['maxmem']) * 100, 1)
                
                if resource_info['maxdisk'] and resource_info['disk']:
                    resource_info['disk_percent'] = round((resource_info['disk'] / resource_info['maxdisk']) * 100, 1)
                
                # Format uptime
                if resource_info['uptime']:
                    resource_info['uptime_human'] = self._format_uptime(resource_info['uptime'])
                
                processed_resources.append(resource_info)
            
            return processed_resources
            
        except Exception as e:
            logger.error(f"Failed to list cluster resources: {e}")
            raise

    def migrate_vm(self, vmid: str, source_node: str, target_node: str, 
                   online: bool = True, force: bool = False) -> Dict[str, Any]:
        """Migrate a VM between nodes."""
        try:
            # Determine VM type (qemu or lxc)
            vm_type = self._get_resource_type(vmid, source_node)
            
            # Prepare migration parameters
            migrate_params = {
                'target': target_node,
                'online': 1 if online else 0
            }
            
            if force:
                migrate_params['force'] = 1
            
            # Perform migration
            if vm_type == 'qemu':
                task = self.proxmox.nodes(source_node).qemu(vmid).migrate.post(**migrate_params)
            elif vm_type == 'lxc':
                task = self.proxmox.nodes(source_node).lxc(vmid).migrate.post(**migrate_params)
            else:
                raise ValueError(f"Unknown VM type for {vmid}")
            
            return {
                'status': 'started',
                'message': f"Migration of {vm_type.upper()} {vmid} from {source_node} to {target_node} started",
                'task': task,
                'vmid': vmid,
                'source': source_node,
                'target': target_node,
                'online': online
            }
            
        except Exception as e:
            logger.error(f"Failed to migrate VM {vmid} from {source_node} to {target_node}: {e}")
            raise

    def set_node_maintenance(self, node: str, maintenance: bool, 
                           reason: str = "Maintenance mode") -> Dict[str, Any]:
        """Set node maintenance mode."""
        try:
            # Note: Proxmox doesn't have a direct "maintenance mode" but we can 
            # disable the node for scheduling new VMs
            if maintenance:
                # This would typically involve moving VMs and marking node unavailable
                # For now, we'll return the concept
                return {
                    'status': 'info',
                    'message': f"Maintenance mode concept for node {node}",
                    'note': "Full maintenance mode requires moving VMs and updating cluster config",
                    'node': node,
                    'maintenance': maintenance,
                    'reason': reason
                }
            else:
                return {
                    'status': 'info',
                    'message': f"Node {node} would be enabled for normal operation",
                    'node': node,
                    'maintenance': maintenance
                }
            
        except Exception as e:
            logger.error(f"Failed to set maintenance mode for node {node}: {e}")
            raise

    def get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster-wide configuration."""
        try:
            # Get cluster configuration
            try:
                cluster_config = self.proxmox.cluster.config.get()
            except Exception:
                cluster_config = {}
            
            # Get cluster options
            try:
                cluster_options = self.proxmox.cluster.options.get()
            except Exception:
                cluster_options = {}
            
            # Get cluster resources for summary
            try:
                resources = self.proxmox.cluster.resources.get()
                resource_summary = self._summarize_cluster_resources(resources)
            except Exception:
                resource_summary = {}
            
            return {
                'cluster_name': self._get_cluster_name(),
                'config': cluster_config,
                'options': cluster_options,
                'resources_summary': resource_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster config: {e}")
            raise

    def _get_resource_type(self, vmid: str, node: str) -> str:
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

    def _get_cluster_name(self) -> str:
        """Get cluster name."""
        try:
            cluster_status = self.proxmox.cluster.status.get()
            for item in cluster_status:
                if item.get('type') == 'cluster':
                    return item.get('name', 'unknown')
            return 'unknown'
        except Exception:
            return 'unknown'

    def _summarize_cluster_resources(self, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize cluster resources."""
        summary = {
            'nodes': 0,
            'vms': 0,
            'lxc': 0,
            'storage': 0,
            'pools': 0,
            'running_vms': 0,
            'stopped_vms': 0,
            'total_memory_gb': 0,
            'used_memory_gb': 0,
            'total_disk_gb': 0,
            'used_disk_gb': 0
        }
        
        for resource in resources:
            res_type = resource.get('type', '')
            
            if res_type == 'node':
                summary['nodes'] += 1
            elif res_type == 'qemu':
                summary['vms'] += 1
                if resource.get('status') == 'running':
                    summary['running_vms'] += 1
                else:
                    summary['stopped_vms'] += 1
            elif res_type == 'lxc':
                summary['lxc'] += 1
                if resource.get('status') == 'running':
                    summary['running_vms'] += 1
                else:
                    summary['stopped_vms'] += 1
            elif res_type == 'storage':
                summary['storage'] += 1
            elif res_type == 'pool':
                summary['pools'] += 1
            
            # Add memory and disk (convert bytes to GB)
            if resource.get('maxmem'):
                summary['total_memory_gb'] += resource['maxmem'] / (1024**3)
            if resource.get('mem'):
                summary['used_memory_gb'] += resource['mem'] / (1024**3)
            if resource.get('maxdisk'):
                summary['total_disk_gb'] += resource['maxdisk'] / (1024**3)
            if resource.get('disk'):
                summary['used_disk_gb'] += resource['disk'] / (1024**3)
        
        # Round values
        for key in ['total_memory_gb', 'used_memory_gb', 'total_disk_gb', 'used_disk_gb']:
            summary[key] = round(summary[key], 1)
        
        return summary

    def _format_uptime(self, uptime_seconds: int) -> str:
        """Format uptime in human-readable format."""
        if uptime_seconds < 60:
            return f"{uptime_seconds} seconds"
        elif uptime_seconds < 3600:
            minutes = uptime_seconds // 60
            return f"{minutes} minutes"
        elif uptime_seconds < 86400:
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = uptime_seconds // 86400
            hours = (uptime_seconds % 86400) // 3600
            return f"{days}d {hours}h" 