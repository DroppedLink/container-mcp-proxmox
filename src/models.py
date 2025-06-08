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