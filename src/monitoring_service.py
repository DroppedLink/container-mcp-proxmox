"""Performance monitoring and statistics service for Proxmox."""

import logging
from typing import List, Dict, Any, Optional
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)


class MonitoringService(BaseProxmoxService):
    """Service for monitoring Proxmox performance and collecting statistics."""

    def get_vm_stats(self, vmid: str, node: str, timeframe: str = "hour") -> Dict[str, Any]:
        """Get VM/container performance statistics over time."""
        try:
            # Determine resource type
            vm_type = self._get_resource_type(vmid, node)
            
            # Get RRD data for the VM/container
            rrd_data = {}
            try:
                if vm_type == 'qemu':
                    rrd_data = self.proxmox.nodes(node).qemu(vmid).rrd.get(timeframe=timeframe)
                elif vm_type == 'lxc':
                    rrd_data = self.proxmox.nodes(node).lxc(vmid).rrd.get(timeframe=timeframe)
            except Exception as e:
                logger.warning(f"Could not get RRD data for {vmid}: {e}")
            
            # Get current status for context
            try:
                if vm_type == 'qemu':
                    current_status = self.proxmox.nodes(node).qemu(vmid).status.current.get()
                elif vm_type == 'lxc':
                    current_status = self.proxmox.nodes(node).lxc(vmid).status.current.get()
            except Exception:
                current_status = {}
            
            # Process RRD data
            processed_stats = self._process_rrd_data(rrd_data)
            
            return {
                'vmid': vmid,
                'node': node,
                'type': vm_type,
                'timeframe': timeframe,
                'current_status': current_status,
                'stats': processed_stats,
                'summary': self._calculate_stats_summary(processed_stats)
            }
            
        except Exception as e:
            logger.error(f"Failed to get VM stats for {vmid} on {node}: {e}")
            raise

    def get_node_stats(self, node: str, timeframe: str = "hour") -> Dict[str, Any]:
        """Get node performance statistics over time."""
        try:
            # Get node RRD data
            rrd_data = {}
            try:
                rrd_data = self.proxmox.nodes(node).rrd.get(timeframe=timeframe)
            except Exception as e:
                logger.warning(f"Could not get RRD data for node {node}: {e}")
            
            # Get current node status
            try:
                current_status = self.proxmox.nodes(node).status.get()
            except Exception:
                current_status = {}
            
            # Process RRD data
            processed_stats = self._process_rrd_data(rrd_data)
            
            return {
                'node': node,
                'timeframe': timeframe,
                'current_status': current_status,
                'stats': processed_stats,
                'summary': self._calculate_stats_summary(processed_stats)
            }
            
        except Exception as e:
            logger.error(f"Failed to get node stats for {node}: {e}")
            raise

    def get_storage_stats(self, storage: str, node: str, timeframe: str = "hour") -> Dict[str, Any]:
        """Get storage performance statistics over time."""
        try:
            # Get storage RRD data
            rrd_data = {}
            try:
                rrd_data = self.proxmox.nodes(node).storage(storage).rrd.get(timeframe=timeframe)
            except Exception as e:
                logger.warning(f"Could not get RRD data for storage {storage}: {e}")
            
            # Get current storage status
            try:
                storage_list = self.proxmox.nodes(node).storage.get()
                current_status = next((s for s in storage_list if s['storage'] == storage), {})
            except Exception:
                current_status = {}
            
            # Process RRD data
            processed_stats = self._process_rrd_data(rrd_data)
            
            return {
                'storage': storage,
                'node': node,
                'timeframe': timeframe,
                'current_status': current_status,
                'stats': processed_stats,
                'summary': self._calculate_stats_summary(processed_stats)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats for {storage} on {node}: {e}")
            raise

    def list_alerts(self, node: str = "") -> List[Dict[str, Any]]:
        """List system alerts and warnings."""
        try:
            alerts = []
            
            # If specific node provided, check only that node
            if node:
                nodes_to_check = [node]
            else:
                # Get all nodes
                nodes_list = self.proxmox.nodes.get()
                nodes_to_check = [n['node'] for n in nodes_list]
            
            for node_name in nodes_to_check:
                try:
                    # Get node status to check for issues
                    node_status = self.proxmox.nodes(node_name).status.get()
                    
                    # Check for high resource usage
                    alerts.extend(self._check_node_alerts(node_name, node_status))
                    
                    # Get running VMs/containers and check their status
                    try:
                        resources = self.proxmox.cluster.resources.get()
                        node_vms = [r for r in resources if r.get('node') == node_name and r.get('type') in ['qemu', 'lxc']]
                        
                        for vm in node_vms:
                            alerts.extend(self._check_vm_alerts(vm))
                    except Exception as e:
                        logger.warning(f"Could not check VM alerts for node {node_name}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error checking alerts for node {node_name}: {e}")
                    continue
            
            # Sort alerts by severity (critical first)
            severity_order = {'critical': 0, 'warning': 1, 'info': 2}
            alerts.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 3))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to list alerts: {e}")
            raise

    def get_resource_usage(self, node: str = "") -> Dict[str, Any]:
        """Get real-time resource usage across cluster or specific node."""
        try:
            usage_summary = {
                'timestamp': self._get_current_timestamp(),
                'nodes': {},
                'cluster_totals': {
                    'cpu_cores': 0,
                    'cpu_used': 0,
                    'memory_total_gb': 0,
                    'memory_used_gb': 0,
                    'storage_total_gb': 0,
                    'storage_used_gb': 0,
                    'vms_total': 0,
                    'vms_running': 0
                }
            }
            
            # If specific node provided, check only that node
            if node:
                nodes_to_check = [node]
            else:
                # Get all nodes
                nodes_list = self.proxmox.nodes.get()
                nodes_to_check = [n['node'] for n in nodes_list]
            
            for node_name in nodes_to_check:
                try:
                    # Get node status
                    node_status = self.proxmox.nodes(node_name).status.get()
                    
                    # Get storage info
                    storage_info = self.proxmox.nodes(node_name).storage.get()
                    
                    # Calculate node usage
                    node_usage = self._calculate_node_usage(node_name, node_status, storage_info)
                    usage_summary['nodes'][node_name] = node_usage
                    
                    # Add to cluster totals
                    totals = usage_summary['cluster_totals']
                    totals['cpu_cores'] += node_usage.get('cpu_cores', 0)
                    totals['cpu_used'] += node_usage.get('cpu_used', 0)
                    totals['memory_total_gb'] += node_usage.get('memory_total_gb', 0)
                    totals['memory_used_gb'] += node_usage.get('memory_used_gb', 0)
                    
                except Exception as e:
                    logger.error(f"Error getting resource usage for node {node_name}: {e}")
                    continue
            
            # Get VM counts
            try:
                resources = self.proxmox.cluster.resources.get()
                vms = [r for r in resources if r.get('type') in ['qemu', 'lxc']]
                usage_summary['cluster_totals']['vms_total'] = len(vms)
                usage_summary['cluster_totals']['vms_running'] = len([v for v in vms if v.get('status') == 'running'])
            except Exception:
                pass
            
            # Calculate cluster percentages
            totals = usage_summary['cluster_totals']
            if totals['cpu_cores'] > 0:
                totals['cpu_usage_percent'] = round((totals['cpu_used'] / totals['cpu_cores']) * 100, 1)
            if totals['memory_total_gb'] > 0:
                totals['memory_usage_percent'] = round((totals['memory_used_gb'] / totals['memory_total_gb']) * 100, 1)
            
            return usage_summary
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
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

    def _process_rrd_data(self, rrd_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process RRD data into useful statistics."""
        if not rrd_data:
            return {}
        
        # Initialize stats structure
        stats = {
            'data_points': len(rrd_data),
            'cpu': [],
            'memory': [],
            'disk_read': [],
            'disk_write': [],
            'network_in': [],
            'network_out': []
        }
        
        for point in rrd_data:
            if point.get('cpu') is not None:
                stats['cpu'].append(point['cpu'])
            if point.get('mem') is not None:
                stats['memory'].append(point['mem'])
            if point.get('diskread') is not None:
                stats['disk_read'].append(point['diskread'])
            if point.get('diskwrite') is not None:
                stats['disk_write'].append(point['diskwrite'])
            if point.get('netin') is not None:
                stats['network_in'].append(point['netin'])
            if point.get('netout') is not None:
                stats['network_out'].append(point['netout'])
        
        return stats

    def _calculate_stats_summary(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from processed data."""
        summary = {}
        
        for metric, values in stats.items():
            if metric == 'data_points':
                continue
            
            if values:
                summary[f'{metric}_avg'] = round(sum(values) / len(values), 2)
                summary[f'{metric}_max'] = round(max(values), 2)
                summary[f'{metric}_min'] = round(min(values), 2)
        
        return summary

    def _check_node_alerts(self, node: str, node_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for node-level alerts."""
        alerts = []
        
        # Check CPU usage
        cpu_usage = node_status.get('cpu', 0)
        if cpu_usage > 0.9:  # 90%
            alerts.append({
                'node': node,
                'type': 'node_cpu',
                'severity': 'critical',
                'message': f"High CPU usage: {cpu_usage*100:.1f}%",
                'value': cpu_usage
            })
        elif cpu_usage > 0.8:  # 80%
            alerts.append({
                'node': node,
                'type': 'node_cpu',
                'severity': 'warning',
                'message': f"Elevated CPU usage: {cpu_usage*100:.1f}%",
                'value': cpu_usage
            })
        
        # Check memory usage
        memory = node_status.get('memory', {})
        if memory.get('total', 0) > 0:
            mem_usage = memory.get('used', 0) / memory.get('total', 1)
            if mem_usage > 0.95:  # 95%
                alerts.append({
                    'node': node,
                    'type': 'node_memory',
                    'severity': 'critical',
                    'message': f"Very high memory usage: {mem_usage*100:.1f}%",
                    'value': mem_usage
                })
            elif mem_usage > 0.85:  # 85%
                alerts.append({
                    'node': node,
                    'type': 'node_memory',
                    'severity': 'warning',
                    'message': f"High memory usage: {mem_usage*100:.1f}%",
                    'value': mem_usage
                })
        
        # Check root filesystem usage
        rootfs = node_status.get('rootfs', {})
        if rootfs.get('total', 0) > 0:
            disk_usage = rootfs.get('used', 0) / rootfs.get('total', 1)
            if disk_usage > 0.95:  # 95%
                alerts.append({
                    'node': node,
                    'type': 'node_disk',
                    'severity': 'critical',
                    'message': f"Root filesystem almost full: {disk_usage*100:.1f}%",
                    'value': disk_usage
                })
            elif disk_usage > 0.85:  # 85%
                alerts.append({
                    'node': node,
                    'type': 'node_disk',
                    'severity': 'warning',
                    'message': f"Root filesystem filling up: {disk_usage*100:.1f}%",
                    'value': disk_usage
                })
        
        return alerts

    def _check_vm_alerts(self, vm: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for VM-level alerts."""
        alerts = []
        
        # Check if VM is down unexpectedly (has uptime but status is not running)
        if vm.get('status') != 'running' and vm.get('uptime', 0) > 0:
            alerts.append({
                'node': vm.get('node', ''),
                'vmid': vm.get('vmid', ''),
                'type': 'vm_down',
                'severity': 'warning',
                'message': f"VM {vm.get('vmid')} ({vm.get('name', 'unknown')}) is down",
                'vm_name': vm.get('name', 'unknown')
            })
        
        # Check VM resource usage if available
        if vm.get('maxcpu') and vm.get('cpu'):
            cpu_usage = vm.get('cpu', 0)
            if cpu_usage > 0.9:  # 90%
                alerts.append({
                    'node': vm.get('node', ''),
                    'vmid': vm.get('vmid', ''),
                    'type': 'vm_cpu',
                    'severity': 'warning',
                    'message': f"VM {vm.get('vmid')} high CPU usage: {cpu_usage*100:.1f}%",
                    'vm_name': vm.get('name', 'unknown'),
                    'value': cpu_usage
                })
        
        return alerts

    def _calculate_node_usage(self, node: str, node_status: Dict[str, Any], storage_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive node resource usage."""
        usage = {
            'node': node,
            'cpu_cores': node_status.get('cpuinfo', {}).get('cpus', 0),
            'cpu_used': node_status.get('cpu', 0),
            'memory_total_gb': round(node_status.get('memory', {}).get('total', 0) / (1024**3), 1),
            'memory_used_gb': round(node_status.get('memory', {}).get('used', 0) / (1024**3), 1),
            'uptime': node_status.get('uptime', 0),
            'load_avg': node_status.get('loadavg', [])
        }
        
        # Calculate percentages
        if usage['cpu_cores'] > 0:
            usage['cpu_usage_percent'] = round((usage['cpu_used'] / usage['cpu_cores']) * 100, 1)
        if usage['memory_total_gb'] > 0:
            usage['memory_usage_percent'] = round((usage['memory_used_gb'] / usage['memory_total_gb']) * 100, 1)
        
        # Calculate storage totals
        storage_total = 0
        storage_used = 0
        for storage in storage_info:
            if storage.get('total', 0) > 0:
                storage_total += storage['total']
                storage_used += storage.get('used', 0)
        
        usage['storage_total_gb'] = round(storage_total / (1024**3), 1)
        usage['storage_used_gb'] = round(storage_used / (1024**3), 1)
        
        if usage['storage_total_gb'] > 0:
            usage['storage_usage_percent'] = round((usage['storage_used_gb'] / usage['storage_total_gb']) * 100, 1)
        
        return usage

    def _get_current_timestamp(self) -> int:
        """Get current Unix timestamp."""
        import time
        return int(time.time()) 