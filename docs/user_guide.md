# Proxmox MCP Testing Service - User Guide

## 1. Introduction

### Overview
The Proxmox MCP (Management and Control Plane) Testing Service is a web application designed to automate the testing of Proxmox Virtual Environment (VE) functionalities. It allows users to define test configurations, schedule test runs, and view detailed reports on the outcomes.

### Purpose and Benefits
- **Automated Testing:** Reduces manual effort in verifying Proxmox features.
- **Comprehensive Validation:** Covers a wide range of Proxmox operations, from VM lifecycle management to storage and networking.
- **Consistency:** Ensures tests are run in a standardized way every time.
- **Early Issue Detection:** Helps identify potential problems in your Proxmox setup or after updates.
- **Resource Management:** Can test creation and cleanup of resources, ensuring your Proxmox environment behaves as expected.

### Key Features
- Web-based interface for easy access and management.
- Configuration of Proxmox server connection profiles.
- Detailed test configuration, including:
    - Selection of specific Proxmox nodes.
    - Custom parameters for VM and LXC creation (OS images, resources, network settings).
    - Granular selection of tests to execute.
    - Option to enable or disable destructive tests (resource creation/deletion).
- Manual and scheduled test execution.
- Real-time monitoring of ongoing test runs.
- Comprehensive test reports with overall summaries and detailed logs for each test case.

## 2. Getting Started

### Accessing the Web Interface
- **URL:** The service will be accessible via a URL provided by your administrator (e.g., `http://mcp-tester.example.com`).
- **Default Credentials:** If authentication is enabled, your administrator will provide you with initial login credentials. It's recommended to change your password upon first login if applicable.

### Navigating the Dashboard
The Dashboard is the first page you see after logging in. It typically provides:
- An overview of recent test runs (status, date, duration).
- Quick action buttons:
    - **"Start New Test Run"**: Takes you to the Test Configuration page to set up and launch a new set of tests.
    - **"View All Reports"**: Navigates to the Reports page where you can find all past test runs.
- A navigation menu (usually a sidebar or top bar) to access other sections:
    - **Dashboard**: Returns to the main dashboard view.
    - **Proxmox Connections**: Manage your Proxmox server connection details.
    - **Test Configurations**: Define and manage your test suites.
    - **Test Runs / Reports**: View past and ongoing test executions.

## 3. Managing Proxmox Connections

Before you can configure tests, you need to tell the service how to connect to your Proxmox VE server(s). This is done by creating Connection Profiles.

### How to Add a New Proxmox Connection Profile
1.  Navigate to the "Proxmox Connections" or "Connection Profiles" section from the main menu.
2.  Click on the "Add New Profile" or similar button.
3.  Fill in the required details:
    *   **Profile Name:** A descriptive name for this connection (e.g., "Lab PVE Cluster", "Production Node 1").
    *   **Host:** The hostname or IP address of your Proxmox VE server (e.g., `pve.example.com`).
    *   **Port:** The Proxmox API port (usually `8006`).
    *   **Username:** The Proxmox VE username (e.g., `root@pam` or `testuser@pve`).
    *   **Password/API Token:** The password for the specified user or a Proxmox API token. API tokens are generally recommended for better security.
        *   *Note: Passwords/tokens are stored securely by the backend.*
    *   **Realm:** The Proxmox authentication realm (e.g., `pam` for Linux PAM users, `pve` for Proxmox VE users, or your specific LDAP/AD realm).
    *   **Verify SSL (Optional):** Check this if your Proxmox server uses a valid SSL certificate. Uncheck for self-signed certificates (common in lab environments), but be aware of the security implications.
4.  Click "Save" or "Create Profile". The system may attempt to test the connection.

### Viewing, Editing, and Deleting Connection Profiles
- In the "Proxmox Connections" section, you will see a list of your saved profiles.
- **View:** Some details might be displayed directly in the list.
- **Edit:** Click an "Edit" icon or button associated with the profile to modify its details.
- **Delete:** Click a "Delete" icon or button to remove the profile. Be cautious, as Test Configurations using this profile may need to be updated.

## 4. Configuring Tests

Test Configurations allow you to define exactly how a set of tests should be run.

