from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional
from datetime import datetime, timezone

from app import schemas, models
from app.database import get_db
from app.tasks import run_mcp_tests_task
# from app.core.security import get_current_active_user # TODO: Implement and use

router = APIRouter()

@router.post("/", response_model=schemas.TestRunDetail, status_code=status.HTTP_202_ACCEPTED) # Return TestRunDetail
async def trigger_test_run(
    test_run_in: schemas.TestRunCreateRequest, # Use specific request schema
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    user_id_placeholder = 1
    config = db.query(models.TestConfiguration).filter(
        models.TestConfiguration.id == test_run_in.test_configuration_id,
        models.TestConfiguration.owner_id == user_id_placeholder
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test configuration not found or access denied"
        )

    db_test_run = models.TestRun(
        test_configuration_id=config.id,
        triggered_by_user_id=user_id_placeholder,
        status="queued",
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_test_run)
    db.commit()
    # Must commit here so that db_test_run gets an ID for the Celery task.

    task_submission = run_mcp_tests_task.apply_async(args=[db_test_run.id], countdown=1)

    db_test_run.celery_task_id = task_submission.id
    db.commit()
    db.refresh(db_test_run) # Refresh to get all fields populated for the response

    # Eagerly load for the response, so frontend gets immediate full detail of the queued run
    db_test_run_detailed = db.query(models.TestRun).options(
        joinedload(models.TestRun.test_configuration).joinedload(models.TestConfiguration.connection_profile),
        joinedload(models.TestRun.triggered_by_user),
        selectinload(models.TestRun.detailed_results) # Use selectinload for lists
    ).filter(models.TestRun.id == db_test_run.id).first()

    return schemas.TestRunDetail.from_orm_with_counts(db_test_run_detailed)


@router.get("/", response_model=List[schemas.TestRunSummary])
async def read_test_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    overall_status: Optional[str] = None,
    test_configuration_id: Optional[int] = None,
    test_configuration_name: Optional[str] = None, # Search within TestConfiguration.name
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    user_id_placeholder = 1 # current_user.id

    query = (
        db.query(
            models.TestRun,
            models.TestConfiguration.name.label("test_configuration_name_label"),
            models.User.username.label("triggered_by_username_label"),
            # Subquery for counts - can be intensive. Consider denormalization if performance is an issue.
            # For simplicity now, we might calculate this in Python or omit from summary for very large datasets.
            # Or, add these counts to TestRun model and update them in the Celery task.
        )
        .join(models.TestConfiguration, models.TestRun.test_configuration_id == models.TestConfiguration.id)
        .join(models.User, models.TestRun.triggered_by_user_id == models.User.id)
        .filter(models.TestRun.triggered_by_user_id == user_id_placeholder) # Security filter
    )

    if date_from:
        query = query.filter(models.TestRun.created_at >= date_from)
    if date_to:
        query = query.filter(models.TestRun.created_at <= date_to)
    if overall_status:
        query = query.filter(models.TestRun.overall_status == overall_status)
    if test_configuration_id:
        query = query.filter(models.TestRun.test_configuration_id == test_configuration_id)
    if test_configuration_name:
        query = query.filter(models.TestConfiguration.name.ilike(f"%{test_configuration_name}%"))

    test_runs_data = query.order_by(models.TestRun.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for run, config_name, username in test_runs_data:
        # Simple counts for summary - could be done with subqueries or by denormalization for performance
        total_tests = db.query(models.TestCaseResult).filter(models.TestCaseResult.test_run_id == run.id).count()
        passed_tests = db.query(models.TestCaseResult).filter(models.TestCaseResult.test_run_id == run.id, models.TestCaseResult.status == 'pass').count()
        failed_tests = db.query(models.TestCaseResult).filter(models.TestCaseResult.test_run_id == run.id, models.TestCaseResult.status.in_(['fail', 'error'])).count()

        results.append(schemas.TestRunSummary(
            id=run.id,
            status=run.status,
            overall_status=run.overall_status,
            start_time=run.start_time,
            end_time=run.end_time,
            duration_seconds=run.duration_seconds,
            celery_task_id=run.celery_task_id,
            test_configuration_id=run.test_configuration_id,
            triggered_by_user_id=run.triggered_by_user_id,
            created_at=run.created_at,
            test_configuration_name=config_name,
            triggered_by_username=username,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
        ))
    return results


@router.get("/{run_id}", response_model=schemas.TestRunDetail)
async def read_test_run_details(
    run_id: int,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    user_id_placeholder = 1 # current_user.id

    # Use options for eager loading related objects
    # joinedload for one-to-one or many-to-one relationships
    # selectinload for one-to-many relationships (like detailed_results)
    test_run = db.query(models.TestRun).options(
        joinedload(models.TestRun.test_configuration).joinedload(models.TestConfiguration.connection_profile),
        joinedload(models.TestRun.triggered_by_user),
        selectinload(models.TestRun.detailed_results)
    ).filter(
        models.TestRun.id == run_id,
        models.TestRun.triggered_by_user_id == user_id_placeholder # Security filter
    ).first()

    if not test_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found or access denied")

    return schemas.TestRunDetail.from_orm_with_counts(test_run)


@router.get("/{run_id}/status", response_model=schemas.TestRunBase) # Returns basic status
async def get_test_run_status(
    run_id: int,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    user_id_placeholder = 1 # current_user.id

    # Query only specific columns for efficiency if TestRunBase is much smaller than TestRun model
    test_run_fields = db.query(
        models.TestRun.status,
        models.TestRun.overall_status,
        models.TestRun.celery_task_id,
        models.TestRun.start_time,
        models.TestRun.end_time,
        models.TestRun.duration_seconds
    ).filter(
        models.TestRun.id == run_id,
        models.TestRun.triggered_by_user_id == user_id_placeholder
    ).first()

    if not test_run_fields:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found or access denied")

    # Manually construct the response model if query returns a tuple
    return schemas.TestRunBase(
        status=test_run_fields[0],
        overall_status=test_run_fields[1],
        celery_task_id=test_run_fields[2],
        start_time=test_run_fields[3],
        end_time=test_run_fields[4],
        duration_seconds=test_run_fields[5]
    )

@router.post("/{run_id}/cancel", response_model=schemas.Msg)
async def cancel_test_run(
    run_id: int,
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_active_user) # TODO
):
    user_id_placeholder = 1
    test_run = db.query(models.TestRun).filter(
        models.TestRun.id == run_id,
        models.TestRun.triggered_by_user_id == user_id_placeholder
    ).first()

    if not test_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found or access denied")

    if test_run.status not in ["pending", "queued", "running"]: # Check current status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel test run in '{test_run.status}' state."
        )

    if test_run.celery_task_id:
        from app.celery_app import celery_app as current_celery_app
        current_celery_app.control.revoke(test_run.celery_task_id, terminate=True, signal='SIGTERM')

    test_run.status = "cancelled"
    test_run.overall_status = "cancelled"
    if not test_run.end_time: # Set end time if not already set
        test_run.end_time = datetime.now(timezone.utc)
    if test_run.start_time and test_run.end_time:
        test_run.duration_seconds = int((test_run.end_time - test_run.start_time).total_seconds())

    db.commit()
    return schemas.Msg(message="Test run cancellation request processed. Actual termination depends on task state and responsiveness.")
