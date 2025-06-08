import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.tasks import run_mcp_tests_task # The Celery task to test
from app.models import TestRun, TestConfiguration, ConnectionProfile, User, TestCaseResult
from app.services.proxmox_service import ProxmoxNonInteractiveService # To mock this service

# --- Fixtures for Task Testing (can also be in conftest.py if widely used) ---

@pytest.fixture
def mock_db_session_for_task():
    """ Mocks a SQLAlchemy session specifically for task testing. """
    db_session = MagicMock(spec=Session) # Using spec=Session is not working here, use direct MagicMock
    db_session.query = MagicMock()
    db_session.add = MagicMock()
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()
    db_session.close = MagicMock()
    return db_session

@pytest.fixture
def mock_session_local_for_task(mock_db_session_for_task: MagicMock):
    """ Mocks SessionLocal to return our mock_db_session_for_task. """
    # Patch 'app.tasks.SessionLocal' which is used by get_task_db_session in tasks.py
    with patch('app.tasks.SessionLocal', return_value=mock_db_session_for_task) as mock_sl:
        yield mock_sl

@pytest.fixture
def mock_proxmox_service_for_task():
    """ Mocks the ProxmoxNonInteractiveService. """
    # The service methods are async, so use AsyncMock for them
    mock_service_instance = AsyncMock(spec=ProxmoxNonInteractiveService)
    # mock_service_instance.run_selected_tests = AsyncMock() # This is the main method we'll control

    # If __init__ or _connect does something critical, mock that too, but usually we mock the instance
    # For this test, we'll mock the class so we can inspect its instantiation
    with patch('app.tasks.ProxmoxNonInteractiveService', return_value=mock_service_instance) as mock_service_class:
        yield mock_service_class, mock_service_instance


# --- Test Cases for run_mcp_tests_task ---

def test_run_mcp_tests_task_success(
    mock_session_local_for_task: MagicMock, # Ensures SessionLocal is mocked
    mock_db_session_for_task: MagicMock,    # The actual session mock to configure
    mock_proxmox_service_for_task: tuple    # Tuple of (MockedClass, MockedInstance)
):
    mock_proxmox_service_class, mock_proxmox_service_instance = mock_proxmox_service_for_task
    test_run_id = 1

    # Setup mock TestRun, TestConfiguration, ConnectionProfile data
    mock_user = User(id=1, username="task_user")
    mock_conn_profile = ConnectionProfile(id=1, host="task.host", username="task_p_user", password_encrypted="enc", realm="pve", owner_id=mock_user.id)
    mock_test_config = TestConfiguration(id=1, name="Task Test Config", target_node="task_node", owner_id=mock_user.id, connection_profile=mock_conn_profile)
    mock_test_run = TestRun(
        id=test_run_id,
        test_configuration_id=mock_test_config.id,
        status="queued",
        test_configuration=mock_test_config # Simulate relationship loading
    )

    # Configure mock_db_session_for_task.query().filter().first() to return mock_test_run
    mock_db_session_for_task.query.return_value.filter.return_value.first.return_value = mock_test_run

    # Configure the mocked service's main method
    # Let's say run_selected_tests doesn't raise an exception for success path
    mock_proxmox_service_instance.run_selected_tests = AsyncMock(return_value=None)

    # Simulate that run_selected_tests caused some TestCaseResults to be added (or not, for a clean pass)
    # For a clean pass, assume no failing TestCaseResults are found by the query
    mock_db_session_for_task.query.return_value.filter.return_value.count.return_value = 0 # No failed cases

    # --- Execute the task directly ---
    # Celery's task.apply() or task.run() can be used for more integrated testing,
    # but calling the function directly is simpler for unit testing its internal logic.
    # We need to mock the task's `update_state` method if `bind=True` is used.
    with patch.object(run_mcp_tests_task, 'update_state', MagicMock()) as mock_update_state:
        result = run_mcp_tests_task(test_run_id)

    # --- Assertions ---
    assert result["status"] == "success"
    assert result["run_id"] == test_run_id
    assert result["overall_status"] == "pass" # Because no failed cases were found

    # Check DB interactions
    mock_session_local_for_task.assert_called_once() # SessionLocal() was called
    mock_db_session_for_task.query.return_value.filter.return_value.first.assert_called_once()

    # Check ProxmoxService instantiation and call
    mock_proxmox_service_class.assert_called_once_with(connection_profile=mock_conn_profile, db=mock_db_session_for_task)
    mock_proxmox_service_instance.run_selected_tests.assert_called_once_with(test_config=mock_test_config, test_run_id=test_run_id)

    # Check TestRun status updates (simplified check on the mock object)
    assert mock_test_run.status == "completed"
    assert mock_test_run.overall_status == "pass"
    assert mock_test_run.start_time is not None
    assert mock_test_run.end_time is not None
    assert mock_test_run.duration_seconds is not None
    assert mock_test_run.celery_task_id == run_mcp_tests_task.request.id # Check if task ID was set

    # Check that update_state was called appropriately
    # Example: mock_update_state.assert_any_call(state='PROGRESS', meta={'status': 'Fetching test run details'})
    #          mock_update_state.assert_called_with(state='SUCCESS', meta={'status': 'Completed', 'overall_status': 'pass'})
    assert mock_update_state.call_count > 0 # At least some state updates happened

    mock_db_session_for_task.commit.assert_called() # Check commits happened
    mock_db_session_for_task.close.assert_called_once() # Session closed


