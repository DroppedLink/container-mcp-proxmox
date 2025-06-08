import asyncio
import time
import traceback # For more detailed error logging
from datetime import datetime, timezone
from app import models, schemas # For type hinting and DB model interaction
from sqlalchemy.orm import Session
# from proxmoxer import ProxmoxAPI # Example if using proxmoxer

# Placeholder for Proxmox connection details decryption
def get_decrypted_password(encrypted_password: str) -> str:
    if not encrypted_password: return ""
    if encrypted_password.startswith("encrypted_"): # Placeholder encryption
        return encrypted_password.split("encrypted_", 1)[1]
    return encrypted_password

class ProxmoxAPIClientMock:
    """
    A mock for the Proxmox API client for development without a live Proxmox server.
    Replace this with the actual Proxmox API client (e.g., proxmoxer.ProxmoxAPI).
    """
    def __init__(self, host, port, user, password, realm, verify_ssl):
        self.host = host
        self.user = user
        print(f"MockProxmoxAPI: Initialized for {host}:{port}, user {user}@{realm}, verify_ssl={verify_ssl}")
        # Simulate a nodes attribute similar to proxmoxer
        self.nodes = {
            "pve1_mock": NodeMock("pve1_mock", self),
            "pve2_mock": NodeMock("pve2_mock", self),
        }
        self.cluster = ClusterMock(self)

    def get_node(self, node_name: str):
        # Helper to get a node, creating if it doesn't exist for dynamic node names from config
        if node_name not in self.nodes:
            self.nodes[node_name] = NodeMock(node_name, self)
            print(f"MockProxmoxAPI: Dynamically created mock node '{node_name}'")
        return self.nodes[node_name]

    def version_get(self): # Renamed from version.get() for direct call
        print("MockProxmoxAPI: version.get() called")
        return {"version": "mock-pve-7.4", "repoid": "mock"}

class ClusterMock:
    def __init__(self, api_client):
        self._api_client = api_client
        self.resources = ResourcesMock(api_client)

class ResourcesMock:
    def __init__(self, api_client):
        self._api_client = api_client
        self._resources_data = [
            {'id': 'node/pve1_mock', 'type': 'node', 'node': 'pve1_mock', 'status': 'online'},
            {'id': 'storage/pve1_mock/local', 'type': 'storage', 'node': 'pve1_mock', 'storage': 'local'},
            {'id': 'qemu/100', 'type': 'qemu', 'node': 'pve1_mock', 'vmid': 100, 'name': 'test-vm100', 'status': 'stopped'},
        ]
    async def get(self, type=None): # type is a filter parameter
        print(f"MockProxmoxAPI: cluster.resources.get(type={type}) called")
        await asyncio.sleep(0.1)
        if type:
            return [res for res in self._resources_data if res['type'] == type]
        return self._resources_data

class NodeMock:
    def __init__(self, name, api_client):
        self.name = name
        self._api_client = api_client
        self.qemu = QemuMock(name, api_client)
        self.lxc = LxcMock(name, api_client)
        self.storage = StorageMock(name, api_client)
        self.tasks = TasksMock(name, api_client)
        # Add other node-level categories like 'services', 'network', etc. as needed

    async def get(self): # Mock for node status
        print(f"MockProxmoxAPI: nodes({self.name}).get() called")
        await asyncio.sleep(0.05)
        return {"status": "online", "cpu": 0.1, "maxcpu": 4, "mem": 1024*1024*1024, "maxmem": 4*1024*1024*1024}

