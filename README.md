# Proxmox MCP Server

A standards-compliant Model Context Protocol (MCP) server for managing Proxmox VE resources via Server-Sent Events (SSE). This server enables AI assistants and LLM applications (like Cursor IDE) to interact with Proxmox clusters through a clean, type-safe API.

## Features

- **SSE Transport Only**: Optimized for web clients like Cursor IDE
- **Full MCP Protocol Support**: Built with the official MCP Python SDK
- **Comprehensive Proxmox Management**:
  - List all VMs and containers
  - Get detailed resource status
  - Start, stop, shutdown, and restart resources
  - Create and manage snapshots
  - Monitor cluster and node status

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

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_resources` | List all VMs and containers | None |
| `get_resource_status` | Get VM/container details | `vmid`, `node` |
| `start_resource` | Start a VM/container | `vmid`, `node` |
| `stop_resource` | Stop a VM/container | `vmid`, `node` |
| `shutdown_resource` | Gracefully shutdown | `vmid`, `node` |
| `restart_resource` | Restart a VM/container | `vmid`, `node` |
| `create_snapshot` | Create VM snapshot | `vmid`, `node`, `snapname`, `description?` |
| `delete_snapshot` | Delete VM snapshot | `vmid`, `node`, `snapname` |
| `get_snapshots` | List VM snapshots | `vmid`, `node` |

## Available Resources

| Resource URI | Description |
|--------------|-------------|
| `proxmox://cluster/status` | Cluster information and health |
| `proxmox://nodes/status` | Node status and resource usage |

## Example Usage in Cursor IDE

Once configured, you can ask Cursor IDE:

- "List all my Proxmox VMs"
- "Show me the status of VM 100"
- "Create a snapshot called 'backup-2024' for VM 100"
- "What's the current cluster status?"

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