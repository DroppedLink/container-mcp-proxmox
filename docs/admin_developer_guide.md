# Proxmox MCP Testing Service - Administrator & Developer Guide

## I. System Architecture

### Overview
The Proxmox MCP Testing Service is composed of several key components working together:
- **Frontend (Web Interface):** A Vue.js single-page application (SPA) that users interact with to manage configurations, trigger tests, and view reports.
- **Backend API:** A FastAPI (Python) application that serves the frontend, handles business logic, interacts with the database, and manages test execution via Celery.
- **Celery Workers:** Python processes that execute the long-running Proxmox test tasks asynchronously. These are managed by Celery.
- **Celery Beat:** A Celery scheduler process that triggers scheduled test runs based on user-defined configurations.
- **Database:** A PostgreSQL (recommended) or SQLite database used to store all persistent data, including user accounts (optional), connection profiles, test configurations, test run history, and detailed test case results. SQLAlchemy is used as the ORM.
- **Message Broker (Redis):** Used by Celery for communication between the API, workers, and Beat. Also used as the Celery result backend.
- **Proxmox VE Environment(s):** The target Proxmox server(s) or cluster(s) against which the tests are executed.

### Technology Stack
- **Frontend:** Vue.js (JavaScript framework), Tailwind CSS (styling).
- **Backend:** FastAPI (Python web framework), Pydantic (data validation).
- **ORM:** SQLAlchemy (with Alembic for database migrations).
- **Task Queue:** Celery.
- **Message Broker:** Redis.
- **Database:** PostgreSQL (recommended for production), SQLite (for development/testing).
- **Proxmox Interaction:** Primarily through direct Proxmox API calls (potentially using a library like `python-proxmoxer` or custom API wrappers within the `ProxmoxNonInteractiveService`).

### Data Flow Diagram (Simplified)

```
User <--> Frontend (Vue.js) <--> Backend API (FastAPI)
                                     |   ^
                                     |   | (DB Operations)
                                     v   |
                                  Database (PostgreSQL)
                                     ^   ^
                                     |   | (Task Status/Results)
                                     |   |
Backend API --(Enqueue Task)--> Message Broker (Redis) --(Dequeue Task)--> Celery Worker(s)
                                     ^                                         |
                                     |                                         | (API Calls)
                                     +----(Scheduled Tasks)---------------- Celery Beat
                                                                               v
                                                                     Proxmox VE Environment
```

## II. Installation and Setup

### Prerequisites
- **Python:** Version 3.8+ (check `Pipfile` or `requirements.txt` for exact version).
- **Node.js & npm/yarn:** For building the frontend (if not served pre-built). Version 16+.
- **Database Server:** PostgreSQL (version 12+) recommended for production. SQLite can be used for development.
- **Message Broker:** Redis (version 5+).
- **Proxmox VE:** Access to a Proxmox VE environment for testing.

### Backend Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>/backend
    ```

2.  **Set up Python Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    # For development, also install test dependencies:
    pip install -r requirements-dev.txt
    ```

4.  **Database Configuration:**
    *   Copy `.env.example` to `.env` (if provided) or create a new `.env` file in the `backend/` directory.
    *   Set the `DATABASE_URL` environment variable:
        ```env
        # Example for PostgreSQL:
        DATABASE_URL=postgresql://user:password@host:port/database_name
        # Example for SQLite (file-based, for development):
        # DATABASE_URL=sqlite:///./mcp_tester.db
        ```
    *   **Run Alembic Migrations:**
        *   Ensure Alembic is configured correctly in `alembic.ini` (it should point to your `DATABASE_URL`).
        *   The `script.py.mako` should reference `target_metadata` from `app.database.Base.metadata`.
        ```bash
        # If first time or no alembic/ directory exists:
        # alembic init alembic  (then configure env.py and script.py.mako)

        # Create a new migration (if models.py changed)
        alembic revision -m "create_initial_tables" # Or a descriptive name for changes

        # Apply migrations to the database
        alembic upgrade head
        ```