class QemuMock:
    def __init__(self, node_name, api_client):
        self.node_name = node_name
        self._api_client = api_client
        self._vms = {} # Store mock VMs state: vmid -> {config}

    async def get(self, vmid=None): # Get all VMs on node or specific VM
        print(f"MockProxmoxAPI: nodes({self.node_name}).qemu.get(vmid={vmid}) called")
        await asyncio.sleep(0.1)
        if vmid:
            vm_info = self._vms.get(int(vmid))
            if vm_info: return vm_info
            # Simulate Proxmox error for non-existent VM
            raise Exception(f"Mock Proxmox Error: VM {vmid} not found (500)")
        return list(self._vms.values())

    async def post(self, **params): # Create VM
        vmid = params.get('vmid')
        if not vmid: raise ValueError("vmid is required for VM creation")
        vmid = int(vmid)
        if vmid in self._vms: raise Exception(f"Mock Proxmox Error: VM {vmid} already exists")

        config = {**params, 'node': self.node_name, 'status': 'stopped', 'type': 'qemu'}
        self._vms[vmid] = config
        print(f"MockProxmoxAPI: nodes({self.node_name}).qemu.post() called to create VM {vmid} with params {params}")
        await asyncio.sleep(0.5)
        # Proxmox API returns task UPID
        return f"UPID:{self.node_name}:HEXHEX:HEXHEX:HEXHEX:qcreate:{vmid}:user@realm:"

    async def delete(self, vmid: int, **params):
        vmid = int(vmid)
        if vmid not in self._vms: raise Exception(f"Mock Proxmox Error: VM {vmid} not found for deletion")
        del self._vms[vmid]
        print(f"MockProxmoxAPI: nodes({self.node_name}).qemu({vmid}).delete() called with params {params}")
        await asyncio.sleep(0.3)
        return f"UPID:{self.node_name}:HEXHEX:HEXHEX:HEXHEX:qmdestroy:{vmid}:user@realm:"

    # Mock for snapshot creation
    async def snapshot_post(self, vmid: int, snapname: str, **params): # proxmoxer uses node.qemu(vmid).snapshot.post(snapname=...)
        vmid = int(vmid)
        if vmid not in self._vms: raise Exception(f"Mock Proxmox Error: VM {vmid} not found for snapshot")
        if 'snapshots' not in self._vms[vmid]: self._vms[vmid]['snapshots'] = []
        self._vms[vmid]['snapshots'].append({'name': snapname, **params})
        print(f"MockProxmoxAPI: VM {vmid} snapshot '{snapname}' created with params {params}")
        await asyncio.sleep(0.2)
        return f"UPID:{self.node_name}:HEXHEX:HEXHEX:HEXHEX:qmsnapshot:{vmid}:user@realm:"

    # Mock for listing snapshots
    async def snapshot_get(self, vmid: int):
        vmid = int(vmid)
        if vmid not in self._vms: raise Exception(f"Mock Proxmox Error: VM {vmid} not found for listing snapshots")
        print(f"MockProxmoxAPI: VM {vmid} list snapshots called")
        await asyncio.sleep(0.1)
        return self._vms[vmid].get('snapshots', [])

class LxcMock: # Similar structure to QemuMock
    def __init__(self, node_name, api_client):
        self.node_name = node_name
        self._api_client = api_client
    # ... methods for LXC ...

class StorageMock:
    def __init__(self, node_name, api_client):
        self.node_name = node_name
        self._api_client = api_client
        self._storages = [ # Default storages for any node
            {'storage': 'local', 'type': 'dir', 'content': 'images,iso,vztmpl,backup,snippets', 'maxdisk': 100*1024**3, 'used': 20*1024**3},
            {'storage': 'local-lvm', 'type': 'lvmthin', 'content': 'images,rootdir', 'maxdisk': 200*1024**3, 'used': 50*1024**3},
        ]
    async def get(self, storage_name=None):
        print(f"MockProxmoxAPI: nodes({self.node_name}).storage.get(storage={storage_name}) called")
        await asyncio.sleep(0.1)
        if storage_name:
            for s in self._storages:
                if s['storage'] == storage_name: return s
            raise Exception(f"Mock Proxmox Error: Storage '{storage_name}' not found.")
        return self._storages

class TasksMock:
    def __init__(self, node_name, api_client):
        self.node_name = node_name
        self._api_client = api_client
    async def status_get(self, upid: str): # proxmoxer: node.tasks(upid).status.get()
        print(f"MockProxmoxAPI: nodes({self.node_name}).tasks('{upid}').status.get() called")
        await asyncio.sleep(0.02) # Tasks are quick to check
        # Simulate task completion
        return {'status': 'stopped', 'exitstatus': 'OK'}


