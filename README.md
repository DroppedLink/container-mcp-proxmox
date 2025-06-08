# Proxmox MCP Server

A standards-compliant Model Context Protocol (MCP) server for managing Proxmox VE resources via Server-Sent Events (SSE). This server enables AI assistants and LLM applications (like Cursor IDE) to interact with Proxmox clusters through a clean, type-safe API.

## Features

- **SSE Transport Only**: Optimized for web clients like Cursor IDE
- **Full MCP Protocol Support**: Built with the official MCP Python SDK
- **Comprehensive Proxmox Management**:
  - **VM/Container Lifecycle**: Create, delete, start, stop, restart VMs and containers
  - **Resource Management**: Resize CPU, RAM, and disk resources dynamically
  - **Backup & Restore**: Full backup/restore operations with compression options
  - **Template & Cloning**: Convert VMs to templates and clone them
  - **Snapshot Management**: Create, delete, and list VM snapshots
  - **User & Permissions**: Manage users, roles, and access control
  - **Monitoring**: Get detailed resource status and cluster health

## Prerequisites

- Python 3.8+
- Access to a Proxmox VE cluster
- Valid Proxmox API credentials

## Installation

1. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd proxmox-mcp-server
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your Proxmox credentials
   ```

3. **Set your Proxmox credentials in `.env`:**
   ```bash
   PROXMOX_HOST=your-proxmox-host.example.com
   PROXMOX_USER=your-username@pam
   PROXMOX_PASSWORD=your-password
   PROXMOX_VERIFY_SSL=false
   ```

## Usage

### Start the Server

```bash
python simple_server.py
```

**Options:**
- `--host HOST` - Server host (default: 0.0.0.0)
- `--port PORT` - Server port (default: 8001)
- `--help` - Show help message

**Example:**
```bash
python simple_server.py --port 8001
```

### Test the Server

```bash
python quick_test.py
```

This will:
- Verify your Proxmox connection
- Test server connectivity
- Show available tools and resources
- Provide configuration instructions

## MCP Client Configuration

### Cursor IDE

1. Start the server: `python simple_server.py --port 8001`
2. In Cursor IDE settings, add MCP server:
   - **URL**: `http://localhost:8001`
   - **Transport**: `SSE`

### Other MCP Clients

The server exposes the standard MCP endpoints:
- **SSE Endpoint**: `http://localhost:8001/sse`
- **Messages Endpoint**: `http://localhost:8001/messages`

## Available Tools

### Core VM/Container Management
| Tool | Description | Parameters |
|------|-------------|------------|
| `list_resources` | List all VMs and containers | None |
| `get_resource_status` | Get VM/container details | `vmid`, `node` |
| `start_resource` | Start a VM/container | `vmid`, `node` |
| `stop_resource` | Stop a VM/container | `vmid`, `node` |
| `shutdown_resource` | Gracefully shutdown | `vmid`, `node` |
| `restart_resource` | Restart a VM/container | `vmid`, `node` |

### VM/Container Creation & Deletion
| Tool | Description | Parameters |
|------|-------------|------------|
| `create_vm` | Create a new VM | `vmid`, `node`, `name`, `cores?`, `memory?`, `disk_size?`, `storage?`, `iso_image?`, `os_type?`, `start_after_create?` |
| `create_container` | Create a new LXC container | `vmid`, `node`, `hostname`, `cores?`, `memory?`, `rootfs_size?`, `storage?`, `template?`, `password?`, `unprivileged?`, `start_after_create?` |
| `delete_resource` | Delete a VM or container | `vmid`, `node`, `force?` |

### Resource Management
| Tool | Description | Parameters |
|------|-------------|------------|
| `resize_resource` | Resize VM/container (CPU, RAM, disk) | `vmid`, `node`, `cores?`, `memory?`, `disk_size?` |

### Snapshot Management
| Tool | Description | Parameters |
|------|-------------|------------|
| `create_snapshot` | Create VM snapshot | `vmid`, `node`, `snapname`, `description?` |
| `delete_snapshot` | Delete VM snapshot | `vmid`, `node`, `snapname` |
| `get_snapshots` | List VM snapshots | `vmid`, `node` |