5.  **Celery Worker and Beat Setup:**
    *   Ensure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are correctly set in your `.env` file (pointing to your Redis instance).
        ```env
        CELERY_BROKER_URL=redis://localhost:6379/0
        CELERY_RESULT_BACKEND=redis://localhost:6379/0
        ```
    *   **To run a Celery worker:**
        ```bash
        # From the backend directory, with virtualenv activated
        celery -A app.celery_app worker -l info -P gevent # -P gevent recommended for async tasks
        ```
    *   **To run Celery Beat (scheduler):**
        ```bash
        # From the backend directory, with virtualenv activated
        celery -A app.celery_app beat -l info --scheduler celery.beat.PersistentScheduler
        # PersistentScheduler stores the schedule state in a local file (celerybeat-schedule).
        # For multi-node Beat, a custom DB-backed scheduler might be needed.
        ```
    *   **Production Setup (Systemd/Supervisor):**
        *   For production, you should run Celery workers and Beat as system services.
        *   **Example Systemd Service File for Celery Worker (`mcp_celery_worker.service`):**
            ```systemd
            [Unit]
            Description=MCP Testing Service Celery Worker
            After=network.target redis.service postgresql.service

            [Service]
            Type=simple
            User=<your_deploy_user>
            Group=<your_deploy_group>
            WorkingDirectory=/path/to/backend
            ExecStart=/path/to/backend/venv/bin/celery -A app.celery_app worker -l info -P gevent --concurrency=4
            Restart=always
            EnvironmentFile=/path/to/backend/.env # Load environment variables

            [Install]
            WantedBy=multi-user.target
            ```
        *   **Example Systemd Service File for Celery Beat (`mcp_celery_beat.service`):**
            ```systemd
            [Unit]
            Description=MCP Testing Service Celery Beat
            After=network.target redis.service postgresql.service

            [Service]
            Type=simple
            User=<your_deploy_user>
            Group=<your_deploy_group>
            WorkingDirectory=/path/to/backend
            ExecStart=/path/to/backend/venv/bin/celery -A app.celery_app beat -l info --scheduler celery.beat.PersistentScheduler
            Restart=always
            EnvironmentFile=/path/to/backend/.env # Load environment variables

            [Install]
            WantedBy=multi-user.target
            ```
        *   Place these files in `/etc/systemd/system/`, then run `sudo systemctl daemon-reload`, `sudo systemctl enable <service_name>`, `sudo systemctl start <service_name>`.
        *   Adjust paths, user, group, and concurrency as needed.

6.  **Web Server (Uvicorn) Setup:**
    *   For development:
        ```bash
        # From the backend directory
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   For production, you might run Uvicorn behind a reverse proxy like Nginx or Traefik. You can use Gunicorn to manage Uvicorn workers:
        ```bash
        # Example with Gunicorn
        gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
        ```
        *   This can also be managed by a systemd service.

### Frontend Setup
(This section is applicable if the frontend is a separate project that needs building. If FastAPI serves the static files, this might be simpler.)

1.  Navigate to the frontend project directory (if separate).
2.  Install dependencies:
    ```bash
    npm install # or yarn install
    ```
3.  Build the application for production:
    ```bash
    npm run build # or yarn build
    ```
4.  The output (usually in a `dist/` directory) needs to be served by a web server (like Nginx) or configured to be served by FastAPI as static files.
    *   If serving with FastAPI, copy the contents of `dist/` to a `static/` directory in the backend and configure FastAPI's `StaticFiles`. Ensure the `index.html` is served for SPA routing.

## III. Configuration

The backend service is primarily configured through environment variables, typically managed in a `.env` file in the `backend/` directory. Refer to `app/core/config.py` for all available settings.

Key environment variables:
-   `DATABASE_URL`: SQLAlchemy database connection string.
-   `CELERY_BROKER_URL`: URL for the Celery message broker (Redis).
-   `CELERY_RESULT_BACKEND`: URL for the Celery result backend (Redis).
-   `SECRET_KEY`: A secret key for signing JWT tokens (important for security). **Change this for production!**
-   `PROXMOX_SECRET_KEY`: A secret key used for encrypting/decrypting sensitive parts of Proxmox connection profiles. **Change this for production!**
-   `ACCESS_TOKEN_EXPIRE_MINUTES`: Lifetime of JWT access tokens.
-   `LOG_LEVEL`: (Not explicitly in config.py yet, but can be added for Uvicorn/FastAPI logging).

## IV. API Documentation

The FastAPI backend automatically generates OpenAPI (Swagger UI) documentation.
-   **Swagger UI:** Accessible at `/api/v1/docs` (relative to the backend URL, e.g., `http://localhost:8000/api/v1/docs`).
-   **ReDoc:** Accessible at `/api/v1/redoc`.
-   **OpenAPI JSON:** Available at `/api/v1/openapi.json`.

This interactive documentation provides details on all available API endpoints, request/response schemas, and allows for sending test requests.

## V. Extending the Service

