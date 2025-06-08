import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from sqlalchemy.orm import Session # For type hinting if needed for db_session
from app.models import ConnectionProfile, TestConfiguration, TestCaseResult, User
from app.services.proxmox_service import ProxmoxNonInteractiveService, ProxmoxAPIClientMock

# --- Fixtures specific to this test file ---

@pytest.fixture
def mock_db_session():
    """Mocks the SQLAlchemy session for service tests.
    Focuses on how the service prepares data, not actual DB commit for some unit tests.
    For integration tests, the real db_session from conftest might be used.
    """
    session = MagicMock(spec=Session)
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    # If your service queries the DB, you might need to mock query().filter().first() etc.
    # session.query = MagicMock()
    return session

@pytest.fixture
def service_connection_profile(test_user: User) -> ConnectionProfile: # Use test_user from conftest
    # Minimal profile for service instantiation
    return ConnectionProfile(
        id=1,
        name="Service Test Profile",
        host="mock.proxmox.com",
        port=8006,
        username="serviceuser",
        password_encrypted="encrypted_proxmox_password", # Will be "decrypted" by service
        realm="pve",
        owner_id=test_user.id # Ensure owner_id is set
    )

@pytest.fixture
def proxmox_service(service_connection_profile: ConnectionProfile, mock_db_session: MagicMock) -> ProxmoxNonInteractiveService:
    """Creates an instance of ProxmoxNonInteractiveService with a mocked DB and API client."""
    # The service's __init__ calls _connect, which instantiates ProxmoxAPIClientMock
    service = ProxmoxNonInteractiveService(connection_profile=service_connection_profile, db=mock_db_session)
    # Ensure the mock API client is attached if _connect was successful
    assert service.proxmox_api is not None
    assert isinstance(service.proxmox_api, ProxmoxAPIClientMock)
    return service

@pytest.fixture
def sample_test_config(service_connection_profile: ConnectionProfile, test_user: User) -> TestConfiguration:
    # Re-use parts of the conftest fixture but ensure it's distinct if needed
    return TestConfiguration(
        id=1,
        name="Service Test Config",
        target_node="pve1_mock", # Default node in mock API
        connection_profile_id=service_connection_profile.id,
        owner_id=test_user.id, # Ensure owner_id
        vm_id_range_start=9500,
        vm_network_bridge="vmbr_service_test",
        vm_cpu_cores=1, vm_ram_mb=512, # Minimal specs
        selected_tests={
            "Resource Discovery": {"List Resources": True},
            "VM Management": {"Create VM": True, "Get VM Status": True, "Delete VM (cleanup)": True}, # Assuming Delete VM is part of cleanup
            "Snapshot Management": {"Create Snapshot": True, "List Snapshots": True}
        },
        enable_destructive_tests=True,
        cleanup_resources=True
    )

# --- Test Cases ---

@pytest.mark.asyncio
async def test_service_connect_success(proxmox_service: ProxmoxNonInteractiveService):
    # _connect is called in __init__ by the fixture.
    # We primarily check if proxmox_api was initialized.
    assert proxmox_service.proxmox_api is not None
    # proxmox_service.proxmox_api.version_get() should not raise an error with the mock
    version_info = proxmox_service.proxmox_api.version_get()
    assert "version" in version_info

@pytest.mark.asyncio
async def test_execute_test_case_success(proxmox_service: ProxmoxNonInteractiveService, mock_db_session: MagicMock):
    test_run_id = 1
    category = "Test Category"
    test_name = "Successful Test"

    async def mock_test_func():
        await asyncio.sleep(0.01)
        return {'success': True, 'message': 'It worked!', 'data': {'key': 'value'}}

    success = await proxmox_service._execute_test_case(test_run_id, category, test_name, mock_test_func)

    assert success is True
    mock_db_session.add.assert_called_once()
    added_result = mock_db_session.add.call_args[0][0]
    assert isinstance(added_result, TestCaseResult)
    assert added_result.test_run_id == test_run_id
    assert added_result.category == category
    assert added_result.test_name == test_name
    assert added_result.status == "pass"
    assert added_result.message == "It worked!"
    assert "Data: {'key': 'value'}" in added_result.logs
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_execute_test_case_failure(proxmox_service: ProxmoxNonInteractiveService, mock_db_session: MagicMock):
    async def mock_test_func_fail():
        await asyncio.sleep(0.01)
        return {'success': False, 'message': 'It failed deliberately.', 'error': 'Custom error detail'}

    success = await proxmox_service._execute_test_case(1, "FailCat", "FailingTest", mock_test_func_fail)
    assert success is False
    added_result = mock_db_session.add.call_args[0][0]
    assert added_result.status == "fail"
    assert added_result.message == "It failed deliberately."
    assert "Error Details: Custom error detail" in added_result.logs