### Backup & Restore
| Tool | Description | Parameters |
|------|-------------|------------|
| `create_backup` | Create VM/container backup | `vmid`, `node`, `storage?`, `mode?`, `compress?`, `notes?` |
| `list_backups` | List available backups | `node?`, `storage?` |
| `restore_backup` | Restore from backup | `archive`, `vmid`, `node`, `storage?`, `force?` |

### Template & Clone Management  
| Tool | Description | Parameters |
|------|-------------|------------|
| `create_template` | Convert VM to template | `vmid`, `node` |
| `clone_vm` | Clone VM or template | `vmid`, `newid`, `node`, `name?`, `target_node?`, `full_clone?`, `storage?` |
| `list_templates` | List all VM templates | None |

### User & Permission Management
| Tool | Description | Parameters |
|------|-------------|------------|
| `create_user` | Create new Proxmox user | `userid`, `password?`, `email?`, `firstname?`, `lastname?`, `groups?`, `enable?` |
| `delete_user` | Delete Proxmox user | `userid` |
| `list_users` | List all users | None |
| `set_permissions` | Set user/group permissions | `path`, `roleid`, `userid?`, `groupid?`, `propagate?` |
| `list_roles` | List available roles | None |
| `list_permissions` | List current permissions | None |

## Available Resources

| Resource URI | Description |
|--------------|-------------|
| `proxmox://cluster/status` | Cluster information and health |
| `proxmox://nodes/status` | Node status and resource usage |

## Example Usage in Cursor IDE

Once configured, you can ask Cursor IDE to perform complex Proxmox operations:

### Basic Operations
- "List all my Proxmox VMs and containers"
- "Show me the status of VM 100"
- "Start VM 101 and show me its status"
- "What's the current cluster status?"

### VM/Container Creation
- "Create a new VM with ID 200 on node pve1, name 'web-server', 2 cores, 2GB RAM"
- "Create a container with ID 300 on node pve2, hostname 'app-container'"
- "Delete VM 199 (use force if needed)"

### Resource Management
- "Resize VM 100 to have 4 cores and 4GB RAM"
- "Expand the disk of VM 100 by 10GB"

### Backup & Restore
- "Create a backup of VM 100 on node pve1"
- "List all available backups"
- "Restore VM from backup '/var/lib/vz/dump/vzdump-qemu-100-2024_01_01-10_00_00.vma.zst'"

### Templates & Cloning
- "Convert VM 100 to a template"
- "Clone template 100 to create new VM 201 named 'web-clone'"
- "List all available templates"

### Snapshots
- "Create a snapshot called 'before-update' for VM 100"
- "List all snapshots for VM 100"
- "Delete snapshot 'old-snap' from VM 100"

### User Management
- "Create a user 'john@pve' with email 'john@company.com'"
- "List all Proxmox users"
- "Set permissions for user 'john@pve' on path '/vms/100' with role 'PVEVMUser'"
- "List all available roles and permissions"

## Troubleshooting

### Connection Issues

1. **Check environment variables**: Run `python quick_test.py`
2. **Test Proxmox access**: Ensure your credentials are correct
3. **Check SSL settings**: Set `PROXMOX_VERIFY_SSL=false` for self-signed certificates
4. **Firewall**: Ensure port 8001 is accessible

### Server Issues

1. **Port in use**: Try a different port with `--port 8002`
2. **Permission errors**: Ensure Python virtual environment is activated
3. **Dependencies**: Reinstall with `pip install -r requirements.txt`

### MCP Client Issues

1. **URL format**: Use `http://localhost:8001` (not `https://`)
2. **Transport**: Ensure "SSE" is selected in client settings
3. **Server running**: Verify server is active with `curl http://localhost:8001`

## Development

### Project Structure

```
├── simple_server.py       # Main SSE server
├── quick_test.py          # Test suite
├── src/
│   ├── service.py         # Proxmox service layer
│   └── models.py          # Data models
├── requirements.txt       # Dependencies
└── README.md             # This file
```

### Adding New Tools

1. Add async function to `simple_server.py`
2. Decorate with `@mcp.tool()`
3. Add proper error handling
4. Update this README

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request