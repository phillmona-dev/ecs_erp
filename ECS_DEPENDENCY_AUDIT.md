# ECS ERP Independence Certification

Date: 2026-05-31

## Scope

This certification covers the deployable ECS add-on tree in this repository.
The system is treated as a greenfield ERP suite with no runtime dependency on
any previous implementation.

## Target Module Structure

- `ecs_base`
- `ecs_finance`
- `ecs_sales`
- `ecs_procurement`
- `ecs_inventory`
- `ecs_hr`
- `ecs_payroll`
- `ecs_construction`
- `ecs_projects`
- `ecs_treasury`
- `ecs_approvals`
- `ecs_self_service`
- `ecs_consolidated_report`
- `ecs_api`

## Certification Results

- Target modules present: passed.
- Extra ECS modules outside target structure: none.
- External historical module dependencies: none.
- Historical model references: none.
- Historical inherited models: none.
- Historical XML IDs: none.
- Historical security groups: none.
- Historical reports: none.
- Historical menus: none.
- Historical transition scripts: none.
- Excluded industry-specific scope: removed.

## Module Graph

All ECS module dependencies now resolve only to:

- target ECS modules, or
- official Odoo modules.

The shared role and governance layer is now `ecs_approvals`.

## Completed Cleanup

- Removed historical wording from ECS comments, docstrings, help text, and manifest descriptions.
- Removed excluded procurement request types, RFQ prefixes, actions, and menus.
- Removed transition-only fields from finance and HR models.
- Removed non-target ECS add-on directories from the deployable tree.
- Removed obsolete ignore entries from `.gitignore`.
- Added missing target modules `ecs_projects` and `ecs_treasury`.
- Replaced the retired security namespace with `ecs_approvals`.
- Updated self-service and consolidated reporting dependencies to target modules only.

## Current Verdict

Certified at source-audit level.

The ECS add-on tree now contains only the target ECS modules and has no detected
runtime reference to any previous implementation. A final database-level
installation test on a clean Odoo 19 instance is still recommended before
production deployment.