@pytest.mark.asyncio
async def test_execute_test_case_exception(proxmox_service: ProxmoxNonInteractiveService, mock_db_session: MagicMock):
    async def mock_test_func_exception():
        await asyncio.sleep(0.01)
        raise ValueError("Something broke badly")

    success = await proxmox_service._execute_test_case(1, "ErrorCat", "ExceptionTest", mock_test_func_exception)
    assert success is False # 'error' status means not successful
    added_result = mock_db_session.add.call_args[0][0]
    assert added_result.status == "error"
    assert "Exception: Something broke badly" in added_result.message
    assert "Traceback:" in added_result.logs

@pytest.mark.asyncio
async def test_list_resources_call(proxmox_service: ProxmoxNonInteractiveService):
    # This tests the individual test method directly
    target_node = "pve1_mock"
    # Mock the underlying Proxmox API call if needed, or rely on ProxmoxAPIClientMock
    with patch.object(proxmox_service.proxmox_api.cluster.resources, 'get', new_callable=AsyncMock) as mock_api_call:
        mock_api_call.return_value = [{'id': 'node/pve1_mock', 'type': 'node'}] # Simulate API response

        result = await proxmox_service.test_list_resources(target_node) # Pass the node argument

        assert result['success'] is True
        assert "Found 1 cluster resources" in result['message'] # Adjust based on actual message from mock
        mock_api_call.assert_called_once() # Verify the mock API was called

