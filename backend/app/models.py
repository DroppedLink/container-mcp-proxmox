from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    connection_profiles = relationship("ConnectionProfile", back_populates="owner")
    test_configurations = relationship("TestConfiguration", back_populates="owner")
    test_runs = relationship("TestRun", back_populates="triggered_by_user")


class ConnectionProfile(Base):
    __tablename__ = "connection_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    host = Column(String, nullable=False)
    port = Column(Integer, default=8006)
    username = Column(String, nullable=False)
    password_encrypted = Column(String, nullable=False) # Store encrypted password/token
    realm = Column(String, nullable=False, default="pam")
    verify_ssl = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="connection_profiles")
    test_configurations = relationship("TestConfiguration", back_populates="connection_profile")


class TestConfiguration(Base):
    __tablename__ = "test_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)

    connection_profile_id = Column(Integer, ForeignKey("connection_profiles.id"))
    target_node = Column(String, nullable=False)

    # VM Creation Defaults
    vm_id_range_start = Column(Integer, default=9000)
    vm_id_range_end = Column(Integer, default=9010)
    vm_os_image = Column(String, nullable=True) # e.g., 'local:iso/ubuntu-22.04-server-cloudimg-amd64.iso'
    vm_ram_mb = Column(Integer, default=1024)
    vm_cpu_cores = Column(Integer, default=1)
    vm_disk_gb = Column(Integer, default=10)
    vm_storage_pool = Column(String, nullable=True) # e.g., 'local-lvm'
    vm_network_bridge = Column(String, nullable=True) # e.g., 'vmbr0'
    vm_vlan_tag = Column(Integer, nullable=True)

    # LXC Creation Defaults
    lxc_id_range_start = Column(Integer, default=8000)
    lxc_id_range_end = Column(Integer, default=8010)
    lxc_template_name = Column(String, nullable=True) # e.g., 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.gz'
    lxc_storage_pool = Column(String, nullable=True)
    lxc_ram_mb = Column(Integer, default=512)
    lxc_cpu_cores = Column(Integer, default=1)
    lxc_disk_gb = Column(Integer, default=5)
    lxc_network_bridge = Column(String, nullable=True)
    lxc_unprivileged = Column(Boolean, default=True)

    # Test Selection (can be stored as JSON or a separate related table if very complex)
    selected_tests = Column(JSON, nullable=True) # e.g., {"vm_lifecycle": true, "storage_tests": ["test_list_storage"]}

    enable_destructive_tests = Column(Boolean, default=False)
    cleanup_resources = Column(Boolean, default=True)

    # Scheduling
    schedule_type = Column(String, nullable=True) # e.g., 'manual', 'daily', 'weekly'
    schedule_time = Column(String, nullable=True) # e.g., '03:00'
    schedule_day_of_week = Column(Integer, nullable=True) # 0-6 for Monday-Sunday

    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="test_configurations")
    connection_profile = relationship("ConnectionProfile", back_populates="test_configurations")
    test_runs = relationship("TestRun", back_populates="test_configuration")


class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, index=True)
    test_configuration_id = Column(Integer, ForeignKey("test_configurations.id"))
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Null if scheduled

    status = Column(String, default="pending") # pending, running, completed, failed, cancelled
    overall_status = Column(String, nullable=True) # pass, fail, warning

    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    celery_task_id = Column(String, nullable=True, index=True) # To track the background task

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    test_configuration = relationship("TestConfiguration", back_populates="test_runs")
    triggered_by_user = relationship("User", back_populates="test_runs")
    detailed_results = relationship("TestCaseResult", back_populates="test_run", cascade="all, delete-orphan")


class TestCaseResult(Base):
    __tablename__ = "test_case_results"

    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)

    test_name = Column(String, nullable=False) # e.g., "VM Lifecycle: Create VM" or "test_list_resources"
    category = Column(String, nullable=True) # e.g., "VM Lifecycle"
    status = Column(String, nullable=False) # pass, fail, skipped, error
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True) # Error message or success details
    logs = Column(Text, nullable=True) # Detailed logs for this specific test case

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    test_run = relationship("TestRun", back_populates="detailed_results")

# To initialize the database (e.g., in a script or using Alembic)
# from .database import engine
# Base.metadata.create_all(bind=engine)
