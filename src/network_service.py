"""Network and firewall management service for Proxmox."""

import logging
from typing import List, Dict, Any, Optional
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)


class NetworkService(BaseProxmoxService):
    """Service for managing Proxmox network and firewall operations."""

    def list_networks(self, node: str = "") -> List[Dict[str, Any]]:
        """List network interfaces, bridges, VLANs, and bonds."""
        try:
            all_networks = []
            
            # If specific node provided, check only that node
            if node:
                nodes_to_check = [node]
            else:
                # Get all nodes
                nodes_list = self.proxmox.nodes.get()
                nodes_to_check = [n['node'] for n in nodes_list]
            
            for node_name in nodes_to_check:
                try:
                    # Get network configuration for the node
                    network_config = self.proxmox.nodes(node_name).network.get()
                    
                    for interface in network_config:
                        network_info = {
                            'node': node_name,
                            'iface': interface.get('iface', ''),
                            'type': interface.get('type', 'unknown'),
                            'method': interface.get('method', ''),
                            'address': interface.get('address', ''),
                            'netmask': interface.get('netmask', ''),
                            'gateway': interface.get('gateway', ''),
                            'bridge_ports': interface.get('bridge_ports', ''),
                            'bridge_stp': interface.get('bridge_stp', ''),
                            'bridge_fd': interface.get('bridge_fd', ''),
                            'vlan_id': interface.get('vlan-id', ''),
                            'vlan_raw_device': interface.get('vlan-raw-device', ''),
                            'bond_slaves': interface.get('slaves', ''),
                            'bond_mode': interface.get('bond_mode', ''),
                            'active': interface.get('active', 0) == 1,
                            'autostart': interface.get('autostart', 0) == 1,
                            'comments': interface.get('comments', '')
                        }
                        
                        # Add additional info based on type
                        if network_info['type'] == 'bridge':
                            network_info['bridge_info'] = {
                                'ports': network_info['bridge_ports'],
                                'stp': network_info['bridge_stp'],
                                'fd': network_info['bridge_fd']
                            }
                        elif network_info['type'] == 'bond':
                            network_info['bond_info'] = {
                                'slaves': network_info['bond_slaves'],
                                'mode': network_info['bond_mode']
                            }
                        elif network_info['type'] == 'vlan':
                            network_info['vlan_info'] = {
                                'id': network_info['vlan_id'],
                                'raw_device': network_info['vlan_raw_device']
                            }
                        
                        all_networks.append(network_info)
                        
                except Exception as e:
                    logger.error(f"Error getting network config for node {node_name}: {e}")
                    continue
            
            return all_networks
            
        except Exception as e:
            logger.error(f"Failed to list networks: {e}")
            raise

    def get_network_config(self, node: str, interface: str) -> Dict[str, Any]:
        """Get detailed configuration of a specific network interface."""
        try:
            # Get the specific interface configuration
            network_list = self.proxmox.nodes(node).network.get()
            interface_config = next((iface for iface in network_list if iface.get('iface') == interface), None)
            
            if not interface_config:
                raise ValueError(f"Interface {interface} not found on node {node}")
            
            # Get additional runtime information if available
            try:
                # Try to get runtime network statistics
                node_status = self.proxmox.nodes(node).status.get()
                # Note: Detailed interface stats would require additional API calls
            except Exception:
                node_status = {}
            
            result = {
                'node': node,
                'interface': interface,
                'config': interface_config,
                'runtime_info': self._get_interface_runtime_info(node, interface)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get network config for {interface} on {node}: {e}")
            raise

    def get_node_network(self, node: str) -> Dict[str, Any]:
        """Get comprehensive network status for a specific node."""
        try:
            # Get network configuration
            network_config = self.proxmox.nodes(node).network.get()
            
            # Get DNS configuration
            try:
                dns_config = self.proxmox.nodes(node).dns.get()
            except Exception:
                dns_config = {}
            
            # Categorize interfaces
            interfaces = {
                'physical': [],
                'bridges': [],
                'bonds': [],
                'vlans': [],
                'other': []
            }
            
            for iface in network_config:
                iface_type = iface.get('type', 'unknown')
                if iface_type == 'eth':
                    interfaces['physical'].append(iface)
                elif iface_type == 'bridge':
                    interfaces['bridges'].append(iface)
                elif iface_type == 'bond':
                    interfaces['bonds'].append(iface)
                elif iface_type == 'vlan':
                    interfaces['vlans'].append(iface)
                else:
                    interfaces['other'].append(iface)
            
            # Get routing information
            try:
                routes = self._get_routing_info(node)
            except Exception:
                routes = []
            
            return {
                'node': node,
                'dns_config': dns_config,
                'interfaces': interfaces,
                'interface_count': {
                    'total': len(network_config),
                    'physical': len(interfaces['physical']),
                    'bridges': len(interfaces['bridges']),
                    'bonds': len(interfaces['bonds']),
                    'vlans': len(interfaces['vlans']),
                    'other': len(interfaces['other'])
                },
                'routes': routes
            }
            
        except Exception as e:
            logger.error(f"Failed to get node network for {node}: {e}")
            raise

    def list_firewall_rules(self, node: str = "", vmid: str = "") -> List[Dict[str, Any]]:
        """List firewall rules for cluster, node, or specific VM."""
        try:
            all_rules = []
            
            if vmid and node:
                # Get VM-specific firewall rules
                try:
                    # Determine VM type
                    vm_type = self._get_resource_type(vmid, node)
                    
                    if vm_type == 'qemu':
                        vm_rules = self.proxmox.nodes(node).qemu(vmid).firewall.rules.get()
                    elif vm_type == 'lxc':
                        vm_rules = self.proxmox.nodes(node).lxc(vmid).firewall.rules.get()
                    else:
                        vm_rules = []
                    
                    for rule in vm_rules:
                        rule_info = self._process_firewall_rule(rule, 'vm', node, vmid)
                        all_rules.append(rule_info)
                        
                except Exception as e:
                    logger.warning(f"Could not get VM firewall rules for {vmid}: {e}")
            
            elif node:
                # Get node-specific firewall rules
                try:
                    node_rules = self.proxmox.nodes(node).firewall.rules.get()
                    for rule in node_rules:
                        rule_info = self._process_firewall_rule(rule, 'node', node)
                        all_rules.append(rule_info)
                except Exception as e:
                    logger.warning(f"Could not get node firewall rules for {node}: {e}")
            
            else:
                # Get cluster-wide firewall rules
                try:
                    cluster_rules = self.proxmox.cluster.firewall.rules.get()
                    for rule in cluster_rules:
                        rule_info = self._process_firewall_rule(rule, 'cluster')
                        all_rules.append(rule_info)
                except Exception as e:
                    logger.warning(f"Could not get cluster firewall rules: {e}")
                
                # Also get all node rules if no specific node requested
                if not node:
                    nodes_list = self.proxmox.nodes.get()
                    for node_info in nodes_list:
                        node_name = node_info['node']
                        try:
                            node_rules = self.proxmox.nodes(node_name).firewall.rules.get()
                            for rule in node_rules:
                                rule_info = self._process_firewall_rule(rule, 'node', node_name)
                                all_rules.append(rule_info)
                        except Exception as e:
                            logger.warning(f"Could not get firewall rules for node {node_name}: {e}")
            
            return all_rules
            
        except Exception as e:
            logger.error(f"Failed to list firewall rules: {e}")
            raise

    def get_firewall_status(self, node: str = "", vmid: str = "") -> Dict[str, Any]:
        """Get firewall status and configuration."""
        try:
            if vmid and node:
                # Get VM firewall status
                vm_type = self._get_resource_type(vmid, node)
                
                if vm_type == 'qemu':
                    fw_options = self.proxmox.nodes(node).qemu(vmid).firewall.options.get()
                elif vm_type == 'lxc':
                    fw_options = self.proxmox.nodes(node).lxc(vmid).firewall.options.get()
                else:
                    fw_options = {}
                
                return {
                    'scope': 'vm',
                    'node': node,
                    'vmid': vmid,
                    'vm_type': vm_type,
                    'options': fw_options
                }
                
            elif node:
                # Get node firewall status
                fw_options = self.proxmox.nodes(node).firewall.options.get()
                
                return {
                    'scope': 'node',
                    'node': node,
                    'options': fw_options
                }
            
            else:
                # Get cluster firewall status
                fw_options = self.proxmox.cluster.firewall.options.get()
                
                return {
                    'scope': 'cluster',
                    'options': fw_options
                }
                
        except Exception as e:
            logger.error(f"Failed to get firewall status: {e}")
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

    def _process_firewall_rule(self, rule: Dict[str, Any], scope: str, 
                               node: str = "", vmid: str = "") -> Dict[str, Any]:
        """Process and format a firewall rule."""
        rule_info = {
            'scope': scope,
            'node': node,
            'vmid': vmid,
            'pos': rule.get('pos', 0),
            'action': rule.get('action', ''),
            'type': rule.get('type', ''),
            'enable': rule.get('enable', 0),
            'source': rule.get('source', ''),
            'dest': rule.get('dest', ''),
            'proto': rule.get('proto', ''),
            'dport': rule.get('dport', ''),
            'sport': rule.get('sport', ''),
            'comment': rule.get('comment', ''),
            'macro': rule.get('macro', ''),
            'iface': rule.get('iface', '')
        }
        
        # Format rule description
        action = rule_info['action'].upper()
        source = rule_info['source'] or 'any'
        dest = rule_info['dest'] or 'any'
        proto = rule_info['proto'] or 'any'
        
        rule_info['description'] = f"{action}: {source} -> {dest} ({proto})"
        
        if rule_info['dport']:
            rule_info['description'] += f" port {rule_info['dport']}"
        
        return rule_info

    def _get_interface_runtime_info(self, node: str, interface: str) -> Dict[str, Any]:
        """Get runtime information for a network interface."""
        # This would typically require additional system calls or parsing
        # For now, return placeholder structure
        return {
            'status': 'unknown',
            'mtu': 'unknown',
            'speed': 'unknown',
            'duplex': 'unknown',
            'carrier': 'unknown'
        }

    def _get_routing_info(self, node: str) -> List[Dict[str, Any]]:
        """Get routing table information for a node."""
        # This would typically require system command execution
        # For now, return placeholder structure
        return [
            {
                'destination': 'default',
                'gateway': 'unknown',
                'interface': 'unknown',
                'metric': 'unknown'
            }
        ] 