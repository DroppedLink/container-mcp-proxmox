# Proxmox MCP Server Enhancement Plan
## Machine-Readable Schemas & Intelligent Error Handling

### 📋 Project Overview

**Current State**: Proxmox MCP server with 45+ tools across 12 categories
**Goal**: Transform into intelligent, self-documenting system with machine-readable schemas and enhanced error handling
**Target**: Minimize AI agent back-and-forth, improve automation reliability

### 🎯 Enhancement Objectives

1. **Machine-Readable Argument Schemas**
   - Comprehensive parameter definitions with types, constraints, and examples
   - Dynamic validation rules and conditional requirements
   - Context-aware parameter suggestions

2. **Structured Error Responses**
   - Machine-parseable error formats with correction suggestions
   - Missing/invalid argument detection with helpful guidance
   - Related tool suggestions for common workflows

3. **Discovery & Wizard System**
   - One-call context discovery for planning operations
   - Step-by-step wizards for complex operations
   - Parameter validation without execution

### 📁 Current File Structure Analysis

```
src/
├── mcp_server.py (474 lines) ⚠️ NEEDS SPLITTING
├── unified_service.py (312 lines) ✅ OK
├── base_service.py (104 lines) ✅ OK
├── vm_service.py (207 lines) ✅ OK
├── storage_service.py (242 lines) ✅ OK
├── task_service.py (300 lines) ✅ OK
├── cluster_service.py (381 lines) ✅ OK
├── monitoring_service.py (429 lines) ✅ OK
├── network_service.py (350 lines) ✅ OK
├── backup_service.py (117 lines) ✅ OK
├── template_service.py (119 lines) ✅ OK
├── snapshot_service.py (70 lines) ✅ OK
├── user_service.py (149 lines) ✅ OK
└── models.py (228 lines) ✅ OK
```

**Current Tool Categories (45+ tools)**:
- Resource Discovery (3 tools)
- Resource Lifecycle (4 tools) 
- Resource Creation (4 tools)
- Snapshot Management (3 tools)
- Backup & Restore (3 tools)
- Template Management (2 tools)
- User Management (6 tools)
- Storage Management (4 tools)
- Task Management (5 tools)
- Cluster Management (6 tools)
- Performance Monitoring (5 tools)
- Network Management (5 tools)

### 🚀 Implementation Tasks

## Phase 1: Foundation Infrastructure (Week 1)

### Task 1.1: Create Schema Registry System
**File**: `src/schema_registry.py` (~350 lines)

**Purpose**: Central repository for all tool schemas with enhanced metadata

**Key Components**:
```python
class ToolSchema:
    name: str
    description: str
    category: str
    parameters: Dict[str, ParameterSchema]
    examples: List[Dict]
    prerequisites: List[str]
    side_effects: List[str]
    estimated_time: str

class ParameterSchema:
    type: str
    description: str
    required: bool
    default: Any
    constraints: Dict
    examples: List[Any]
    enum_values: Optional[List]
    validation_rules: List[str]
```

**Implementation Steps**:
1. Define base schema classes with full type hints
2. Create schema for each of the 45+ existing tools
3. Add parameter constraints (min/max, patterns, enums)
4. Include realistic examples for each tool
5. Add prerequisite checking rules
6. Implement dynamic enum value fetching (nodes, storage, etc.)

### Task 1.2: Create Parameter Validation System
**File**: `src/parameter_validator.py` (~300 lines)

**Purpose**: Pre-execution parameter validation with intelligent error reporting

**Key Components**:
```python
class ParameterValidator:
    async def validate_parameters(tool_name: str, params: Dict) -> ValidationResult
    async def check_prerequisites(tool_name: str, params: Dict) -> List[str]
    async def suggest_corrections(tool_name: str, params: Dict, errors: List) -> Dict
    async def get_dynamic_options(parameter_name: str, context: Dict) -> List

class ValidationResult:
    valid: bool
    errors: List[ValidationError]
    suggestions: List[str]
    corrected_params: Dict
```

**Implementation Steps**:
1. Build validation engine using schema definitions
2. Add context-aware validation (check if nodes exist, VM IDs available)
3. Implement suggestion system for common errors
4. Add cross-parameter validation (storage capacity vs VM size)
5. Create dynamic option fetching (available storage, active nodes)

### Task 1.3: Create Enhanced Error Handler
**File**: `src/error_handler.py` (~200 lines)

**Purpose**: Structured, machine-readable error responses

**Key Components**:
```python
class ErrorResponse:
    success: bool = False
    error_code: str
    message: str
    details: ErrorDetails
    suggestions: List[str]
    tool_schema: Dict

class ErrorDetails:
    missing_required: List[str]
    invalid_values: Dict[str, InvalidValue]
    context_errors: List[str]
    related_tools: List[str]

class InvalidValue:
    provided: Any
    expected: str
    example: Any
    valid_options: Optional[List]
```

