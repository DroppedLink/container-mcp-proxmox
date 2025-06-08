import asyncio
from app.celery_app import celery_app
from app.database import SessionLocal # To create a new session for the task
from app.models import TestRun, TestConfiguration, ConnectionProfile, TestCaseResult
from app.services.proxmox_service import ProxmoxNonInteractiveService
from app.core.config import settings # If needed for any task-specific settings
from datetime import datetime, timezone

# Helper function to create a new DB session for the task
def get_task_db_session():
    return SessionLocal()

@celery_app.task(bind=True, name="app.tasks.run_mcp_tests_task")
def run_mcp_tests_task(self, test_run_id: int):
    """
    Celery task to execute Proxmox MCP tests.
    `bind=True` makes `self` the first argument, giving access to task instance.
    """
    db = get_task_db_session()
    test_run = None
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Fetching test run details'})
        test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()

        if not test_run:
            self.update_state(state='FAILURE', meta={'status': 'TestRun not found'})
            print(f"Task Error: TestRun ID {test_run_id} not found.")
            return {"status": "error", "message": "TestRun not found"}

        if test_run.status == "cancelled": # Check if cancelled before starting
            self.update_state(state='REVOKED', meta={'status': 'TestRun was cancelled by user'})
            print(f"Task Info: TestRun ID {test_run_id} was cancelled. Skipping execution.")
            return {"status": "cancelled", "run_id": test_run_id}

        test_run.status = "running"
        test_run.celery_task_id = self.request.id # Store Celery task ID
        test_run.start_time = datetime.now(timezone.utc)
        db.commit()
        db.refresh(test_run) # Refresh to get the updated celery_task_id if needed elsewhere

        self.update_state(state='PROGRESS', meta={'status': 'Fetching configuration'})
        config = test_run.test_configuration
        if not config:
            raise ValueError("TestConfiguration not found for the TestRun.")

        conn_profile = config.connection_profile
        if not conn_profile:
            raise ValueError("ConnectionProfile not found for the TestConfiguration.")

        self.update_state(state='PROGRESS', meta={'status': 'Initializing Proxmox service'})
        proxmox_service = ProxmoxNonInteractiveService(connection_profile=conn_profile, db=db)

        self.update_state(state='PROGRESS', meta={'status': 'Executing tests'})
        # The run_selected_tests method in ProxmoxNonInteractiveService needs to be async
        # or run within an event loop if it contains async calls.
        # Celery tasks are typically synchronous. If proxmox_service methods are async,
        # they need to be run using asyncio.run()
        asyncio.run(proxmox_service.run_selected_tests(test_config=config, test_run_id=test_run.id))

        self.update_state(state='PROGRESS', meta={'status': 'Calculating final status'})
        # Determine overall status based on TestCaseResult entries
        failed_cases_count = db.query(TestCaseResult).filter(
            TestCaseResult.test_run_id == test_run_id,
            TestCaseResult.status.in_(['fail', 'error'])
        ).count()

        if failed_cases_count > 0:
            test_run.overall_status = "fail"
        else:
            skipped_cases_count = db.query(TestCaseResult).filter(
                TestCaseResult.test_run_id == test_run_id,
                TestCaseResult.status == 'skipped'
            ).count()
            total_cases = db.query(TestCaseResult).filter(TestCaseResult.test_run_id == test_run_id).count()
            if skipped_cases_count == total_cases and total_cases > 0 : # All skipped
                 test_run.overall_status = "skipped"
            elif db.query(TestCaseResult).filter(TestCaseResult.test_run_id == test_run_id, TestCaseResult.status == 'pass').count() > 0: # At least one pass
                test_run.overall_status = "pass" # Mark as pass if there are any passes and no failures
            else: # No passes, no failures, possibly no tests ran or all skipped without being total
                test_run.overall_status = "completed" # Or "unknown", "nodata"

        test_run.status = "completed"
        self.update_state(state='SUCCESS', meta={'status': 'Completed', 'overall_status': test_run.overall_status})
        final_status = {"status": "success", "run_id": test_run_id, "overall_status": test_run.overall_status}

    except Exception as e:
        print(f"Task Error for TestRun ID {test_run_id}: {e}")
        if test_run: # test_run might be None if initial query fails
            test_run.status = "failed"
            test_run.overall_status = "error" # Indicates a system error during test execution
            # Optionally store the error message in the TestRun or a specific log
            # test_run.error_message = str(e) # Requires adding 'error_message' field to TestRun model

            # Create a TestCaseResult to log this top-level error
            error_case = models.TestCaseResult(
                test_run_id=test_run.id,
                test_name="System Error",
                category="Task Execution",
                status="error",
                message=f"Task failed: {str(e)}",
                logs=f"Traceback: {e.__traceback__}" # Be cautious with traceback length
            )
            db.add(error_case)

        self.update_state(state='FAILURE', meta={'status': 'Task execution failed', 'error': str(e)})
        final_status = {"status": "error", "message": str(e), "run_id": test_run_id}
    finally:
        if test_run and test_run.start_time: # Ensure start_time was set
            test_run.end_time = datetime.now(timezone.utc)
            if test_run.end_time and test_run.start_time: # Redundant check, but safe
                 test_run.duration_seconds = int((test_run.end_time - test_run.start_time).total_seconds())
        if db:
            db.commit() # Commit final changes to test_run and any error TestCaseResult
            db.close()
    return final_status


@celery_app.task(name="app.tasks.sample_celery_task")
def sample_celery_task(message: str):
    """A sample Celery task for testing the setup."""
    print(f"Sample Celery Task Received: {message}")
    return f"Processed: {message}"

# Example of how to load schedules dynamically (e.g., on Celery Beat startup)
# This is more advanced and would typically be part of a custom Celery Beat scheduler
# or a startup script for Beat.
# def load_schedules_from_db():
#     db = get_task_db_session()
#     try:
#         active_configs_with_schedules = db.query(TestConfiguration).filter(
#             TestConfiguration.schedule_type != None,
#             TestConfiguration.schedule_type != "manual"
#         ).all()
#
#         schedule_config = {}
#         for config in active_configs_with_schedules:
#             if config.schedule_type == 'daily' and config.schedule_time:
#                 hour, minute = map(int, config.schedule_time.split(':'))
#                 schedule_config[f'scheduled_run_config_{config.id}'] = {
#                     'task': 'app.tasks.run_mcp_tests_task',
#                     'schedule': crontab(hour=hour, minute=minute),
#                     'args': (config.id,),
#                 }
#             # Add more schedule types (weekly, etc.) here
#         return schedule_config
#     finally:
#         db.close()

# if settings.ENVIRONMENT == "production": # Or some other flag
#    celery_app.conf.beat_schedule.update(load_schedules_from_db())
