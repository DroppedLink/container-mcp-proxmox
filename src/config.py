"""
Configuration constants for Proxmox MCP Server.
"""
import os

# Server Configuration
DEFAULT_MCP_HOST = "0.0.0.0"
DEFAULT_MCP_PORT = 8001

# Proxmox VM/Container Defaults
DEFAULT_VM_CORES = 1
DEFAULT_VM_MEMORY = 512  # MB
DEFAULT_VM_DISK_SIZE = "8G"
DEFAULT_VM_OS_TYPE = "l26"
DEFAULT_SCSI_HARDWARE = "virtio-scsi-pci"

DEFAULT_CONTAINER_CORES = 1
DEFAULT_CONTAINER_MEMORY = 512  # MB
DEFAULT_CONTAINER_ROOTFS_SIZE = "8G"

# Network Configuration
DEFAULT_NETWORK_BRIDGE = os.getenv("PROXMOX_DEFAULT_BRIDGE", "vmbr0")
DEFAULT_VM_NETWORK = f"virtio,bridge={DEFAULT_NETWORK_BRIDGE}"
DEFAULT_CONTAINER_NETWORK = f"name=eth0,bridge={DEFAULT_NETWORK_BRIDGE},ip=dhcp"

# Storage Configuration
def get_default_storage():
    """Get default storage from environment or use auto-detection."""
    return os.getenv("PROXMOX_DEFAULT_STORAGE", None)  # None means auto-detect

# Storage Preferences
PREFER_SHARED_STORAGE = os.getenv("PROXMOX_PREFER_SHARED_STORAGE", "true").lower() in ("true", "1", "yes")
ALLOW_LOCAL_STORAGE = os.getenv("PROXMOX_ALLOW_LOCAL_STORAGE", "false").lower() in ("true", "1", "yes")

# Test Configuration
TEST_VM_ID_RANGE_START = int(os.getenv("PROXMOX_TEST_VMID_START", "9990"))
TEST_VM_ID_RANGE_END = int(os.getenv("PROXMOX_TEST_VMID_END", "9999"))
TEST_PASSWORD_PREFIX = os.getenv("PROXMOX_TEST_PASSWORD_PREFIX", "MCPTest")

# Backup Configuration
DEFAULT_BACKUP_COMPRESSION = "zstd"
DEFAULT_BACKUP_MODE = "snapshot"
DEFAULT_BACKUP_STORAGE = "local" 