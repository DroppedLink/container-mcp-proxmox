import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session # For type hinting
from datetime import datetime, timezone, timedelta

from app import schemas
from app.models import TestRun, TestConfiguration, User, ConnectionProfile, TestCaseResult # Import models

# --- Test Triggering a Test Run ---
def test_trigger_test_run_success(
    client: TestClient, db_session: Session, test_configuration: TestConfiguration, test_user: User, mocker
):
    # Mock Celery task submission to prevent actual execution during API test
    mock_apply_async = mocker.patch('app.tasks.run_mcp_tests_task.apply_async')
    mock_apply_async.return_value.id = "mocked-celery-task-id-trigger"

    payload = {"test_configuration_id": test_configuration.id}
    response = client.post("/api/v1/test-runs/", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["test_configuration_id"] == test_configuration.id
    assert data["status"] == "queued"
    assert data["celery_task_id"] == "mocked-celery-task-id-trigger"
    assert data["triggered_by_user"]["id"] == test_user.id
    assert data["test_configuration"]["id"] == test_configuration.id

    mock_apply_async.assert_called_once()
    # Check if the task was called with the correct TestRun ID argument
    # This requires inspecting the args passed to apply_async
    # For now, just checking it was called is a good start.
    # args_called, _ = mock_apply_async.call_args
    # created_run_in_db = db_session.query(TestRun).filter(TestRun.celery_task_id == "mocked-celery-task-id-trigger").first()
    # assert args_called[0] == [created_run_in_db.id]


def test_trigger_test_run_config_not_found(client: TestClient):
    payload = {"test_configuration_id": 99999} # Non-existent ID
    response = client.post("/api/v1/test-runs/", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Test configuration not found" in response.json()["detail"]

# --- Test Listing Test Runs ---
def test_read_test_runs_empty(client: TestClient, db_session: Session): # db_session to ensure tables are created
    response = client.get("/api/v1/test-runs/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_read_test_runs_with_data(
    client: TestClient, db_session: Session, sample_test_run: TestRun, test_configuration: TestConfiguration, test_user: User
):
    # sample_test_run fixture creates one run. Let's add another for pagination/filtering tests.
    # Create a second TestConfiguration for variety
    other_conn_profile = ConnectionProfile(name="Other Conn", host="other.host", username="other", password_encrypted="enc", realm="pve", owner_id=test_user.id)
    db_session.add(other_conn_profile)
    db_session.commit()

    other_config = TestConfiguration(
        name="Nightly LXC Checks", target_node="pve2_mock", owner_id=test_user.id,
        connection_profile_id=other_conn_profile.id, schedule_type="daily", schedule_time="02:00",
        created_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add(other_config)
    db_session.commit()

    run2_start_time = datetime.now(timezone.utc) - timedelta(hours=5)
    run2 = TestRun(
        test_configuration_id=other_config.id, triggered_by_user_id=test_user.id,
        status="running", overall_status="None", celery_task_id="celery-run2",
        created_at=run2_start_time, start_time=run2_start_time
    )
    db_session.add(run2)
    db_session.commit()

    response = client.get("/api/v1/test-runs/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    # Check if sorted by created_at desc (sample_test_run is newer if created after run2 in this test setup logic)
    # Actually, sample_test_run is older based on its fixture's created_at
    # Let's ensure the order is correct based on `created_at` (descending)
    assert data[0]["id"] == sample_test_run.id # sample_test_run is newer if its fixture is called after run2 is created
    assert data[1]["id"] == run2.id
    assert data[0]["test_configuration_name"] == test_configuration.name
    assert data[1]["test_configuration_name"] == other_config.name

    # Test pagination (limit)
    response_limit1 = client.get("/api/v1/test-runs/?limit=1")
    assert response_limit1.status_code == status.HTTP_200_OK
    data_limit1 = response_limit1.json()
    assert len(data_limit1) == 1
    assert data_limit1[0]["id"] == sample_test_run.id

    # Test pagination (skip)
    response_skip1 = client.get("/api/v1/test-runs/?skip=1&limit=1")
    assert response_skip1.status_code == status.HTTP_200_OK
    data_skip1 = response_skip1.json()
    assert len(data_skip1) == 1
    assert data_skip1[0]["id"] == run2.id

    # Test filtering by status
    response_status_running = client.get("/api/v1/test-runs/?overall_status=None") # run2's overall_status
    assert response_status_running.status_code == status.HTTP_200_OK
    data_status_running = response_status_running.json()
    assert len(data_status_running) == 1
    assert data_status_running[0]["id"] == run2.id

    response_status_pass = client.get("/api/v1/test-runs/?overall_status=pass") # sample_test_run's overall_status
    assert response_status_pass.status_code == status.HTTP_200_OK
    data_status_pass = response_status_pass.json()
    assert len(data_status_pass) == 1
    assert data_status_pass[0]["id"] == sample_test_run.id

    # Test filtering by test_configuration_id
    response_config_id = client.get(f"/api/v1/test-runs/?test_configuration_id={other_config.id}")
    assert response_config_id.status_code == status.HTTP_200_OK
    data_config_id = response_config_id.json()
    assert len(data_config_id) == 1
    assert data_config_id[0]["test_configuration_id"] == other_config.id

    # Test filtering by test_configuration_name
    response_config_name = client.get(f"/api/v1/test-runs/?test_configuration_name=Nightly") # Partial match
    assert response_config_name.status_code == status.HTTP_200_OK
    data_config_name = response_config_name.json()
    assert len(data_config_name) == 1
    assert "Nightly LXC Checks" in data_config_name[0]["test_configuration_name"]

    # Test filtering by date range
    # sample_test_run created_at is now() - 10min (approx)
    # run2 created_at is now() - 5 hours
    date_from_str = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    response_date = client.get(f"/api/v1/test-runs/?date_from={date_from_str}")
    assert response_date.status_code == status.HTTP_200_OK
    data_date = response_date.json()
    assert len(data_date) == 1 # Only sample_test_run should match
    assert data_date[0]["id"] == sample_test_run.id


# --- Test Reading Detailed Test Run ---
def test_read_test_run_details_success(client: TestClient, db_session: Session, sample_test_run: TestRun):
    response = client.get(f"/api/v1/test-runs/{sample_test_run.id}/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == sample_test_run.id
    assert data["status"] == sample_test_run.status
    assert data["overall_status"] == sample_test_run.overall_status
    assert data["test_configuration"]["id"] == sample_test_run.test_configuration_id
    assert data["triggered_by_user"]["id"] == sample_test_run.triggered_by_user_id

    assert "detailed_results" in data
    assert len(data["detailed_results"]) > 0 # sample_test_run fixture adds 2 test case results
    first_tc_result = data["detailed_results"][0]
    assert first_tc_result["category"] == "VM Management"
    assert first_tc_result["test_name"] == "Create VM"
    assert first_tc_result["status"] == "pass"

    # Check calculated counts from TestRunDetail.from_orm_with_counts
    assert data["total_tests"] == len(data["detailed_results"])
    assert data["passed_tests"] == sum(1 for tc in data["detailed_results"] if tc["status"] == "pass")
    assert data["failed_tests"] == sum(1 for tc in data["detailed_results"] if tc["status"] == "fail")


def test_read_test_run_details_not_found(client: TestClient):
    response = client.get("/api/v1/test-runs/99999/") # Non-existent ID
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Test run not found" in response.json()["detail"]

# --- Test Get Test Run Status ---
def test_get_test_run_status_success(client: TestClient, sample_test_run: TestRun):
    response = client.get(f"/api/v1/test-runs/{sample_test_run.id}/status/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == sample_test_run.status
    assert data["overall_status"] == sample_test_run.overall_status
    assert data["celery_task_id"] == sample_test_run.celery_task_id

def test_get_test_run_status_not_found(client: TestClient):
    response = client.get("/api/v1/test-runs/99999/status/")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- Test Cancel Test Run ---
@pytest.mark.parametrize("initial_status, expected_final_status_code, can_cancel", [
    ("queued", status.HTTP_200_OK, True),
    ("running", status.HTTP_200_OK, True),
    ("pending", status.HTTP_200_OK, True),
    ("completed", status.HTTP_400_BAD_REQUEST, False),
    ("failed", status.HTTP_400_BAD_REQUEST, False),
    ("cancelled", status.HTTP_400_BAD_REQUEST, False),
])
def test_cancel_test_run(
    client: TestClient, db_session: Session, test_configuration: TestConfiguration, test_user: User,
    initial_status: str, expected_final_status_code: int, can_cancel: bool, mocker
):
    run_to_cancel = TestRun(
        test_configuration_id=test_configuration.id,
        triggered_by_user_id=test_user.id,
        status=initial_status, # Set initial status
        celery_task_id="celery-task-to-cancel-123"
    )
    db_session.add(run_to_cancel)
    db_session.commit()

    mock_celery_control_revoke = mocker.patch('app.celery_app.celery_app.control.revoke')

    response = client.post(f"/api/v1/test-runs/{run_to_cancel.id}/cancel")
    assert response.status_code == expected_final_status_code

    db_session.refresh(run_to_cancel)
    if can_cancel:
        assert response.json()["message"].startswith("Test run cancellation request processed")
        assert run_to_cancel.status == "cancelled"
        mock_celery_control_revoke.assert_called_once_with("celery-task-to-cancel-123", terminate=True, signal='SIGTERM')
    else:
        assert f"Cannot cancel test run in '{initial_status}' state" in response.json()["detail"]
        assert run_to_cancel.status == initial_status # Status should not change
        mock_celery_control_revoke.assert_not_called()