class ProxmoxNonInteractiveService:
    def __init__(self, connection_profile: models.ConnectionProfile, db: Session):
        self.host = connection_profile.host
        self.port = connection_profile.port
        self.username = connection_profile.username
        self.password = get_decrypted_password(connection_profile.password_encrypted)
        self.realm = connection_profile.realm
        self.verify_ssl = connection_profile.verify_ssl
        self.db = db
        self.proxmox_api = None # This will hold the ProxmoxAPI client instance
        self.created_resources_for_cleanup = [] # List of tuples: (type, node, vmid/id, name)
        self._connect()

    def _connect(self):
        """Initialize Proxmox API client."""
        try:
            # Replace ProxmoxAPI with ProxmoxAPIClientMock for testing without live server
            # self.proxmox_api = ProxmoxAPI(
            self.proxmox_api = ProxmoxAPIClientMock(
                self.host, port=self.port,
                user=self.username, password=self.password, realm=self.realm,
                verify_ssl=self.verify_ssl
            )
            # Test connection - e.g., fetch version (actual API might raise error)
            version_info = self.proxmox_api.version_get() # Adjusted for mock
            print(f"Successfully connected to Proxmox (mock): {self.host}. Version: {version_info}")
        except Exception as e:
            print(f"Failed to connect to Proxmox (mock): {e}")
            # This error will be caught by the first test case that tries to use self.proxmox_api
            # Or, can be raised here and caught by the Celery task to mark the run as failed early.
            # For now, let _execute_test_case handle it.
            self.proxmox_api = None # Ensure it's None if connection fails

    async def _wait_for_task(self, node_id: str, upid: str, timeout: int = 300):
        """Waits for a Proxmox task to complete."""
        print(f"Mock: Waiting for task {upid} on node {node_id}...")
        if not self.proxmox_api: raise ConnectionError("Proxmox API not connected.")

        node_client = self.proxmox_api.get_node(node_id) # Adjusted for mock
        for _ in range(timeout // 5): # Check every 5 seconds
            task_status = await node_client.tasks.status_get(upid=upid) # Adjusted for mock
            if task_status['status'] == 'stopped':
                if task_status.get('exitstatus') == 'OK':
                    print(f"Mock: Task {upid} completed successfully.")
                    return True
                else:
                    raise Exception(f"Mock: Task {upid} failed with status: {task_status.get('exitstatus')}")
            await asyncio.sleep(0.1) # Faster polling for mock
        raise TimeoutError(f"Mock: Task {upid} timed out after {timeout}s (simulated).")

    async def _execute_test_case(self, test_run_id: int, category: str, test_name: str, test_func, *args, **kwargs):
        start_time_tc = time.perf_counter()
        status = "pass"
        message = ""
        logs = ""

        if not self.proxmox_api and test_name != "Proxmox Connection": # Allow connection test to report failure
            status = "error"
            message = "Proxmox API client not initialized. Connection likely failed during service setup."
        else:
            try:
                test_result = await test_func(*args, **kwargs) # All test functions are async now

                if isinstance(test_result, dict): # Expected return type
                    if test_result.get('success', False):
                        status = "pass"
                        message = test_result.get('message', "Test executed successfully.")
                        if test_result.get('data'):
                            logs += f"Data: {str(test_result.get('data'))[:1500]}\n" # Limit log data length
                    else:
                        status = "fail"
                        message = test_result.get('message', "Test failed as per custom logic.")
                        if test_result.get('error'):
                             logs += f"Error Details: {test_result.get('error')}\n"
                else: # Should not happen
                    status = "error"
                    message = "Test function returned an unexpected result type."
                    logs += f"Unexpected result: {test_result}\n"
            except Exception as e:
                status = "error"
                message = f"Exception: {str(e)}"
                logs += f"Traceback: {traceback.format_exc()}\n"
                print(f"Error in {category} - {test_name}: {e}")

        duration_seconds = time.perf_counter() - start_time_tc

        tc_result_obj = models.TestCaseResult(
            test_run_id=test_run_id, category=category, test_name=test_name,
            status=status, duration_seconds=duration_seconds, message=message,
            logs=logs.strip() if logs else None, created_at=datetime.now(timezone.utc)
        )
        self.db.add(tc_result_obj)
        self.db.commit()
        return status == "pass"


    async def run_selected_tests(self, test_config: models.TestConfiguration, test_run_id: int):
        """Main method to execute tests based on the configuration."""

        # Initial connection check as a "test case"
        if not self.proxmox_api:
            await self._execute_test_case(test_run_id, "Setup", "Proxmox Connection",
                                          lambda: {'success': False, 'message': "Failed to initialize Proxmox API client during service setup."})
            return # Stop further tests if connection failed

        print(f"Running tests for config: {test_config.name} on node: {test_config.target_node}")
        selected_tests_map = test_config.selected_tests or {}
        target_node = test_config.target_node # Primary node for tests

        # --- Resource Discovery ---
        cat_rd = "Resource Discovery"
        if selected_tests_map.get(cat_rd, {}).get("List Resources", False):
            await self._execute_test_case(test_run_id, cat_rd, "List Resources", self.test_list_resources, target_node)

        # --- VM Management ---
        cat_vm = "VM Management"
        vm_tests_config = selected_tests_map.get(cat_vm, {})
        # Use a specific VM ID for testing, from config or generate one
        test_vmid = test_config.vm_id_range_start
        vm_name = f"mcp-test-{test_vmid}"

        if vm_tests_config.get("Create VM", False):
            if test_config.enable_destructive_tests:
                await self._execute_test_case(test_run_id, cat_vm, f"Create VM {vm_name}",
                                              self.test_create_vm, test_config, target_node, test_vmid, vm_name)
            else:
                await self._skip_test_case(test_run_id, cat_vm, f"Create VM {vm_name}", "Destructive test disabled.")

        if vm_tests_config.get("Get VM Status", False) and test_config.enable_destructive_tests: # Assuming VM was created
            await self._execute_test_case(test_run_id, cat_vm, f"Get VM Status {vm_name}", self.test_get_vm_status, target_node, test_vmid)

        # --- Snapshot Management ---
        cat_snap = "Snapshot Management"
        snap_tests_config = selected_tests_map.get(cat_snap, {})
        snap_name = f"testsnap-{int(time.time())}"

        if snap_tests_config.get("Create Snapshot", False) and test_config.enable_destructive_tests:
            # Prerequisite: VM must exist (created in a previous step or pre-existing if not cleaning up)
            await self._execute_test_case(test_run_id, cat_snap, f"Create Snapshot {snap_name} for VM {vm_name}",
                                          self.test_create_snapshot, target_node, test_vmid, snap_name)

        if snap_tests_config.get("List Snapshots", False) and test_config.enable_destructive_tests:
             await self._execute_test_case(test_run_id, cat_snap, f"List Snapshots for VM {vm_name}",
                                          self.test_list_snapshots, target_node, test_vmid)

        # --- Storage Management ---
        cat_storage = "Storage Management"
        if selected_tests_map.get(cat_storage, {}).get("List Storage", False):
            await self._execute_test_case(test_run_id, cat_storage, "List Storage on Node", self.test_list_storage, target_node)

        # ... (Many other test categories and specific tests would be added here, following the pattern) ...

        # --- Cleanup (must be the last step related to resource modification) ---
        if test_config.enable_destructive_tests and test_config.cleanup_resources:
            await self.cleanup_created_resources_phase(test_run_id, target_node) # Pass target_node for clarity

        print(f"Finished all selected tests for run ID: {test_run_id}")

    async def _skip_test_case(self, test_run_id: int, category: str, test_name: str, reason: str):
        tc_result_obj = models.TestCaseResult(
            test_run_id=test_run_id, category=category, test_name=test_name,
            status="skipped", duration_seconds=0, message=reason,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(tc_result_obj)
        self.db.commit()

    # --- Adapted Test Methods (Examples) ---
    async def test_list_resources(self, node: str): # Changed node to target_node for clarity
        # resources = await self.proxmox_api.cluster.resources.get() # Corrected for mock
        # return {'success': True, 'message': f'Found {len(resources)} cluster resources.', 'data': resources}
        await asyncio.sleep(0.1) # Simulate API call
        mock_data = [{'id': f'node/{node}', 'type': 'node'}, {'id': f'qemu/123', 'node': node}]
        return {'success': True, 'message': f'Simulated: Found {len(mock_data)} resources on cluster (visible from {node}).', 'data': mock_data}

    async def test_create_vm(self, test_config: models.TestConfiguration, node: str, vmid: int, vm_name: str):
        params = {
            'vmid': vmid, 'name': vm_name,
            'cores': test_config.vm_cpu_cores, 'memory': test_config.vm_ram_mb,
            'net0': f'virtio,bridge={test_config.vm_network_bridge or "vmbr0_mock"}', # Default mock bridge
            # 'ide2': f'{test_config.vm_os_image},media=cdrom', # Requires image on storage
            # 'scsi0': f'{test_config.vm_storage_pool or "local-lvm_mock"}:{test_config.vm_disk_gb}G', # Requires storage
        }
        # task_upid = await self.proxmox_api.get_node(node).qemu.post(**params) # Adjusted for mock
        # await self._wait_for_task(node, task_upid)
        await self.proxmox_api.get_node(node).qemu.post(**params) # Mock create
        self.created_resources_for_cleanup.append({'type': 'vm', 'node': node, 'id': vmid, 'name': vm_name})
        return {'success': True, 'message': f'VM {vm_name} (ID: {vmid}) creation task started.', 'data': params}

    async def test_get_vm_status(self, node: str, vmid: int):
        # status = await self.proxmox_api.get_node(node).qemu(vmid).status.get('current') # proxmoxer: node.qemu(vmid).status.current.get()
        # return {'success': True, 'message': f'VM {vmid} status: {status.get("status")}', 'data': status}
        vm_info = await self.proxmox_api.get_node(node).qemu.get(vmid=vmid) # Mock get
        return {'success': True, 'message': f'Simulated: VM {vmid} status is {vm_info.get("status", "unknown")}', 'data': vm_info}

    async def test_create_snapshot(self, node: str, vmid: int, snap_name: str):
        # task_upid = await self.proxmox_api.get_node(node).qemu(vmid).snapshot.post(snapname=snap_name, description='Test snapshot')
        # await self._wait_for_task(node, task_upid)
        await self.proxmox_api.get_node(node).qemu.snapshot_post(vmid=vmid, snapname=snap_name, description='Test snapshot by MCP') # Mock
        self.created_resources_for_cleanup.append({'type': 'snapshot', 'node': node, 'vmid': vmid, 'id': snap_name, 'name': snap_name})
        return {'success': True, 'message': f'Snapshot {snap_name} for VM {vmid} created.', 'data': {'vmid': vmid, 'snap_name': snap_name}}

    async def test_list_snapshots(self, node: str, vmid: int):
        # snapshots = await self.proxmox_api.get_node(node).qemu(vmid).snapshot.get()
        snapshots = await self.proxmox_api.get_node(node).qemu.snapshot_get(vmid=vmid) # Mock
        return {'success': True, 'message': f'Found {len(snapshots)} snapshots for VM {vmid}.', 'data': snapshots}

    async def test_list_storage(self, node: str):
        # storages = await self.proxmox_api.get_node(node).storage.get()
        storages = await self.proxmox_api.get_node(node).storage.get() # Mock
        return {'success': True, 'message': f'Found {len(storages)} storages on node {node}.', 'data': storages}

    async def cleanup_created_resources_phase(self, test_run_id: int, target_node_for_logging: str):
        """Cleans up resources created during the test run. Logs actions as test cases."""
        category = "Cleanup"
        print(f"Cleanup Phase: Will attempt to delete {len(self.created_resources_for_cleanup)} created resources.")

        # Sort for cleanup: snapshots before VMs, etc. (simple sort by type for now)
        # More complex dependency management might be needed in real scenarios.
        self.created_resources_for_cleanup.sort(key=lambda x: (x['type'] != 'snapshot', x['type'] != 'vm'))


        for resource in reversed(self.created_resources_for_cleanup): # Often good to delete in reverse order of creation
            res_type = resource['type']
            res_node = resource['node']
            res_id = resource['id'] # This is VMID for VMs, snapname for snapshots
            res_name = resource['name']

            test_name_cleanup = f"Delete {res_type.capitalize()} '{res_name}' (ID/Name: {res_id}) on {res_node}"

            async def cleanup_action(): # Define async closure for _execute_test_case
                if res_type == 'vm':
                    # await self.proxmox_api.get_node(res_node).qemu(res_id).delete(force=True) # Might need force=1
                    await self.proxmox_api.get_node(res_node).qemu.delete(vmid=res_id, force=1) # Mock
                    return {'success': True, 'message': f'VM {res_name} deleted.'}
                elif res_type == 'snapshot':
                    vmid = resource['vmid'] # Snapshots need VMID context
                    # await self.proxmox_api.get_node(res_node).qemu(vmid).snapshot(res_id).delete() # proxmoxer: snapshot(snapname).delete()
                    # Mock logic for deleting snapshot (not explicitly in mock client, assume success)
                    print(f"Mock: Deleting snapshot '{res_id}' for VM {vmid} on node {res_node}")
                    await asyncio.sleep(0.1)
                    return {'success': True, 'message': f'Snapshot {res_name} for VM {vmid} deleted.'}
                # Add other resource types like 'container', 'user', 'pool'
                return {'success': False, 'message': f'Unknown resource type "{res_type}" for cleanup.'}

            await self._execute_test_case(test_run_id, category, test_name_cleanup, cleanup_action)

        self.created_resources_for_cleanup.clear()
        print("Cleanup phase finished.")
