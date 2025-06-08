from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True # Enables an object to be mapped from ORM model to Pydantic model

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase): # For internal use, includes hashed_password
    hashed_password: str


# --- Token Schemas (for Authentication) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# --- ConnectionProfile Schemas ---
class ConnectionProfileBase(BaseModel):
    name: str
    host: str
    port: Optional[int] = 8006
    username: str
    realm: Optional[str] = "pam"
    verify_ssl: Optional[bool] = True

class ConnectionProfileCreate(ConnectionProfileBase):
    password: str # Password/API Token, will be encrypted before saving

class ConnectionProfileUpdate(ConnectionProfileBase):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None # To update password (send unencrypted)
    realm: Optional[str] = None
    verify_ssl: Optional[bool] = None

class ConnectionProfile(ConnectionProfileBase): # Schema for responses
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # password_encrypted is NOT exposed in API responses

    class Config:
        orm_mode = True


# --- TestConfiguration Schemas ---
class TestConfigurationBase(BaseModel):
    name: str
    description: Optional[str] = None
    target_node: str

    vm_id_range_start: Optional[int] = 9000
    vm_id_range_end: Optional[int] = 9010
    vm_os_image: Optional[str] = None
    vm_ram_mb: Optional[int] = 1024
    vm_cpu_cores: Optional[int] = 1
    vm_disk_gb: Optional[int] = 10
    vm_storage_pool: Optional[str] = None
    vm_network_bridge: Optional[str] = None
    vm_vlan_tag: Optional[int] = None

    lxc_id_range_start: Optional[int] = 8000
    lxc_id_range_end: Optional[int] = 8010
    lxc_template_name: Optional[str] = None
    lxc_storage_pool: Optional[str] = None
    lxc_ram_mb: Optional[int] = 512
    lxc_cpu_cores: Optional[int] = 1
    lxc_disk_gb: Optional[int] = 5
    lxc_network_bridge: Optional[str] = None
    lxc_unprivileged: Optional[bool] = True

    selected_tests: Optional[Dict[str, Any]] = Field(default_factory=dict)
    enable_destructive_tests: Optional[bool] = False
    cleanup_resources: Optional[bool] = True

    schedule_type: Optional[str] = "manual"
    schedule_time: Optional[str] = None # 'HH:MM'
    schedule_day_of_week: Optional[int] = None # 0-6 (Sun-Sat for Celery crontab)

class TestConfigurationCreate(TestConfigurationBase):
    connection_profile_id: int

class TestConfigurationUpdate(TestConfigurationBase): # All fields optional for PATCH-like behavior
    name: Optional[str] = None
    target_node: Optional[str] = None
    connection_profile_id: Optional[int] = None
    # Make all other fields from TestConfigurationBase optional as well
    description: Optional[str] = None
    vm_id_range_start: Optional[int] = None
    vm_id_range_end: Optional[int] = None
    # ... (repeat for all fields in TestConfigurationBase) ...


class TestConfiguration(TestConfigurationBase): # Schema for responses (detailed view)
    id: int
    owner_id: int
    connection_profile_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    connection_profile: Optional[ConnectionProfile] = None # For nested response

    class Config:
        orm_mode = True

class TestConfigurationMinimal(BaseModel): # For embedding in TestRun list
    id: int
    name: str
    target_node: str

    class Config:
        orm_mode = True


# --- TestCaseResult Schemas ---
class TestCaseResultBase(BaseModel):
    test_name: str
    category: Optional[str] = None
    status: str
    duration_seconds: Optional[float] = None
    message: Optional[str] = None
    logs: Optional[str] = None

class TestCaseResultCreate(TestCaseResultBase): # Used by service to create results
    test_run_id: int

class TestCaseResult(TestCaseResultBase): # Schema for responses
    id: int
    test_run_id: int
    created_at: datetime

    class Config:
        orm_mode = True


# --- TestRun Schemas ---
class TestRunBase(BaseModel): # Common fields for TestRun
    status: Optional[str] = "pending"
    overall_status: Optional[str] = None # 'pass', 'fail', 'warning', 'error', 'skipped', 'cancelled', 'completed'
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    celery_task_id: Optional[str] = None

class TestRunCreateRequest(BaseModel): # For triggering a run via API
    test_configuration_id: int

class TestRunUpdateInternal(TestRunBase): # For worker to update status (internal use)
    pass


# Schema for the list of TestRuns (GET /test-runs/)
class TestRunSummary(TestRunBase):
    id: int
    test_configuration_id: int
    triggered_by_user_id: Optional[int] = None
    created_at: datetime

    test_configuration_name: Optional[str] = None # Populated by query/join
    triggered_by_username: Optional[str] = None # Populated by query/join

    # Aggregated results (calculated or from TestRun model if stored)
    total_tests: Optional[int] = None
    passed_tests: Optional[int] = None
    failed_tests: Optional[int] = None

    class Config:
        orm_mode = True


# Schema for detailed TestRun report (GET /test-runs/{test_run_id}/)
class TestRunDetail(TestRunBase):
    id: int
    test_configuration_id: int
    triggered_by_user_id: Optional[int] = None
    created_at: datetime

    test_configuration: Optional[TestConfiguration] = None # Full configuration
    triggered_by_user: Optional[User] = None # User who triggered it
    detailed_results: List[TestCaseResult] = Field(default_factory=list)

    # Aggregated results (can be calculated from detailed_results or stored in TestRun model)
    total_tests: Optional[int] = None
    passed_tests: Optional[int] = None
    failed_tests: Optional[int] = None
    skipped_tests: Optional[int] = None
    error_tests: Optional[int] = None


    @classmethod
    def from_orm_with_counts(cls, test_run_model: Any):
        """ Helper to populate counts from detailed_results if not stored on model. """
        instance = cls.from_orm(test_run_model)
        if instance.detailed_results:
            instance.total_tests = len(instance.detailed_results)
            instance.passed_tests = sum(1 for res in instance.detailed_results if res.status == 'pass')
            instance.failed_tests = sum(1 for res in instance.detailed_results if res.status == 'fail')
            instance.skipped_tests = sum(1 for res in instance.detailed_results if res.status == 'skipped')
            instance.error_tests = sum(1 for res in instance.detailed_results if res.status == 'error')
        return instance

    class Config:
        orm_mode = True


# --- General Schemas ---
class Msg(BaseModel):
    message: str