### Creating a New Test Configuration
1.  Navigate to the "Test Configurations" section.
2.  Click "Create New Configuration" or a similar button.
3.  The configuration form is typically divided into several sections:

    *   **General Information:**
        *   **Configuration Name:** A descriptive name (e.g., "Nightly VM Creation Tests", "Storage Liveness Check").
        *   **Description (Optional):** More details about the purpose of this configuration.

    *   **Proxmox Setup:**
        *   **Proxmox Connection Profile:** Select one of your pre-defined Connection Profiles.
        *   **Target Node:** Specify the Proxmox node on which these tests should primarily operate (e.g., `node1`, `pve-server-03`). Some tests might interact with the whole cluster.

    *   **VM Creation Defaults (if VM tests are selected):**
        *   These settings are used when tests involve creating new Virtual Machines.
        *   **VM ID Range:** A starting and ending ID for test VMs (e.g., 9000-9010). The service will pick IDs from this range. Ensure these IDs do not conflict with existing VMs.
        *   **Operating System Image/ISO:** The ISO or image to use for new VMs (e.g., `local:iso/ubuntu-22.04.iso`, `ceph-storage:vm-images/windows-server-2022.qcow2`). The format depends on your Proxmox storage setup.
        *   **RAM (MB):** Memory allocated to test VMs (e.g., `2048`).
        *   **CPU Cores:** Number of CPU cores for test VMs (e.g., `2`).
        *   **Disk Size (GB):** Size of the primary disk for test VMs (e.g., `20`).
        *   **Storage Pool for Disk:** The Proxmox storage where the VM's disk will be created (e.g., `local-lvm`, `shared-ssd-storage`).
        *   **Network Bridge:** The network bridge for the VM's network interface (e.g., `vmbr0`).
        *   **VLAN Tag (Optional):** If your network requires VLAN tagging.

    *   **LXC Container Creation Defaults (if LXC tests are selected):**
        *   Similar to VM defaults, but for LXC containers.
        *   **Container ID Range:** (e.g., 8000-8010).
        *   **LXC Template:** The template to use for new containers (e.g., `local:vztmpl/ubuntu-22.04-standard.tar.gz`).
        *   **Storage Pool:** (e.g., `local-zfs`).
        *   **RAM (MB), CPU Cores, Disk Size (GB).**
        *   **Network Bridge, Network Configuration (DHCP/Static).**
        *   **Unprivileged Container:** Whether to run as unprivileged (recommended).

    *   **Test Selection:**
        *   This section lists all available tests, usually grouped by category (e.g., "Resource Discovery", "VM Lifecycle", "Storage Management", "Snapshot Management", "Networking").
        *   Check the boxes next to individual tests or entire categories you want to include in this configuration.
        *   Hovering over a test name might provide a brief description of what it does.

    *   **Advanced Options:**
        *   **Enable Destructive Tests:**
            *   **WARNING:** This is a critical setting. If checked, tests that create, modify, or delete resources (like VMs, LXCs, snapshots, storage volumes, users) WILL be performed.
            *   **Only enable this in a dedicated test environment or if you fully understand the implications.** Accidental data loss can occur if misconfigured in a production environment.
            *   If unchecked, such tests will be skipped.
        *   **Automatically Clean Up Created Resources:** If destructive tests are enabled, this option (usually enabled by default) will attempt to delete any resources created during the test run (e.g., test VMs, snapshots).

    *   **Scheduling:**
        *   **Run Manually:** The default; this configuration will only run when you explicitly trigger it.
        *   **Run on a Schedule:**
            *   **Frequency:** Choose from options like "Daily", "Weekly".
            *   **Time:** Specify the time (e.g., `02:00` AM) in UTC or server's local time (clarify with admin).
            *   **Day of Week/Month:** Select specific days if "Weekly" or "Monthly" is chosen.
            *   *Example: Daily at 3:00 AM, or Every Monday at 9:00 AM.*
            *   *A cron-like syntax might also be supported for more complex schedules.*

4.  Click "Save" or "Create Configuration".

### Viewing, Editing, and Deleting Test Configurations
- In the "Test Configurations" section, you'll see a list of all saved configurations.
- **View/Edit:** Click on a configuration's name or an "Edit" button to modify it.
- **Delete:** Click a "Delete" button to remove a configuration. Scheduled runs for this configuration will also be cancelled.