**Implementation Steps**:
1. Define comprehensive error response structure
2. Create error categorization system
3. Build suggestion engine for common fix patterns
4. Add related tool recommendations
5. Implement context-aware error messages

### Task 1.4: Create Enhanced Type Definitions
**File**: `src/enhanced_types.py` (~150 lines)

**Purpose**: Type definitions for the new schema and validation system

**Implementation Steps**:
1. Define all TypedDict classes for schemas
2. Add validation result types
3. Create error response types
4. Add wizard and discovery types

## Phase 2: MCP Server Restructuring (Week 2)

### Task 2.1: Split MCP Server File
**Critical**: `mcp_server.py` is at 474 lines and will exceed 500 with enhancements

**New Structure**:
- `src/mcp_server.py` (~200 lines) - Core server setup only
- `src/tool_definitions.py` (~250 lines) - Schema-based tool definitions
- `src/tool_handlers.py` (~200 lines) - Tool execution with validation
- `src/discovery_tools.py` (~150 lines) - New discovery tools

**Implementation Steps**:
1. Extract tool schema definitions to `tool_definitions.py`
2. Move tool execution logic to `tool_handlers.py`
3. Keep only server startup and lifespan in `mcp_server.py`
4. Create new discovery tools in separate file

### Task 2.2: Create Tool Definitions Module
**File**: `src/tool_definitions.py` (~250 lines)

**Purpose**: Schema-based tool definitions using the schema registry

**Implementation Steps**:
1. Import schema registry
2. Define all 45+ tools using enhanced schemas
3. Add dynamic parameter validation
4. Include examples and prerequisites for each tool

### Task 2.3: Create Tool Handlers Module  
**File**: `src/tool_handlers.py` (~200 lines)

**Purpose**: Tool execution logic with integrated validation

**Implementation Steps**:
1. Create validation wrapper for all tool calls
2. Implement structured error responses
3. Add parameter preprocessing and normalization
4. Include execution timing and logging

## Phase 3: Discovery & Wizard System (Week 2-3)

### Task 3.1: Create Context Manager
**File**: `src/context_manager.py` (~250 lines)

**Purpose**: Runtime context discovery and caching

**Key Components**:
```python
class ProxmoxContext:
    async def get_available_nodes() -> List[NodeInfo]
    async def get_available_storage(node: str) -> List[StorageInfo]
    async def get_available_templates() -> List[TemplateInfo]
    async def get_vm_id_suggestions(count: int) -> List[int]
    async def check_resource_availability(requirements: Dict) -> AvailabilityCheck
```

**Implementation Steps**:
1. Build node discovery with health status
2. Add storage discovery with capacity information
3. Create template and ISO discovery
4. Implement VM ID availability checking
5. Add resource capacity validation

### Task 3.2: Create Wizard Service
**File**: `src/wizard_service.py` (~450 lines)

**Purpose**: Step-by-step wizards and discovery tools

**New Tools to Implement**:
1. `describe_tool` - Get complete schema for any tool
2. `list_tool_categories` - Browse tools by category  
3. `discover_context` - Get all available resources in one call
4. `validate_parameters` - Pre-validate without execution
5. `vm_creation_wizard` - Step-by-step VM creation
6. `migration_wizard` - Plan and validate migrations
7. `backup_wizard` - Plan backup strategies
8. `suggest_parameters` - AI-friendly parameter suggestions

**Implementation Steps**:
1. Create tool introspection methods
2. Build comprehensive context discovery
3. Implement parameter validation endpoints
4. Create step-by-step wizards for complex operations
5. Add intelligent parameter suggestion system

### Task 3.3: Create Discovery Tools Module
**File**: `src/discovery_tools.py` (~150 lines)

**Purpose**: New MCP tools for discovery and validation

**Implementation Steps**:
1. Implement `describe_tool` with full schema output
2. Create `discover_context` for one-call environment discovery
3. Add `validate_parameters` for pre-execution validation
4. Build `suggest_parameters` for AI assistance

## Phase 4: Service Integration (Week 3)

### Task 4.1: Update Unified Service
**File**: `src/unified_service.py` (312 → ~400 lines)

**Implementation Steps**:
1. Integrate parameter validation wrapper
2. Add context management integration
3. Update error handling to use structured responses
4. Add validation hooks to all service methods

### Task 4.2: Update Base Service
**File**: `src/base_service.py` (104 → ~150 lines)

**Implementation Steps**:
1. Add validation hooks to base methods
2. Integrate structured error handling
3. Add context discovery base methods
4. Update connection handling with better errors

### Task 4.3: Update Domain Services
**Files**: All service files (+50-100 lines each)

