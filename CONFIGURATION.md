# Proxmox MCP Server Configuration Guide

This document explains how to configure the Proxmox MCP Server and customize its behavior through environment variables and configuration files.

## 🔧 Configuration Files

### 1. Environment Configuration (`.env`)

Copy `env.example` to `.env` and configure your Proxmox connection:

```bash
cp env.example .env
```

#### Required Settings
```bash
# Proxmox VE API Configuration
PROXMOX_HOST=your-proxmox-host.example.com
PROXMOX_USER=your-username@pam
PROXMOX_PASSWORD=your-password
PROXMOX_VERIFY_SSL=false
```

#### Optional Server Settings
```bash
# MCP Server Configuration
MCP_HOST=0.0.0.0              # Server bind address
MCP_PORT=8001                 # Server port
```

#### Optional Infrastructure Defaults
```bash
# Proxmox Infrastructure Defaults
PROXMOX_DEFAULT_STORAGE=local-lvm    # Default storage for VMs/containers
PROXMOX_DEFAULT_BRIDGE=vmbr0         # Default network bridge
```

#### Optional Test Configuration
```bash
# Test Configuration
PROXMOX_TEST_VMID_START=9990         # Start of test VM ID range
PROXMOX_TEST_VMID_END=9999           # End of test VM ID range
PROXMOX_TEST_PASSWORD_PREFIX=MCPTest # Prefix for test user passwords
```

### 2. Cursor SSE Configuration (`cursor-sse-config.json`)

Configure Cursor IDE integration:

```json
{
  "mcpServers": {
    "proxmox": {
      "url": "http://localhost:8001/sse",
      "transport": "sse"
    }
  }
}
```

**Note**: Update the URL if your server runs on a different host/port.

## 🏗️ Infrastructure Defaults

The server uses intelligent defaults that can be overridden:

### VM Creation Defaults
- **Cores**: 1 CPU core
- **Memory**: 512 MB RAM
- **Disk Size**: 8GB
- **OS Type**: Linux 2.6+ (`l26`)
- **SCSI Hardware**: `virtio-scsi-pci`
- **Network**: `virtio,bridge=vmbr0`
- **Storage**: Auto-detected or `local-lvm`

### Container Creation Defaults
- **Cores**: 1 CPU core
- **Memory**: 512 MB RAM
- **Root FS Size**: 8GB
- **Network**: `name=eth0,bridge=vmbr0,ip=dhcp`
- **Unprivileged**: `true`
- **Storage**: Auto-detected or `local-lvm`

### Storage Auto-Detection

When no storage is specified, the server automatically:

1. Checks `PROXMOX_DEFAULT_STORAGE` environment variable
2. If not set, finds suitable storage using `get_suitable_storage()`
3. Selects storage with most available space for the content type
4. Falls back to `local-lvm` if auto-detection fails

### Disk Format Selection

The server automatically selects the optimal disk format:

- **Directory/NFS/CIFS storage**: `qcow2` format
- **LVM/ZFS storage**: `raw` format

## 🧪 Test Configuration

### VM ID Range
Test VMs are created in the range `9990-9999` by default. Override with:
```bash
PROXMOX_TEST_VMID_START=8000
PROXMOX_TEST_VMID_END=8099
```

### Test Passwords
Test user passwords use the format `{PREFIX}{timestamp}!`. Override prefix with:
```bash
PROXMOX_TEST_PASSWORD_PREFIX=MyTest
```

## 🌐 Network Configuration

### Default Bridge
All VMs and containers use `vmbr0` by default. Override with:
```bash
PROXMOX_DEFAULT_BRIDGE=vmbr1
```

### Custom Network Configuration
For advanced networking, modify the configuration in `src/config.py`:

```python
# Custom VM network configuration
DEFAULT_VM_NETWORK = f"virtio,bridge={DEFAULT_NETWORK_BRIDGE},tag=100"

# Custom container network configuration  
DEFAULT_CONTAINER_NETWORK = f"name=eth0,bridge={DEFAULT_NETWORK_BRIDGE},ip=192.168.1.100/24,gw=192.168.1.1"
```

## 📦 Storage Configuration

### Default Storage Priority
1. Environment variable `PROXMOX_DEFAULT_STORAGE`
2. Auto-detected suitable storage (most free space)
3. Fallback to `local-lvm`

### Storage Content Types
The server automatically selects storage based on content type:
- **VMs**: `images` content type
- **Containers**: `rootdir` content type
- **Backups**: `backup` content type
- **Templates**: `vztmpl` content type

## 🔒 Security Configuration

### SSL Verification
For development environments, SSL verification is typically disabled:
```bash
PROXMOX_VERIFY_SSL=false
```

For production, enable SSL verification and use proper certificates:
```bash
PROXMOX_VERIFY_SSL=true
```

### User Permissions
Ensure your Proxmox user has appropriate permissions:
- **VM/Container Management**: `VM.Allocate`, `VM.Config.Disk`, `VM.Config.Memory`, etc.
- **Storage Access**: `Datastore.Allocate`, `Datastore.AllocateSpace`
- **User Management**: `User.Modify`, `Group.Allocate` (if using user management features)

## 🚀 Server Startup Options

### Command Line Arguments
```bash
python mcp_server.py --help
```

### Environment Variables
```bash
# Override default host/port
MCP_HOST=127.0.0.1 MCP_PORT=8080 python mcp_server.py
```

### Docker Configuration
```bash
# Using environment file
docker run -d --env-file .env -p 8001:8001 proxmox-mcp-server

# Using individual environment variables
docker run -d \
  -e PROXMOX_HOST=your-host \
  -e PROXMOX_USER=your-user \
  -e PROXMOX_PASSWORD=your-password \
  -p 8001:8001 \
  proxmox-mcp-server
```

## 🔧 Advanced Configuration

### Custom Configuration Module
Modify `src/config.py` for advanced customization:

```python
# Custom backup defaults
DEFAULT_BACKUP_COMPRESSION = "lzo"  # Instead of "zstd"
DEFAULT_BACKUP_MODE = "suspend"     # Instead of "snapshot"

# Custom VM defaults
DEFAULT_VM_CORES = 2               # Instead of 1
DEFAULT_VM_MEMORY = 1024           # Instead of 512
```

### Runtime Configuration
Some settings can be changed at runtime through the API:

```python
# Example: Override storage for specific operations
await service.create_vm(
    vmid="100",
    node="pve",
    name="test-vm",
    storage="fast-ssd"  # Override default storage
)
```

## 📝 Configuration Validation

The server validates configuration on startup:

1. **Required environment variables** are checked
2. **Proxmox connectivity** is tested
3. **Storage availability** is verified
4. **Network bridge existence** is confirmed (if specified)

## 🐛 Troubleshooting

### Common Configuration Issues

1. **Connection Failed**: Check `PROXMOX_HOST`, `PROXMOX_USER`, `PROXMOX_PASSWORD`
2. **Storage Not Found**: Verify storage exists and is accessible
3. **Network Bridge Error**: Ensure bridge exists on target node
4. **Permission Denied**: Check user permissions in Proxmox

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python mcp_server.py
```

### Configuration Test
Run the test suite to validate configuration:
```bash
python tests/comprehensive_mcp_test.py
```

## 📚 Related Documentation

- [README.md](README.md) - Main documentation
- [env.example](env.example) - Configuration template
- [src/config.py](src/config.py) - Configuration constants 