## 5. Running Tests

### Manually Triggering a Test Run
1.  Go to the "Test Configurations" page.
2.  Find the configuration you want to run.
3.  Click the "Run Now" (or a similar play icon) button associated with that configuration.
4.  You may be asked for confirmation.
5.  You will typically be redirected to the Test Execution Page for this new run.

### Understanding Scheduled Test Runs
- If a Test Configuration has a schedule defined, the service will automatically trigger it at the specified times.
- These runs will appear in the Reports list.

### Monitoring an Ongoing Test Run
The Test Execution Page provides real-time updates for a running test:
- **Overall Progress:** A progress bar or percentage indicating how many tests have completed.
- **Status Summary:** Number of tests passed, failed, or skipped so far.
- **Live Log Output:** A stream of messages from the backend showing:
    - Which test case is currently running.
    - Key actions being performed.
    - Status updates for each step.
    - Errors or warnings encountered.
- **Test Case List:** A list of all tests in the run, with status icons (e.g., pending, running, pass, fail, skip).
- **Cancel Option:** A "Cancel" button to attempt to stop the ongoing test run. Note that cancellation might not be immediate, especially if a long operation is already in progress.

## 6. Viewing Reports

### Accessing the List of All Test Runs
1.  Navigate to the "Reports" or "Test Runs" section from the main menu.
2.  You will see a table or list of all past and currently running test executions.

### Filtering and Searching Test Runs
The Reports page usually provides filter options to help you find specific runs:
- **Date Range:** Show runs between a start and end date.
- **Status:** Filter by overall status (e.g., "COMPLETED", "FAILED", "RUNNING", "QUEUED", "PASS", "FAIL" - specific statuses may vary).
- **Test Configuration:** Select a specific Test Configuration to see only its runs, or search by its name.
- **Triggered By:** Filter by how the test was started (e.g., "Manual", "Scheduled").

### Understanding the Summary Information
Each entry in the test run list typically shows:
- **Run ID:** A unique identifier for the test run.
- **Status:** The current overall status of the run.
- **Test Configuration Name:** The name of the configuration used.
- **Start Date & Time:** When the test run began.
- **Duration:** How long the test run took (or has been running).
- **Summary Counts:** (e.g., Total Tests, Passed, Failed).

### Accessing and Interpreting the Detailed Report Page
1.  From the Reports list, click on a Run ID or a "View Details" button to open the Detailed Report Page for that specific run.
2.  This page contains:
    *   **Overall Summary:**
        *   Run ID, final status (e.g., PASS, FAIL, COMPLETED WITH ERRORS).
        *   Start time, end time, total duration.
        *   Total number of test cases, number passed, failed, skipped, and with errors.
        *   Pass percentage.
    *   **Configuration Used:**
        *   A snapshot or link to the full Test Configuration that was used for this run. This includes all Proxmox connection details, target node, VM/LXC parameters, and the list of selected tests. This is crucial for understanding the context of the results.
    *   **Individual Test Case Results:**
        *   A table listing every single test case that was part of this run. For each test case:
            *   **Category:** The functional group it belongs to (e.g., "VM Lifecycle").
            *   **Test Name:** A descriptive name of the test (e.g., "Create VM vm-9001", "Check Snapshot Deletion").
            *   **Status:**
                *   `PASS`: The test completed successfully and all its assertions were met.
                *   `FAIL`: The test completed, but one or more assertions failed (e.g., a VM was expected to be running but was stopped).
                *   `SKIPPED`: The test was not executed (e.g., it was a destructive test and this was disabled, or a prerequisite was not met).
                *   `ERROR`: The test itself encountered an unexpected error during execution (e.g., an API call failed due to a network issue, or an internal script error).
            *   **Duration:** How long this specific test case took to run.
            *   **Message:** A brief summary from the test (e.g., "VM created successfully", "Snapshot 'snap1' not found").
            *   **Logs/Details:** Clicking a "View Logs" or "Details" button/icon may open a modal or expand a section showing detailed log messages, API requests/responses (if captured), or error tracebacks for that specific test case. This is vital for diagnosing failures.

By carefully reviewing these detailed reports, you can understand the health of your Proxmox environment and pinpoint any issues detected by the testing service.
---
This user guide should cover the main interactions a user would have with the service.
