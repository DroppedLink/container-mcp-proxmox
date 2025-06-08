"""
User and permission management service.
"""
import logging
from typing import Dict, Any, List
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)

class UserService(BaseProxmoxService):
    """Service for user and permission management."""
    
    def create_user(self, userid: str, password: str = "", email: str = "",
                   firstname: str = "", lastname: str = "", groups: str = "",
                   enable: bool = True) -> Dict[str, Any]:
        """Create a new Proxmox user."""
        try:
            config = {
                'userid': userid,
                'enable': 1 if enable else 0
            }
            
            if password:
                config['password'] = password
            if email:
                config['email'] = email
            if firstname:
                config['firstname'] = firstname
            if lastname:
                config['lastname'] = lastname
            if groups:
                config['groups'] = groups
            
            self.proxmox.access.users.create(**config)
            
            return {
                "status": "success",
                "message": f"User {userid} created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create user {userid}: {e}")
            raise
    
    def delete_user(self, userid: str) -> Dict[str, Any]:
        """Delete a Proxmox user."""
        try:
            self.proxmox.access.users(userid).delete()
            
            return {
                "status": "success",
                "message": f"User {userid} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete user {userid}: {e}")
            raise
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all Proxmox users."""
        try:
            users = self.proxmox.access.users.get()
            
            formatted_users = []
            for user in users:
                formatted_users.append({
                    'userid': user['userid'],
                    'enable': bool(user.get('enable', 1)),
                    'email': user.get('email', ''),
                    'firstname': user.get('firstname', ''),
                    'lastname': user.get('lastname', ''),
                    'groups': user.get('groups', '')
                })
            
            return formatted_users
            
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise
    
    def set_permissions(self, path: str, roleid: str, userid: str = "",
                       groupid: str = "", propagate: bool = True) -> Dict[str, Any]:
        """Set permissions for a user or group on a path."""
        try:
            config = {
                'path': path,
                'roles': roleid,
                'propagate': 1 if propagate else 0
            }
            
            if userid:
                config['users'] = userid
            elif groupid:
                config['groups'] = groupid
            else:
                raise ValueError("Either userid or groupid must be provided")
            
            self.proxmox.access.acl.put(**config)
            
            target = userid if userid else groupid
            target_type = "user" if userid else "group"
            
            return {
                "status": "success",
                "message": f"Permissions set for {target_type} {target} on path {path}"
            }
            
        except Exception as e:
            logger.error(f"Failed to set permissions: {e}")
            raise
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """List all available Proxmox roles."""
        try:
            roles = self.proxmox.access.roles.get()
            
            formatted_roles = []
            for role in roles:
                formatted_roles.append({
                    'roleid': role['roleid'],
                    'privs': role.get('privs', '')
                })
            
            return formatted_roles
            
        except Exception as e:
            logger.error(f"Failed to list roles: {e}")
            raise
    
    def list_permissions(self) -> List[Dict[str, Any]]:
        """List all ACL permissions."""
        try:
            acls = self.proxmox.access.acl.get()
            
            formatted_acls = []
            for acl in acls:
                formatted_acls.append({
                    'path': acl['path'],
                    'type': acl['type'],
                    'ugid': acl['ugid'],
                    'roleid': acl['roleid'],
                    'propagate': bool(acl.get('propagate', 1))
                })
            
            return formatted_acls
            
        except Exception as e:
            logger.error(f"Failed to list permissions: {e}")
            raise 