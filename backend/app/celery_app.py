from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.database import SessionLocal # To query schedules from DB

# Initialize Celery
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # task_track_started=True, # Good for more detailed state reporting
    # broker_connection_retry_on_startup=True,
)

def load_schedules():
    """
    Loads test schedules from the database and formats them for Celery Beat.
    This is a simple approach; for fully dynamic scheduling without restarting Beat,
    a custom database scheduler or a more complex mechanism would be needed.
    """
    db = SessionLocal()
    try:
        from app.models import TestConfiguration # Local import to avoid circular dependency issues at module load
        active_configs_with_schedules = db.query(TestConfiguration).filter(
            TestConfiguration.schedule_type != None,
            TestConfiguration.schedule_type != "manual" # 'manual' means not scheduled by Beat
        ).all()

        beat_schedule = {}
        for config in active_configs_with_schedules:
            schedule_name = f'scheduled_run_config_{config.id}'
            task_path = 'app.tasks.run_mcp_tests_task' # Make sure this matches the task name in @celery_app.task

            cron_args = {}
            valid_schedule = False

            if config.schedule_type == 'daily' and config.schedule_time:
                try:
                    hour, minute = map(int, config.schedule_time.split(':'))
                    cron_args = {'hour': hour, 'minute': minute, 'day_of_week': '*'}
                    valid_schedule = True
                except ValueError:
                    print(f"Warning: Invalid daily schedule_time format '{config.schedule_time}' for config ID {config.id}. Expected HH:MM.")

            elif config.schedule_type == 'weekly' and config.schedule_day_of_week is not None and config.schedule_time:
                try:
                    hour, minute = map(int, config.schedule_time.split(':'))
                    # Ensure schedule_day_of_week is in Celery's crontab format (0-6 for Sun-Sat, or 1-7 for Mon-Sun depending on Celery/OS)
                    # Celery crontab uses 0-6 for Sunday-Saturday.
                    cron_args = {'hour': hour, 'minute': minute, 'day_of_week': str(config.schedule_day_of_week)}
                    valid_schedule = True
                except ValueError:
                    print(f"Warning: Invalid weekly schedule_time format '{config.schedule_time}' for config ID {config.id}. Expected HH:MM.")

            # Add more types like 'monthly' if needed

            if valid_schedule:
                beat_schedule[schedule_name] = {
                    'task': task_path,
                    'schedule': crontab(**cron_args),
                    'args': (config.id,), # Pass test_configuration_id to the task
                    # 'options': {'queue': 'scheduled_tests'} # Optional: route to a specific queue
                }
            elif config.schedule_type not in ['manual', None]: # Log if schedule type was meant to be active
                print(f"Warning: Config ID {config.id} has schedule_type '{config.schedule_type}' but invalid parameters. It will not be scheduled by Beat.")

        print(f"Loaded Celery Beat schedules: {beat_schedule}")
        return beat_schedule
    except Exception as e:
        # Log this error properly in a real application
        print(f"Error loading schedules from database: {e}")
        return {} # Return empty schedule on error
    finally:
        db.close()

# Load schedules when Celery app is configured.
# This means Beat will load these schedules upon its startup.
# Changes to schedules in DB would require Beat to be restarted with this setup.
celery_app.conf.beat_schedule = load_schedules()

# Example static schedule for testing Beat itself (can be removed later)
# celery_app.conf.beat_schedule['sample-task-every-minute'] = {
#     'task': 'app.tasks.sample_celery_task',
#     'schedule': crontab(minute='*/1'), # Every minute
#     'args': ("Hello from Celery Beat static schedule!",)
# }


if __name__ == '__main__':
    # This allows running celery worker with `python -m app.celery_app worker -l info -B` (to include Beat)
    # However, it's more common to run worker and beat as separate processes:
    # `celery -A app.celery_app worker -l info`
    # `celery -A app.celery_app beat -l info --scheduler celery.beat.PersistentScheduler` (or default)
    celery_app.start()
