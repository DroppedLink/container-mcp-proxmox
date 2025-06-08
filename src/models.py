# src/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict, Literal

# --- Proxmox Resource Models ---

class ProxmoxResource(BaseModel):
    vmid: str
    name: str
    type: Literal["qemu", "lxc"]
    status: str
    node: str
    uptime: int

class ResourceIdentifier(BaseModel):
    node: str
    vmid: str

class ResourceStatusResult(ProxmoxResource):
    cpu: Optional[float] = 0
    memory: Optional[int] = 0
    disk: Optional[int] = 0

class CreateSnapshotParams(BaseModel):
    vmid: str
    node: str
    snapname: str
    description: Optional[str] = ""

class DeleteSnapshotParams(BaseModel):
    vmid: str
    node: str
    snapname: str

class OperationStatus(BaseModel):
    status: str
    message: Optional[str] = None
    task_id: Optional[str] = None

class ListResourcesResult(BaseModel):
    resources: List[ProxmoxResource]

# --- New Models for Extended Features ---

# VM/CT Creation Models
class CreateVMParams(BaseModel):
    vmid: str
    node: str
    name: str
    cores: Optional[int] = None
    memory: Optional[int] = None  # MB
    disk_size: Optional[str] = None
    storage: Optional[str] = None
    iso_image: Optional[str] = None
    os_type: Optional[str] = None  # Linux 2.6+
    start_after_create: Optional[bool] = False

class CreateCTParams(BaseModel):
    vmid: str
    node: str
    hostname: str
    cores: Optional[int] = None
    memory: Optional[int] = None  # MB
    rootfs_size: Optional[str] = None
    storage: Optional[str] = None
    template: Optional[str] = None
    password: Optional[str] = None
    unprivileged: Optional[bool] = True
    start_after_create: Optional[bool] = False

# Resource Resizing Models
class ResizeResourceParams(BaseModel):
    vmid: str
    node: str
    cores: Optional[int] = None
    memory: Optional[int] = None  # MB
    disk_size: Optional[str] = None  # e.g., "+2G" for expansion

# Backup Models
class CreateBackupParams(BaseModel):
    vmid: str
    node: str
    storage: Optional[str] = "local"
    mode: Optional[Literal["snapshot", "suspend", "stop"]] = "snapshot"
    compress: Optional[Literal["none", "lzo", "gzip", "zstd"]] = "zstd"
    notes: Optional[str] = ""

class RestoreBackupParams(BaseModel):
    archive: str  # backup file path
    vmid: str
    node: str
    storage: Optional[str] = None
    force: Optional[bool] = False

# Template and Clone Models
class CreateTemplateParams(BaseModel):
    vmid: str
    node: str

class CloneVMParams(BaseModel):
    vmid: str  # source VM
    newid: str  # new VM ID
    node: str
    name: Optional[str] = None
    target_node: Optional[str] = None
    full_clone: Optional[bool] = True
    storage: Optional[str] = None

# User and Role Management Models
class CreateUserParams(BaseModel):
    userid: str  # format: user@realm
    password: Optional[str] = None
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    groups: Optional[List[str]] = []
    enable: Optional[bool] = True

class UpdateUserParams(BaseModel):
    userid: str
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    groups: Optional[List[str]] = None
    enable: Optional[bool] = None

class SetPermissionParams(BaseModel):
    path: str  # e.g., "/vms/100", "/nodes/pve"
    userid: Optional[str] = None
    groupid: Optional[str] = None
    roleid: str
    propagate: Optional[bool] = True

# Storage Models
class StorageContentParams(BaseModel):
    storage_name: str
    node: str
    content_type: Optional[str] = ""

class SuitableStorageParams(BaseModel):
    node: str
    content_type: str
    min_free_gb: Optional[float] = 0

# Task Management Models
class TaskListParams(BaseModel):
    node: Optional[str] = ""
    limit: Optional[int] = 20
    running_only: Optional[bool] = False

class TaskStatusParams(BaseModel):
    node: str
    upid: str

class CancelTaskParams(BaseModel):
    node: str
    upid: str

class BackupJobParams(BaseModel):
    node: str
    schedule: str
    vmid: Optional[str] = ""
    storage: Optional[str] = "local"
    enabled: Optional[bool] = True
    comment: Optional[str] = ""
    mailto: Optional[str] = ""
    compress: Optional[str] = "zstd"
    mode: Optional[str] = "snapshot"

# Cluster Management Models
class NodeStatusParams(BaseModel):
    node: str

class ClusterResourcesParams(BaseModel):
    resource_type: Optional[str] = ""

class MigrateVMParams(BaseModel):
    vmid: str
    source_node: str
    target_node: str
    online: Optional[bool] = True
    force: Optional[bool] = False

class NodeMaintenanceParams(BaseModel):
    node: str
    maintenance: bool
    reason: Optional[str] = "Maintenance mode"

# Monitoring Models
class VMStatsParams(BaseModel):
    vmid: str
    node: str
    timeframe: Optional[str] = "hour"

class NodeStatsParams(BaseModel):
    node: str
    timeframe: Optional[str] = "hour"

class StorageStatsParams(BaseModel):
    storage: str
    node: str
    timeframe: Optional[str] = "hour"

class AlertsParams(BaseModel):
    node: Optional[str] = ""

class ResourceUsageParams(BaseModel):
    node: Optional[str] = ""

# Network Management Models
class NetworkListParams(BaseModel):
    node: Optional[str] = ""

class NetworkConfigParams(BaseModel):
    node: str
    interface: str

class NodeNetworkParams(BaseModel):
    node: str

class FirewallRulesParams(BaseModel):
    node: Optional[str] = ""
    vmid: Optional[str] = ""

class FirewallStatusParams(BaseModel):
    node: Optional[str] = ""
    vmid: Optional[str] = ""