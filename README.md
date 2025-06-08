# Proxmox MCP Testing Service

This project provides a comprehensive web-based service for configuring, executing, and reporting on automated tests against Proxmox Virtual Environment (VE) infrastructures. It enables users to validate Proxmox functionalities, manage test configurations, schedule continuous testing, and analyze detailed results.

The service is designed with a modern architecture, featuring a FastAPI backend, a Vue.js frontend (conceptual, not yet implemented in this phase), Celery for asynchronous task management, and a relational database for persistent storage.

## Documentation

**For comprehensive information on using, administering, and developing this service, please refer to our official documentation:**

➡️ **[Proxmox MCP Testing Service Documentation](./docs/README.md)**

The documentation includes:
*   **User Guide:** Instructions on how to use the web interface to manage Proxmox connections, configure tests, run tests, and view reports.
*   **Administrator & Developer Guide:** Detailed information on system architecture, installation, setup, configuration, API reference, and guidelines for extending the service.

## Features (New Web Service)

*   **Web-Based Interface:** Modern UI for managing all aspects of Proxmox testing.
*   **Connection Management:** Securely store and manage connection profiles for multiple Proxmox servers.
*   **Flexible Test Configuration:**
    *   Define detailed test suites targeting specific Proxmox nodes.
    *   Customize parameters for VM and LXC creation (OS, resources, network).
    *   Select from a comprehensive list of available tests.
    *   Control destructive operations (resource creation/deletion) with clear warnings.
*   **Test Execution & Scheduling:**
    *   Trigger tests manually or schedule them for continuous validation (e.g., nightly, weekly).
    *   Asynchronous test execution using Celery workers.
    *   Real-time monitoring of ongoing test runs.
*   **Comprehensive Reporting:**
    *   List and filter all past test runs.
    *   View detailed reports for each run, including overall status, configuration used, and individual test case results (status, duration, logs).
*   **Extensible Architecture:** Designed to allow developers to easily add new test cases.

## High-Level Architecture

*   **Frontend:** Vue.js (conceptual)
*   **Backend API:** FastAPI (Python)
*   **Task Queue:** Celery with Redis
*   **Database:** PostgreSQL (recommended) / SQLite
*   **Core Logic:** `ProxmoxNonInteractiveService` adapts tests from `comprehensive_mcp_test.py` for automated execution.

## Getting Started (Development & Deployment Overview)

While the full setup instructions are in the [Administrator & Developer Guide](./docs/admin_developer_guide.md), here's a brief overview:

1.  **Prerequisites:** Python 3.8+, PostgreSQL/SQLite, Redis.
2.  **Backend Setup:**
    *   Clone repository, set up a Python virtual environment.
    *   Install dependencies: `pip install -r backend/requirements.txt` (and `backend/requirements-dev.txt` for development).
    *   Configure `.env` file in `backend/` for database URL, Celery settings, secret keys.
    *   Run database migrations: `alembic upgrade head`.
3.  **Run Services:**
    *   **FastAPI Web Server:** `uvicorn app.main:app --reload` (from `backend/` directory).
    *   **Celery Worker:** `celery -A app.celery_app worker -l info -P gevent` (from `backend/` directory).
    *   **Celery Beat Scheduler:** `celery -A app.celery_app beat -l info` (from `backend/` directory).

**Please see the detailed guides in the `docs/` directory for complete instructions.**

## Original SSE MCP Server (Archived)

The previous version of this project was a simpler, standards-compliant Model Context Protocol (MCP) server for managing Proxmox VE resources via Server-Sent Events (SSE). This version enabled AI assistants and LLM applications to interact with Proxmox. For details on this older version, please refer to commit history prior to the introduction of the new web service architecture or specific archive tags if available. Some related files might still be present in the `archive/` directory.

## Contributing

Contributions to the new Proxmox MCP Testing Service are welcome. Please refer to the [Administrator & Developer Guide](./docs/admin_developer_guide.md) for guidelines on extending the service and setting up a development environment.

## License

MIT License - see the (forthcoming) LICENSE file for details. (Assuming MIT, will need to be created).