def test_run_mcp_tests_task_service_failure(
    mock_session_local_for_task: MagicMock,
    mock_db_session_for_task: MagicMock,
    mock_proxmox_service_for_task: tuple
):
    mock_proxmox_service_class, mock_proxmox_service_instance = mock_proxmox_service_for_task
    test_run_id = 2

    mock_test_run = TestRun(id=test_run_id, status="queued", test_configuration=TestConfiguration(connection_profile=ConnectionProfile()))
    mock_db_session_for_task.query.return_value.filter.return_value.first.return_value = mock_test_run

    # Simulate failure from ProxmoxNonInteractiveService.run_selected_tests
    service_exception_message = "Proxmox API connection error during test"
    mock_proxmox_service_instance.run_selected_tests = AsyncMock(side_effect=Exception(service_exception_message))

    with patch.object(run_mcp_tests_task, 'update_state', MagicMock()) as mock_update_state:
        result = run_mcp_tests_task(test_run_id)

    assert result["status"] == "error"
    assert result["message"] == service_exception_message
    assert mock_test_run.status == "failed"
    assert mock_test_run.overall_status == "error"

    # Check that an error TestCaseResult was added
    # mock_db_session_for_task.add.assert_called()
    # added_object = mock_db_session_for_task.add.call_args_list[-1][0][0] # Get the last added object
    # assert isinstance(added_object, TestCaseResult)
    # assert added_object.status == "error"
    # assert service_exception_message in added_object.message

    mock_db_session_for_task.commit.assert_called()
    mock_db_session_for_task.close.assert_called_once()


def test_run_mcp_tests_task_run_not_found(
    mock_session_local_for_task: MagicMock,
    mock_db_session_for_task: MagicMock,
    mock_proxmox_service_for_task: tuple # Not strictly needed here but good for consistency
):
    test_run_id = 3
    # Simulate TestRun not found
    mock_db_session_for_task.query.return_value.filter.return_value.first.return_value = None

    with patch.object(run_mcp_tests_task, 'update_state', MagicMock()) as mock_update_state:
        result = run_mcp_tests_task(test_run_id)

    assert result["status"] == "error"
    assert "TestRun not found" in result["message"]

    # Ensure service was not called if run not found
    mock_proxmox_service_class, mock_proxmox_service_instance = mock_proxmox_service_for_task
    mock_proxmox_service_instance.run_selected_tests.assert_not_called()

    mock_db_session_for_task.close.assert_called_once() # Session should still be closed


def test_run_mcp_tests_task_handles_failed_test_cases(
    mock_session_local_for_task: MagicMock,
    mock_db_session_for_task: MagicMock,
    mock_proxmox_service_for_task: tuple
):
    mock_proxmox_service_class, mock_proxmox_service_instance = mock_proxmox_service_for_task
    test_run_id = 4

    mock_test_run = TestRun(id=test_run_id, status="queued", test_configuration=TestConfiguration(connection_profile=ConnectionProfile()))
    mock_db_session_for_task.query.return_value.filter.return_value.first.return_value = mock_test_run
    mock_proxmox_service_instance.run_selected_tests = AsyncMock(return_value=None) # Service itself runs fine

    # Simulate that run_selected_tests resulted in one failed TestCaseResult being stored
    # This is checked by querying the DB for TestCaseResult with status 'fail' or 'error'
    # The first call to count is for failed_cases_count
    mock_db_session_for_task.query.return_value.filter.return_value.count.side_effect = [1, 0, 1] # 1 fail, 0 skipped, 1 total

    with patch.object(run_mcp_tests_task, 'update_state', MagicMock()) as mock_update_state:
        result = run_mcp_tests_task(test_run_id)

    assert result["status"] == "success" # Task itself succeeded
    assert result["overall_status"] == "fail" # But the test run failed due to test cases
    assert mock_test_run.status == "completed"
    assert mock_test_run.overall_status == "fail"

    # Ensure the count query for failed tests was made
    # This is a bit complex to assert precisely without more intricate mock setup for query chains.
    # A simple check is that count was called.
    assert mock_db_session_for_task.query.return_value.filter.return_value.count.call_count > 0

    mock_db_session_for_task.commit.assert_called()
    mock_db_session_for_task.close.assert_called_once()