### Adding New Test Cases
1.  **Locate the Service:** Open `backend/app/services/proxmox_service.py`.
2.  **Define a New Async Method:** Add a new `async def test_your_new_feature(self, test_config: models.TestConfiguration, ...any_other_params):` method to the `ProxmoxNonInteractiveService` class.
    *   Derive necessary parameters (node, VM IDs, specific settings) from `test_config`.
    *   Interact with `self.proxmox_api` (the Proxmox API client, currently mocked by `ProxmoxAPIClientMock`). Remember to use `await` for async API calls.
    *   If creating resources that need cleanup, add them to `self.created_resources_for_cleanup`. Example:
        ```python
        self.created_resources_for_cleanup.append({'type': 'new_resource_type', 'node': node, 'id': resource_id, 'name': resource_name})
        ```
    *   Return a dictionary with `{'success': bool, 'message': str, 'data': Optional[Any], 'error': Optional[str]}`.
3.  **Update `run_selected_tests`:** In the same file, find the `run_selected_tests` method. Add a new section for your test category or integrate your test into an existing one.
    ```python
    # Example:
    cat_new = "My New Category"
    if selected_tests_map.get(cat_new, {}).get("My New Test Name In Config", False):
        await self._execute_test_case(test_run_id, cat_new, "My New Test Name In Report",
                                      self.test_your_new_feature, test_config, other_params_if_any)
    ```
4.  **Update Frontend Test Selection (if applicable):** The frontend's Test Configuration page will need to be updated to include the new test option. This typically involves modifying the Vue.js components that render the test selection tree. The `selected_tests` JSON structure in `TestConfiguration.selected_tests` will need to accommodate the new test.
5.  **Write Unit Tests:** Add unit tests for your new service method in `backend/tests/services/test_proxmox_service.py`.

### Proxmox API Interaction
-   The service currently uses `ProxmoxAPIClientMock`. To interact with a real Proxmox server, replace the instantiation of `ProxmoxAPIClientMock` in `ProxmoxNonInteractiveService._connect()` with your chosen Proxmox API library (e.g., `proxmoxer.ProxmoxAPI`).
-   Ensure all API calls are `async` if your chosen library supports asyncio, or run synchronous library calls in a thread pool executor using `await asyncio.to_thread()` if within an async service method.
-   Handle exceptions from API calls gracefully and translate them into appropriate `success=False` returns with error messages.

### Frontend Development
(If applicable, provide guidelines for frontend components, state management, and API interaction.)

## VI. Troubleshooting

### Common Issues
-   **Celery Workers/Beat Not Starting:**
    *   Check Redis connection (`CELERY_BROKER_URL`).
    *   Ensure virtual environment is activated and dependencies are installed.
    *   Verify paths in systemd service files.
    *   Check Celery logs for errors.
-   **Database Connection Problems:**
    *   Verify `DATABASE_URL` in `.env`.
    *   Ensure PostgreSQL/SQLite server is running and accessible.
    *   Check database credentials and permissions.
    *   Make sure migrations have been applied (`alembic upgrade head`).
-   **Proxmox API Errors:**
    *   Verify Proxmox server connection details in Connection Profiles.
    *   Check network connectivity to the Proxmox server.
    *   Ensure the Proxmox user has sufficient permissions for the operations being tested.
    *   Look at `TestCaseResult.logs` for detailed error messages from the Proxmox API.
-   **Tests Not Running as Scheduled:**
    *   Ensure Celery Beat service is running.
    *   Check `celery_app.py` and the `load_schedules()` logic if schedules are not being picked up from the database. (Restart Beat after DB schedule changes with the current simple loader).
    *   Verify the schedule parameters (time, day) in the Test Configuration are correct.
-   **Permission Denied Errors (File System):**
    *   Ensure the user running the FastAPI application and Celery services has write permissions for log directories (if file logging is configured) and any other necessary paths (e.g., `celerybeat-schedule` file for PersistentScheduler).

### Checking Logs
-   **FastAPI Application Logs:** Output to console by Uvicorn/Gunicorn. Configure proper logging for production (e.g., to file or a log management system).
-   **Celery Worker Logs:** Output to console where the worker is started, or to systemd journal if run as a service.
-   **Celery Beat Logs:** Similar to worker logs.
-   **Proxmox Server Logs:** Check logs on the Proxmox VE host (e.g., `/var/log/syslog`, task logs in the Proxmox VE GUI) for issues related to API calls.
-   **Service-Level Logs:** The `ProxmoxNonInteractiveService` and individual test cases may produce print statements or use Python's `logging` module. These will appear in Celery worker logs. `TestCaseResult.logs` in the database also store specific logs for each test.
---
This guide provides a solid foundation for administrators and developers.
