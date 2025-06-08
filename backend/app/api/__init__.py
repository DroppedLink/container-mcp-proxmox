from fastapi import APIRouter
from .endpoints import auth, connection_profiles, test_configurations, test_runs

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(connection_profiles.router, prefix="/connection-profiles", tags=["Connection Profiles"])
api_router.include_router(test_configurations.router, prefix="/test-configurations", tags=["Test Configurations"])
api_router.include_router(test_runs.router, prefix="/test-runs", tags=["Test Runs"])