@pytest.mark.asyncio
async def test_create_vm_call_destructive_enabled(proxmox_service: ProxmoxNonInteractiveService, sample_test_config: TestConfiguration):
    sample_test_config.enable_destructive_tests = True # Ensure it's enabled
    target_node = sample_test_config.target_node
    vmid = sample_test_config.vm_id_range_start
    vm_name = f"mcp-test-{vmid}"

    # Mock the ProxmoxAPIClientMock's post method for qemu
    with patch.object(proxmox_service.proxmox_api.get_node(target_node).qemu, 'post', new_callable=AsyncMock) as mock_vm_create:
        mock_vm_create.return_value = f"UPID:{target_node}:FAKETASKID::qcreate:{vmid}:user@realm:" # Simulate task ID

        # Also mock _wait_for_task if it's called (it's commented out in the actual mock create)
        with patch.object(proxmox_service, '_wait_for_task', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = True # Simulate task success

            result = await proxmox_service.test_create_vm(sample_test_config, target_node, vmid, vm_name)

            assert result['success'] is True
            assert f"VM {vm_name} (ID: {vmid}) creation task started" in result['message']
            mock_vm_create.assert_called_once()
            # mock_wait.assert_called_once() # Uncomment if _wait_for_task is part of the flow

            # Check if resource was added for cleanup
            assert len(proxmox_service.created_resources_for_cleanup) == 1
            cleanup_entry = proxmox_service.created_resources_for_cleanup[0]
            assert cleanup_entry['type'] == 'vm'
            assert cleanup_entry['id'] == vmid


@pytest.mark.asyncio
async def test_run_selected_tests_orchestration(
    proxmox_service: ProxmoxNonInteractiveService,
    sample_test_config: TestConfiguration,
    mock_db_session: MagicMock
):
    test_run_id = 123
    sample_test_config.selected_tests = { # Define specific tests to run
        "Resource Discovery": {"List Resources": True},
        "VM Management": {"Create VM": True}, # Destructive, will run
    }
    sample_test_config.enable_destructive_tests = True

    # Mock individual test methods that would be called to isolate orchestration logic
    proxmox_service.test_list_resources = AsyncMock(return_value={'success': True, 'message': 'Listed'})
    proxmox_service.test_create_vm = AsyncMock(return_value={'success': True, 'message': 'Created'})
    proxmox_service.cleanup_created_resources_phase = AsyncMock() # Mock cleanup too

    await proxmox_service.run_selected_tests(sample_test_config, test_run_id)

    # Check that _execute_test_case was called for each selected test + connection test
    # mock_db_session.add.call_count should be number of tests + 1 (for connection)
    # Expected calls: Proxmox Connection, List Resources, Create VM
    assert mock_db_session.add.call_count >= 3

    # Verify that the actual test methods were called
    proxmox_service.test_list_resources.assert_called_once_with(sample_test_config.target_node)
    proxmox_service.test_create_vm.assert_called_once() # Args are more complex, check if needed

    # Verify cleanup was called
    proxmox_service.cleanup_created_resources_phase.assert_called_once_with(test_run_id, sample_test_config.target_node)


@pytest.mark.asyncio
async def test_run_selected_tests_destructive_disabled(
    proxmox_service: ProxmoxNonInteractiveService,
    sample_test_config: TestConfiguration,
    mock_db_session: MagicMock
):
    test_run_id = 124
    sample_test_config.selected_tests = {
        "VM Management": {"Create VM": True}
    }
    sample_test_config.enable_destructive_tests = False # DESTRUCTIVE DISABLED

    proxmox_service.test_create_vm = AsyncMock() # Should not be called
    proxmox_service._skip_test_case = AsyncMock() # This should be called

    await proxmox_service.run_selected_tests(sample_test_config, test_run_id)

    # Check that _skip_test_case was called for the destructive test
    # (Plus one for the initial connection test in _execute_test_case)
    # mock_db_session.add should be called for connection test and for skipped test
    assert mock_db_session.add.call_count >= 2
    proxmox_service._skip_test_case.assert_called_once()
    call_args_skip = proxmox_service._skip_test_case.call_args[0]
    assert call_args_skip[1] == "VM Management" # category
    assert "Create VM" in call_args_skip[2] # test_name
    assert "Destructive test disabled" in call_args_skip[3] # reason

    proxmox_service.test_create_vm.assert_not_called() # Ensure the actual destructive test wasn't


@pytest.mark.asyncio
async def test_cleanup_phase(proxmox_service: ProxmoxNonInteractiveService, mock_db_session: MagicMock):
    test_run_id = 125
    target_node = "pve_cleanup_node"
    vm_id_to_clean = 9001
    vm_name_to_clean = f"mcp-clean-{vm_id_to_clean}"

    # Populate created_resources_for_cleanup as if a VM was created
    proxmox_service.created_resources_for_cleanup = [
        {'type': 'vm', 'node': target_node, 'id': vm_id_to_clean, 'name': vm_name_to_clean}
    ]

    # Mock the specific delete call within the mock API
    # proxmox_service.proxmox_api.get_node(target_node).qemu is an instance of QemuMock
    # We want to mock the 'delete' method on that instance.
    # This requires knowing the structure of your mock.
    mock_qemu_delete = AsyncMock(return_value=f"UPID:{target_node}:TASKID::qmdelete:{vm_id_to_clean}:user@realm:")

    # Since get_node might be called multiple times, we need to ensure the mock is correctly set up.
    # Patching the QemuMock.delete method globally for this test might be easier if the node is dynamic.
    # For simplicity, if target_node is fixed for this test:
    proxmox_service.proxmox_api.get_node(target_node).qemu.delete = mock_qemu_delete

    # If _wait_for_task is part of the actual delete flow, mock it too.
    # For the mock, it's not directly called by the mock delete itself.

    await proxmox_service.cleanup_created_resources_phase(test_run_id, target_node)

    # Check _execute_test_case was called for the cleanup action
    # (meaning a TestCaseResult was added for the cleanup)
    assert mock_db_session.add.call_count >= 1
    added_result = mock_db_session.add.call_args[0][0]
    assert added_result.category == "Cleanup"
    assert f"Delete VM '{vm_name_to_clean}'" in added_result.test_name
    assert added_result.status == "pass" # Assuming mock delete is successful

    # Verify the actual delete on the (mocked) Proxmox API was called
    mock_qemu_delete.assert_called_once_with(vmid=vm_id_to_clean, force=1)

    assert len(proxmox_service.created_resources_for_cleanup) == 0 # List should be cleared