**Services to Update**:
- `vm_service.py`
- `storage_service.py` 
- `task_service.py`
- `cluster_service.py`
- `monitoring_service.py`
- `network_service.py`
- `backup_service.py`
- `template_service.py`
- `snapshot_service.py`
- `user_service.py`

**Implementation Steps for Each**:
1. Add parameter validation to all methods
2. Update error handling to use structured responses
3. Add context checking where appropriate
4. Include suggestion generation for common errors

## Phase 5: Testing & Validation (Week 4)

### Task 5.1: Update Test Suite
**File**: `comprehensive_mcp_test.py` 

**Implementation Steps**:
1. Add tests for all new discovery tools
2. Test parameter validation system
3. Validate error response structure
4. Test wizard functionality
5. Verify backward compatibility

### Task 5.2: Create Schema Validation Tests
**New File**: `test_schema_validation.py`

**Implementation Steps**:
1. Test all tool schemas are valid
2. Validate parameter constraints work correctly
3. Test dynamic option fetching
4. Verify error message quality

### Task 5.3: Performance Testing
**Implementation Steps**:
1. Measure validation overhead
2. Test discovery tool performance
3. Validate context caching efficiency
4. Ensure no regression in existing tools

## 🎯 Success Criteria

### Functional Requirements
- [ ] All 45+ existing tools maintain backward compatibility
- [ ] New discovery tools provide comprehensive context in single calls
- [ ] Parameter validation catches errors before execution
- [ ] Error responses are machine-readable with helpful suggestions
- [ ] Wizards guide users through complex operations

### Technical Requirements  
- [ ] All files remain under 500 lines
- [ ] Clean separation of concerns maintained
- [ ] Performance impact < 10ms per tool call
- [ ] Comprehensive test coverage > 90%
- [ ] Documentation updated for all new features

### AI Agent Benefits
- [ ] Reduced round-trips for parameter discovery
- [ ] Self-healing error responses with suggestions
- [ ] One-call environment discovery
- [ ] Intelligent parameter suggestions
- [ ] Validation without execution

## 🔧 Implementation Notes

### Key Patterns to Follow
1. **Backward Compatibility**: All existing tool interfaces unchanged
2. **Incremental Enhancement**: New features opt-in, gradual migration
3. **Consistent Error Handling**: Structured responses across all tools
4. **Performance First**: Validation should be fast, caching where possible
5. **Documentation**: Self-documenting schemas with examples

### Architecture Principles
1. **Single Responsibility**: Each file has one clear purpose
2. **Dependency Injection**: Services receive dependencies, not hardcoded
3. **Async First**: All new code uses async/await patterns
4. **Type Safety**: Full type hints for all new code
5. **Error Transparency**: Never hide errors, always provide actionable feedback

### Testing Strategy
1. **Unit Tests**: Each component tested in isolation
2. **Integration Tests**: End-to-end tool execution testing
3. **Performance Tests**: Validation overhead measurement
4. **Regression Tests**: Ensure existing functionality unaffected
5. **User Acceptance**: Test from AI agent perspective

## 📚 Reference Information

### Current Tool List (45+ tools)
```
Resource Discovery: list_resources, get_resource_status, list_templates
Resource Lifecycle: start_resource, stop_resource, shutdown_resource, restart_resource  
Resource Creation: create_vm, create_container, delete_resource, resize_resource
Snapshot Management: create_snapshot, get_snapshots, delete_snapshot
Backup & Restore: create_backup, list_backups, restore_backup
Template Management: create_template, clone_vm
User Management: create_user, list_users, delete_user, set_permissions, list_roles, list_permissions
Storage Management: list_storage, get_storage_status, list_storage_content, get_suitable_storage
Task Management: list_tasks, get_task_status, cancel_task, list_backup_jobs, create_backup_job
Cluster Management: get_cluster_health, get_node_status_detailed, list_cluster_resources, migrate_vm, set_node_maintenance, get_cluster_config
Performance Monitoring: get_vm_stats, get_node_stats, get_storage_stats, list_alerts, get_resource_usage
Network Management: list_networks, get_network_config, get_node_network, list_firewall_rules, get_firewall_status
```

### Environment Setup
```bash
# Dependencies (check requirements.txt)
pip install mcp proxmoxer starlette python-dotenv

# Environment variables needed
PROXMOX_HOST=your-proxmox-host
PROXMOX_USER=your-username
PROXMOX_PASSWORD=your-password
```

### Key Files to Understand Before Starting
1. `src/unified_service.py` - Main service coordination
2. `src/base_service.py` - Base service patterns
3. `src/mcp_server.py` - Current MCP implementation
4. `comprehensive_mcp_test.py` - Testing patterns

---

**Priority**: High - AI agents currently struggle with parameter discovery and error recovery
**Complexity**: Medium - Well-defined requirements, existing codebase is clean
**Timeline**: 3-4 weeks for full implementation
**Impact**: High - Will significantly improve AI agent automation success rate