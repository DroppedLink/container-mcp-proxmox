from fastapi import FastAPI
from app.api import api_router  # Import the main API router
from app.database import engine, Base # For initial table creation (optional here)

# # Create database tables on startup if they don't exist (for development)
# # In production, you'd typically use Alembic migrations.
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Proxmox MCP Testing Service",
    description="Backend service for managing and running Proxmox MCP tests.",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json", # Standardize OpenAPI doc URL
    docs_url="/api/v1/docs", # Standardize Swagger UI URL
    redoc_url="/api/v1/redoc" # Standardize ReDoc URL
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Proxmox MCP Testing Service API. See /api/v1/docs for details."}

# Include the API router with a prefix
app.include_router(api_router, prefix="/api/v1")

# Further application setup, middleware, exception handlers etc. can be added here
# For example, CORS middleware:
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:8080"], # Adjust to your frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
