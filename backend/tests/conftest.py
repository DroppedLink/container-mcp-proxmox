import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Renamed to avoid conflict
from sqlalchemy.pool import StaticPool # For SQLite in-memory

from app.main import app # Main FastAPI application
from app.database import Base, get_db # Base for creating tables, get_db for overriding
from app.models import User, ConnectionProfile, TestConfiguration, TestRun, TestCaseResult # Import all models
from app.core.config import settings # To potentially override settings for tests

# --- Settings for Testing ---
# Use an in-memory SQLite database for tests for speed and isolation
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:"
# SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///./test.db" # Or use a file-based SQLite

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST,
    connect_args={"check_same_thread": False}, # Needed for SQLite
    poolclass=StaticPool, # Use StaticPool for SQLite in-memory to ensure same connection is used
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# --- Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """
    Create all database tables once per test session using the test engine.
    `autouse=True` ensures this fixture is run automatically.
    """
    Base.metadata.create_all(bind=engine_test)
    yield
    # Optional: Drop all tables after test session if using a file-based test DB
    # Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def db_session() -> SQLAlchemySession:
    """
    Provides a clean database session for each test function.
    Rolls back any changes after the test to ensure isolation.
    """
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def override_get_db(db_session: SQLAlchemySession):
    """
    Overrides the `get_db` dependency in the FastAPI app to use the test database session.
    This ensures API endpoints interact with the test database.
    """
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass # Session is managed by db_session fixture

    app.dependency_overrides[get_db] = _override_get_db
    yield
    del app.dependency_overrides[get_db] # Clean up override


@pytest.fixture(scope="function")
def client(override_get_db) -> TestClient:
    """
    Provides a FastAPI TestClient instance that uses the overridden test database.
    Depends on `override_get_db` to ensure DB override is active.
    """
    # It's important that override_get_db is called before TestClient is initialized
    # if TestClient initialization triggers any DB interaction (though usually it doesn't).
    with TestClient(app) as c:
        yield c

# --- Data Fixtures (Examples) ---

@pytest.fixture(scope="function")
def test_user(db_session: SQLAlchemySession) -> User:
    # In a real app, use a password hashing utility
    # from app.core.security import get_password_hash
    # hashed_password = get_password_hash("testpassword")
    hashed_password_placeholder = "hashed_testpassword"

    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=hashed_password_placeholder,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_connection_profile(db_session: SQLAlchemySession, test_user: User) -> ConnectionProfile:
    # In a real app, password_encrypted would be properly encrypted
    # from app.core.security import encrypt_data
    # encrypted_pass = encrypt_data("proxmox_password", settings.PROXMOX_SECRET_KEY)
    encrypted_pass_placeholder = "encrypted_proxmox_password"

    profile = ConnectionProfile(
        name="Test Proxmox Server",
        host="pve.example.com",
        port=8006,
        username="proxmox_user",
        password_encrypted=encrypted_pass_placeholder,
        realm="pve",
        owner_id=test_user.id
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile

@pytest.fixture(scope="function")
def test_configuration(db_session: SQLAlchemySession, test_user: User, test_connection_profile: ConnectionProfile) -> TestConfiguration:
    config = TestConfiguration(
        name="Default VM Test Config",
        description="A standard configuration for testing VM creation.",
        target_node="pve1_mock", # Matches mock service
        connection_profile_id=test_connection_profile.id,
        owner_id=test_user.id,
        vm_id_range_start=9000,
        vm_id_range_end=9005,
        vm_os_image="local:iso/ubuntu-focal.iso",
        vm_ram_mb=2048,
        vm_cpu_cores=2,
        vm_disk_gb=20,
        vm_storage_pool="local-lvm",
        vm_network_bridge="vmbr0",
        selected_tests={
            "Resource Discovery": {"List Resources": True},
            "VM Management": {"Create VM": True, "Get VM Status": True},
            # "Snapshot Management": {"Create Snapshot": True, "List Snapshots": True} # Add more as needed
        },
        enable_destructive_tests=True, # Default to True for many tests
        cleanup_resources=True,
        schedule_type="manual"
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config

@pytest.fixture(scope="function")
def sample_test_run(db_session: SQLAlchemySession, test_user: User, test_configuration: TestConfiguration) -> TestRun:
    run = TestRun(
        test_configuration_id=test_configuration.id,
        triggered_by_user_id=test_user.id,
        status="completed", # Example status
        overall_status="pass", # Example status
        start_time=datetime.now(timezone.utc) - timedelta(minutes=10),
        end_time=datetime.now(timezone.utc) - timedelta(minutes=5),
        duration_seconds=300,
        celery_task_id="fake-celery-id-123"
    )
    db_session.add(run)
    db_session.commit()

    # Add some sample test case results
    tc1 = TestCaseResult(test_run_id=run.id, category="VM Management", test_name="Create VM", status="pass", duration_seconds=60.0, message="VM created")
    tc2 = TestCaseResult(test_run_id=run.id, category="VM Management", test_name="Get VM Status", status="pass", duration_seconds=5.0, message="VM is running")
    db_session.add_all([tc1, tc2])
    db_session.commit()
    db_session.refresh(run)
    return run

# Fixture to mock Celery task submission (optional, if you don't want tasks to actually run)
# @pytest.fixture(autouse=True)
# def mock_celery_task_apply_async(mocker):
#     class MockAsyncResult:
#         def __init__(self, task_id):
#             self.id = task_id
#     # Mock the .apply_async method of your specific task
#     # Replace 'app.tasks.run_mcp_tests_task' with the actual path to your task object
#     return mocker.patch('app.tasks.run_mcp_tests_task.apply_async',
#                         return_value=MockAsyncResult("mocked_celery_task_id_123"))


# For datetime imports in fixtures
from datetime import datetime, timezone, timedelta
if False: datetime.now(); timezone.utc; timedelta() # Make linters happy
