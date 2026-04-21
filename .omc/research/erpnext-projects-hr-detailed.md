# ERPnext Projects, HR & Support Modules - Detailed Analysis

Source: `/Users/changtom/Downloads/UltrERP/reference/erpnext-develop`

---

## 1. PROJECTS MODULE

### 1.1 Project

**Doctype**: `erpnext/projects/doctype/project/project.json`

#### Fields
- **Naming**: `PROJ-.####` via naming series
- **Core Fields**: `project_name`, `status` (Open/Completed/Cancelled), `project_type` (Link), `priority` (Medium/Low/High), `is_active` (Yes/No)
- **Dates**: `expected_start_date`, `expected_end_date`, `actual_start_date` (read_only, via Timesheet), `actual_end_date` (read_only)
- **Customer**: `customer` (Link), `sales_order` (Link)
- **Costing/Billing**: `estimated_costing`, `total_costing_amount` (via Timesheet), `total_purchase_cost` (via Purchase Invoice), `total_sales_amount` (via Sales Order), `total_billable_amount`, `total_billed_amount`, `total_consumed_material_cost` (via Stock Entry)
- **Margin**: `gross_margin`, `per_gross_margin` (calculated)
- **Cost Center**: `cost_center` (Link)
- **Department**: `department` (Link)
- **Progress**: `percent_complete_method` (Manual/Task Completion/Task Progress/Task Weight), `percent_complete` (read_only)
- **Auto-Progress**: `collect_progress` (Check), `holiday_list`, `frequency` (Hourly/Twice Daily/Daily/Weekly), `from_time`, `to_time`, `first_email`, `second_email`, `daily_time_to_send`, `day_to_send`, `weekly_time_to_send`, `subject`, `message`
- **Users**: `users` child table (Project User: user, email, image, full_name, project_status, welcome_email_sent)
- **Template**: `project_template` (Link) - set_only_once
- **Notes**: `notes` (Text Editor)

#### State Machine
- Statuses: **Open**, **Completed**, **Cancelled**
- Valid transitions: Open -> Completed, Open -> Cancelled, Completed -> Open (manual via `set_project_status`)
- Percent complete auto-calculated based on `percent_complete_method`:
  - `Task Completion`: (Completed + Cancelled tasks) / Total tasks
  - `Task Progress`: Sum of task progress / Total tasks
  - `Task Weight`: Weighted average by task_weight
  - `Manual`: Direct input; set to 100 when status = Completed

#### Permissions
| Role | Permissions |
|------|-------------|
| Projects User | CRUD + share + report |
| Projects Manager | CRUD + export + share + report |
| Desk User | Read level 1 |
| Employee | Select + share + export + print + email + report |

#### Controller Logic (`project.py`)
- `onload()`: Sets activity_summary from Timesheet Detail
- `validate()`: copy_from_template, send_welcome_email, update_costing, update_percent_complete, validate dates
- `copy_from_template()`: Creates tasks from Project Template, maps dependencies and parent tasks
- `update_costing()`: Aggregates from Timesheet Detail (costing_amount, billing_amount, start/end dates, hours), Purchase Invoice, Sales Order, Stock Entry
- `calculate_gross_margin()`: total_billed_amount - (total_costing_amount + total_purchase_cost + consumed_material_cost)
- `update_project()`: Called externally by Task to recalculate costing/percent
- `after_insert()`: Links sales_order to project; copies from template
- `on_trash()`: Unlinks sales_order
- `send_welcome_email()`: Sends email to project users with collaboration link
- `before_print()`: Reloads activity summary

#### Key Functions
- `hourly_reminder()`, `project_status_update_reminder()`, `daily_reminder()`, `twice_daily_reminder()`, `weekly_reminder()`: Scheduled progress collection
- `collect_project_status()`: Parses email replies for project updates
- `send_project_status_email_to_users()`: Sends daily project summary
- `update_project_sales_billing()`: Periodic sync with sales/billing
- `create_kanban_board_if_not_exists()`: Creates Kanban board for tasks
- `set_project_status()`: Bulk-set status on project and all tasks

#### Child Tables
- **Project User**: user, email, image, full_name, project_status, welcome_email_sent

#### Integration Points
- Sales Order (project field set on SO)
- Timesheet Detail (costing/billing/time aggregation)
- Purchase Invoice Item (purchase cost)
- Sales Invoice Item (billed amount)
- Stock Entry (consumed material)
- Task (via project field)

---

### 1.2 Task

**Doctype**: `erpnext/projects/doctype/task/task.json`

#### Fields
- **Naming**: `TASK-.YYYY.-.#####` (expression-based)
- **Core Fields**: `subject` (reqd), `project` (Link), `issue` (Link), `type` (Link to Task Type), `color`
- **Structure**: `is_group` (Check), `parent_task` (Link, tree), `template_task`
- **Status**: Open/Working/Pending Review/Overdue/Template/Completed/Cancelled
- **Priority**: Low/Medium/High/Urgent
- **Timeline**: `exp_start_date` (Datetime), `exp_end_date` (Datetime), `expected_time` (hours), `progress` (%)
- **Is Milestone**: `is_milestone` (Check)
- **Dependencies**: `depends_on` (Table: Task Depends On), `depends_on_tasks` (hidden Code, read_only)
- **Actual**: `act_start_date`, `act_end_date`, `actual_time` (read_only, via Timesheet)
- **Costing**: `total_costing_amount`, `total_billing_amount` (read_only)
- **Template**: `is_template`, `start` (Begin On Days), `duration` (Days)
- **Completion**: `completed_by` (User), `completed_on` (Date)
- **Review**: `review_date` (depends on Closed/Pending Review)
- **Closing**: `closing_date` (depends on Closed)
- **Tree Fields**: `lft`, `rgt`, `old_parent` (NestedSet)

#### State Machine
- Statuses: **Open**, **Working**, **Pending Review**, **Overdue**, **Template**, **Completed**, **Cancelled**
- Valid transitions:
  - Open -> Working, Pending Review, Overdue, Completed, Cancelled
  - Working -> Pending Review, Open, Overdue, Completed, Cancelled
  - Pending Review -> Open, Completed, Cancelled
  - Overdue -> any except Template
  - Template: Special status for template tasks only
- Task cannot be completed if dependent tasks are not completed/cancelled

#### Controller Logic (`task.py`)
- `validate()`: dates, progress, status, dependencies, parent is group, completed_on
- `validate_dates()`: from/to date validation, parent expected end date, project dates
- `validate_status()`: Cannot complete if dependencies not met; closes assignments on complete
- `update_depends_on()`: Builds comma-separated depends_on_tasks string
- `on_update()`: Updates NSM model, checks recursion, reschedules dependent tasks, updates project, unassigns todo, populates depends_on
- `check_recursion()`: Detects circular task dependencies (max 15 levels)
- `reschedule_dependent_tasks()`: When task end date changes, shifts dependent task dates
- `update_time_and_costing()`: Aggregates from Timesheet Detail
- `has_webform_permission()`: Checks Project User table

#### Permissions
| Role | Permissions |
|------|-------------|
| Projects User | CRUD + share + report |

#### Integration Points
- Project (task belongs to project)
- Issue (task linked from issue)
- Task Depends On (dependency table)
- Timesheet Detail (actual time/costing/billing)

---

### 1.3 Timesheet

**Doctype**: `erpnext/projects/doctype/timesheet/timesheet.json`

#### Fields
- **Naming**: `TS-.YYYY.-` (series)
- **Core Fields**: `employee` (Link), `employee_name` (read_only), `department` (read_only), `user` (read_only)
- **Project/Customer**: `parent_project` (Link), `customer` (Link), `sales_invoice` (read_only)
- **Dates**: `start_date`, `end_date`
- **Time Logs** (Table - Timesheet Detail): activity_type, task, project, from_time, to_time, hours, completed
- **Billing**: `total_hours`, `total_billable_hours`, `total_billed_hours`, `total_costing_amount`, `total_billable_amount`, `total_billed_amount`, `per_billed`
- **Base amounts**: `base_total_costing_amount`, `base_total_billable_amount`, `base_total_billed_amount`
- **Status**: Draft/Submitted/Partially Billed/Billed/Payslip/Completed/Cancelled

#### State Machine
- Statuses: **Draft**, **Submitted**, **Partially Billed**, **Billed**, **Payslip**, **Completed**, **Cancelled**
- Submit -> Bill ->Payslip flow; can be cancelled from Draft/Submitted

#### Permissions
| Role | Permissions |
|------|-------------|
| Projects User | CRUD + submit + amend + cancel |
| HR User | CRUD + submit + amend + cancel |
| Manufacturing User | CRUD + submit + amend + cancel |
| Employee | Read + write (create only) |
| Accounts User | CRUD + submit + amend + cancel (level 0 and 1) |

#### Child Tables
- **Timesheet Detail**: activity_type, task, project, from_time, to_time, hours, completed, billing_amount, costing_amount, base_billing_amount, base_costing_amount

---

### 1.4 Activity Type

**Doctype**: `erpnext/projects/doctype/activity_type/activity_type.json`

#### Fields
- `activity_type` (unique, reqd), `costing_rate`, `billing_rate`, `disabled`

#### Permissions
| Role | Permissions |
|------|-------------|
| System Manager | Full |
| Projects User | Read + write + share + report |
| Employee | Read only |

---

### 1.5 Project Template

**Doctype**: `erpnext/projects/doctype/project_template/project_template.json`

#### Fields
- `project_type` (Link), `disabled`, `tasks` (Table: Project Template Task)

#### Child Tables
- **Project Template Task**: task (Link), start (days), duration (days), task_weight

#### Usage
Used when creating a new Project to auto-generate tasks. When `project_template` is set on Project, `copy_from_template()` creates tasks, maps dependencies and parent tasks.

---

### 1.6 Project Type

**Doctype**: `erpnext/projects/doctype/project_type/project_type.json`

#### Fields
- `project_type` (Data, reqd)

---

### 1.7 Task Type

**Doctype**: `erpnext/projects/doctype/task_type/task_type.json`

#### Fields
- `task_type`, `weight` (Float), `disabled`

---

### 1.8 Activity Cost

**Doctype**: `erpnext/projects/doctype/activity_cost/activity_cost.json`

#### Fields
- `employee` (Link), `employee_name` (read_only), `department` (Link), `activity_type` (Link), `costing_rate`, `billing_rate`, `currency` (Link)

---

### 1.9 Task Depends On

**Doctype**: `erpnext/projects/doctype/task_depends_on/task_depends_on.json`

#### Fields
- `task` (Link), `subject` (Data, read_only)

---

### 1.10 Dependent Task

**Doctype**: `erpnext/projects/doctype/dependent_task/dependent_task.json`

#### Fields
- `task` (Link), `subject` (Data, read_only)

---

### 1.11 Project Update

**Doctype**: `erpnext/projects/doctype/project_update/project_update.json`

#### Fields
- `project` (Link), `date`, `time`, `sent` (Check), `users` (Table: Project Update User with project_status)
- Used for progress collection via email

---

### 1.12 Projects Settings

**Doctype**: `erpnext/projects/doctype/projects_settings/projects_settings.json`

#### Fields
- `collect_progress` (Check), `send_progress_reminder` (Check), `based_on` (Task Completion/Task Progress)

---

### 1.13 Project Reports

| Report | Description |
|--------|-------------|
| Daily Timesheet Summary | Timesheet data aggregated by day |
| Timesheet Billing Summary | Billable vs billed hours analysis |
| Project Summary | Project progress and costing overview |
| Delayed Tasks Summary | Tasks past expected end date |
| Project-wise Stock Tracking | Material consumption per project |

---

### 1.14 Project Dashboard Charts

- Project Summary (completed vs open projects)
- Completed Projects (trend chart)
- Open Projects (number card)
- Timesheet Working Hours (number card)
- Non-completed Tasks (number card)

---

## 2. SUPPORT MODULE

### 2.1 Issue

**Doctype**: `erpnext/support/doctype/issue/issue.json`

#### Fields
- **Naming**: `ISS-.YYYY.-` (series)
- **Core Fields**: `subject` (reqd, global search), `status` (Open/Replied/On Hold/Resolved/Closed), `priority` (Link), `issue_type` (Link), `issue_split_from`
- **Customer**: `customer` (Link), `raised_by` (email, global search), `customer_name` (read_only)
- **Description**: `description` (Text Editor)
- **SLA**: `service_level_agreement` (Link), `response_by` (Datetime, read_only), `reset_service_level_agreement` (Button)
- **SLA Status**: `agreement_status` (First Response Due/Resolution Due/Fulfilled/Failed, read_only), `sla_resolution_by`, `sla_resolution_date`
- **Response Metrics**: `first_response_time`, `first_responded_on`, `avg_response_time`, `resolution_time`, `user_resolution_time`, `on_hold_since`, `total_hold_time`
- **Resolution**: `resolution_details` (Text Editor)
- **Reference**: `lead` (Link), `contact` (Link), `email_account` (Link), `project` (Link), `company` (Link), `via_customer_portal` (Check)
- **Timestamps**: `opening_date`, `opening_time`, `content_type`, `attachment`

#### State Machine
- Statuses: **Open**, **Replied**, **On Hold**, **Resolved**, **Closed**
- Auto-close: When `close_issue_after_days` is set in Support Settings, replied tickets auto-close after N days
- SLA paused on: Configurable statuses via Pause SLA On Status table

#### Permissions
| Role | Permissions |
|------|-------------|
| Support Team | Full |

#### Controller Logic (`issue.py`)
- `validate()`: Creates communication if via_customer_portal; sets lead/contact from raised_by email
- `on_update()`: Creates communication in timeline if via_customer_portal
- `set_lead_contact()`: Parses email to find Lead/Contact/Customer
- `create_communication()`: Creates Communication linked to issue
- `split_issue()`: Creates new issue from current, resets SLA, replicates communications
- `reset_issue_metrics()`: Clears resolution_time, user_resolution_time

#### Key Functions
- `auto_close_tickets()`: Scheduled job to close old replied tickets
- `set_multiple_status()`: Bulk status update
- `make_task()`: Map Issue to Task
- `make_issue_from_communication()`: Create Issue from email Communication
- `set_first_response_time()`: Triggered on communication; calculates first response time based on SLA working hours
- `calculate_first_response_time()`: Complex calculation accounting for working hours, holidays, multi-day scenarios

#### Integration Points
- Customer/Lead/Contact
- Project
- Communication (timeline)
- Service Level Agreement
- Task (via make_task)

---

### 2.2 Service Level Agreement (SLA)

**Doctype**: `erpnext/support/doctype/service_level_agreement/service_level_agreement.json`

#### Fields
- **Naming**: `SLA-{document_type}-{service_level}`
- **Core Fields**: `service_level` (reqd), `document_type` (Link to DocType, e.g., Issue), `enabled`
- **Entity**: `entity_type` (Customer/Customer Group/Territory), `entity` (Dynamic Link), `condition` (Python expression)
- **Default**: `default_service_level_agreement`
- **Valid Period**: `start_date`, `end_date`
- **Priority**: `default_priority` (Issue Priority), `priorities` (Table: Service Level Priority - priority, response_time, resolution_time)
- **SLA Fulfillment**: `sla_fulfilled_on` (Table: SLA Fulfilled On Status - status)
- **SLA Pause**: `pause_sla_on` (Table: Pause SLA On Status - status)
- **Working Hours**: `support_and_resolution` (Table: Service Day - workday, start_time, end_time)
- **Holiday List**: `holiday_list` (Link)
- **Apply**: `apply_sla_for_resolution` (Check)

#### Child Tables
- **Service Level Priority**: priority (Link), response_time (Duration), resolution_time (Duration)
- **SLA Fulfilled On Status**: status (Data)
- **Pause SLA On Status**: status (Data)
- **Service Day**: workday (Data), start_time (Time), end_time (Time)

#### Permissions
| Role | Permissions |
|------|-------------|
| System Manager | Full |
| Desk User | Read |

---

### 2.3 Issue Priority

**Doctype**: `erpnext/support/doctype/issue_priority/issue_priority.json`

#### Fields
- `name` (via fieldname), `color`

---

### 2.4 Issue Type

**Doctype**: `erpnext/support/doctype/issue_type/issue_type.json`

#### Fields
- `name` (via fieldname)

---

### 2.5 Warranty Claim

**Doctype**: `erpnext/support/doctype/warranty_claim/warranty_claim.json`

#### Fields
- **Naming**: `SER-WRN-.YYYY.-` (series)
- **Core Fields**: `status` (Open/Closed/Work In Progress/Cancelled), `complaint_date`, `customer` (Link, reqd)
- **Item**: `serial_no` (Link), `item_code` (Link), `item_name` (read_only), `description` (read_only)
- **Warranty**: `warranty_amc_status` (Under Warranty/Out of Warranty/Under AMC/Out of AMC), `warranty_expiry_date`, `amc_expiry_date`
- **Resolution**: `resolution_date` (Datetime), `resolved_by` (User), `resolution_details`
- **Contact**: `customer_name`, `contact_person`, `contact_display`, `contact_mobile`, `contact_email`
- **Address**: `territory`, `customer_group`, `customer_address`, `address_display`, `service_address`
- **Company**: `company` (Link, reqd)
- **Complaint**: `complaint` (Text Editor, reqd)

#### State Machine
- Statuses: **Open**, **Work In Progress**, **Closed**, **Cancelled**

#### Permissions
| Role | Permissions |
|------|-------------|
| Maintenance User | Full |

---

### 2.6 Maintenance Schedule

**Note**: This doctype exists but was not deeply analyzed in this session.

---

### 2.7 Support Settings

**Doctype**: `erpnext/support/doctype/support_settings/support_settings.json`

#### Fields
- `close_issue_after_days` (Int, default 0 = disabled)

---

### 2.8 Support Reports

| Report | Description |
|--------|-------------|
| Issue Summary | Issue counts by status/type/priority |
| Support Hour Distribution | Hours spent on support |
| First Response Time for Issues | SLA first response metrics |
| Issue Analytics | Detailed issue analytics |

---

## 3. HR MODULE (Setup Doctypes)

The HR module in ERPnext uses setup doctypes (in `erpnext/setup/doctype/`) rather than a dedicated `hr/` directory.

### 3.1 Employee

**Doctype**: `erpnext/setup/doctype/employee/employee.json`

#### Fields
- **Naming**: `HR-EMP-` (series)
- **Basic Info**: `employee_name` (read_only, from first+middle+last), `status` (Active/Inactive/Suspended/Left), `employee_number`
- **Personal**: `salutation`, `first_name`, `middle_name`, `last_name`, `gender`, `date_of_birth`, `marital_status`, `blood_group`
- **Family**: `family_background` (Small Text), `health_details` (Small Text)
- **Contact**: `cell_number`, `personal_email`, `company_email`, `prefered_email` (read_only)
- **Company Details**: `company` (Link, reqd), `department` (Link), `designation` (Link), `branch` (Link), `reports_to` (Link to Employee)
- **Employment**: `date_of_joining`, `scheduled_confirmation_date` (Offer Date), `final_confirmation_date` (Confirmation Date), `contract_end_date`, `notice_number_of_days`, `date_of_retirement`
- **Salary**: `ctc` (Cost to Company), `salary_currency`, `salary_mode` (Bank/Cash/Cheque), `bank_name`, `bank_ac_no`, `iban`
- **Attendance**: `attendance_device_id` (Biometric/RF tag ID, unique)
- **Holiday List**: `holiday_list` (Link)
- **Image**: `image`
- **Bio**: `bio` (Text Editor)
- **Education**: `education` (Table: Employee Education)
- **Work History**: `external_work_history` (Table), `internal_work_history` (Table)
- **Exit**: `resignation_letter_date`, `relieving_date`, `reason_for_leaving`, `leave_encashed`, `encashment_date`, `held_on` (exit interview), `new_workplace`, `feedback`
- **Emergency**: `emergency_contact_details` section with `person_to_be_contacted`, `emergency_phone_number`, `relation`
- **Address**: `current_address`, `current_accommodation_type`, `permanent_address`, `permanent_accommodation_type`
- **User**: `user_id` (Link to User), `create_user_permission` (Check), `create_user_automatically` (Check)
- **Passport**: `passport_number`, `date_of_issue`, `valid_upto`, `place_of_issue`
- **Tree**: `lft`, `rgt`, `old_parent` (NestedSet via reports_to)
- **Flags**: `unsubscribed`

#### State Machine
- Statuses: **Active**, **Inactive**, **Suspended**, **Left**
- `relieving_date` is mandatory when status = Left

#### Permissions
| Role | Permissions |
|------|-------------|
| Employee | Read + print + email + report |
| HR User | Full + import/export |
| HR Manager | Full + import/export |

#### Features
- `is_tree`: Yes (via reports_to parent field)
- `image_field`: image
- `create_user_automatically`: Creates User from preferred email on save

---

### 3.2 Department

**Doctype**: `erpnext/setup/doctype/department/department.json`

#### Fields
- `department_name` (reqd), `parent_department` (Link), `company` (Link, reqd), `is_group` (Check), `disabled` (Check)
- Tree structure via NestedSet

#### Permissions
| Role | Permissions |
|------|-------------|
| HR User | Full |
| Academics User | Full |
| HR Manager | Full |
| Employee | Select |

---

### 3.3 Designation

**Doctype**: `erpnext/setup/doctype/designation/designation.json`

#### Fields
- `designation_name` (Data, reqd)

#### Permissions
| Role | Permissions |
|------|-------------|
| HR User | Full |
| HR Manager | Full |

---

### 3.4 Branch

**Doctype**: `erpnext/setup/doctype/branch/branch.json`

#### Fields
- `branch` (Data, reqd)

---

### 3.5 Holiday List

**Doctype**: `erpnext/setup/doctype/holiday_list/holiday_list.json`

#### Fields
- `holiday_list_name` (unique, reqd), `from_date`, `to_date`, `total_holidays` (read_only)
- `weekly_off` (Select: Sunday-Saturday), `get_weekly_off_dates` (Button)
- `is_half_day` (Check)
- `holidays` (Table: Holiday - holiday_date, description, is_half_day)
- `country`, `subdivision` (for local holidays), `get_local_holidays` (Button)
- `color`

#### Features
- Auto-calculate total holidays
- Add weekly offs automatically
- Import local holidays by country/subdivision

#### Permissions
| Role | Permissions |
|------|-------------|
| HR Manager | Full |

---

### 3.6 Employment Type

**Doctype**: `erpnext/setup/doctype/employment_type/employment_type.json`

#### Fields
- `employee_type_name` (Data, reqd)

---

### 3.7 Employee Education (Child Table)

**Doctype**: `erpnext/setup/doctype/employee_education/employee_education.json`

#### Fields
- `school_university`, `qualification`, `level`, `year_of_passing`, `result`

---

### 3.8 Employee External Work History (Child Table)

**Doctype**: `erpnext/setup/doctype/employee_external_work_history/employee_external_work_history.json`

#### Fields
- `company`, `designation`, `from_date`, `to_date`, `total_experience` (Float)

---

### 3.9 Employee Internal Work History (Child Table)

**Doctype**: `erpnext/setup/doctype/employee_internal_work_history/employee_internal_work_history.json`

#### Fields
- `branch`, `department`, `designation`, `from_date`, `to_date`, `company`

---

### 3.10 Cost Center

**Doctype**: `erpnext/accounts/doctype/cost_center/cost_center.json`

#### Fields
- `cost_center_name`, `parent_cost_center`, `company`, `is_group`, `disabled`, `lft`, `rgt`
- Tree structure

---

## 4. CROSS-MODULE INTEGRATION

### 4.1 Project Billing Flow
1. Employee logs time via Timesheet (activity_type, hours, task, project)
2. Timesheet Detail captures costing_amount (based on Activity Cost) and billing_amount
3. Project aggregates total_costing_amount, total_billable_amount from Timesheet Detail
4. Sales Invoice created from Timesheet (or manually) with billing amount
5. Project updates total_billed_amount from Sales Invoice Item

### 4.2 Task Dependencies and Gantt
- Tasks support `depends_on` relationships via Task Depends On table
- `depends_on_tasks` is a comma-separated denormalized field for quick lookups
- `reschedule_dependent_tasks()` auto-shifts dependent task dates when predecessor changes
- Project Template stores task dependencies as template_task references
- `dependency_mapping()` recreates dependencies when project is created from template
- Gantt chart visualization available via tree view

### 4.3 Attendance via Biometric/Geo-fencing
- Employee has `attendance_device_id` field (Biometric/RF tag ID)
- This integrates with external attendance systems that can push data
- Holiday List used for attendance calculations

### 4.4 Issue Lifecycle
1. Issue created (via email, portal, or manual)
2. SLA applied based on customer/priority
3. Response tracked via first_response_time calculation
4. Status flows: Open -> Replied -> On Hold/Resolved -> Closed
5. Auto-close scheduled job for old replied tickets
6. Issue can be split into multiple issues

### 4.5 Issue Escalation (SLA)
- SLA defines response_time and resolution_time per priority
- Response By and Resolution By dates calculated from creation + working hours
- Working hours configured via Service Day table (per weekday)
- Holidays excluded via Holiday List
- SLA can be paused on configurable statuses (Pause SLA On Status)
- SLA fulfilled when status matches configured fulfilled statuses

---

## 5. KEY GAPS & FEATURES FOR ULTRERP

Based on the ERPnext analysis, UltrERP should consider implementing:

### Projects
- Task dependencies with auto-rescheduling
- Project templates with task generation
- Timesheet-based billing (costing_rate, billing_rate per activity type)
- Gross margin calculation on projects
- Progress collection via email
- Gantt chart integration
- Project Kanban boards

### HR
- Employee tree via reports_to
- Biometric attendance device ID field
- Holiday list management with weekly offs
- Department tree structure
- Employee exit/rehiring workflow (status = Left)

### Support
- SLA with working hours and holiday calendars
- First response time tracking
- Issue split functionality
- Auto-close tickets after N days
- Issue-to-task conversion
- Customer portal integration

---

## 6. SOURCE FILE REFERENCE

| File | Purpose |
|------|---------|
| `erpnext/projects/doctype/project/project.json` | Project doctype |
| `erpnext/projects/doctype/project/project.py` | Project controller |
| `erpnext/projects/doctype/task/task.json` | Task doctype |
| `erpnext/projects/doctype/task/task.py` | Task controller |
| `erpnext/projects/doctype/timesheet/timesheet.json` | Timesheet doctype |
| `erpnext/projects/doctype/activity_type/activity_type.json` | Activity type |
| `erpnext/projects/doctype/project_template/project_template.json` | Project template |
| `erpnext/support/doctype/issue/issue.json` | Issue doctype |
| `erpnext/support/doctype/issue/issue.py` | Issue controller |
| `erpnext/support/doctype/service_level_agreement/service_level_agreement.json` | SLA |
| `erpnext/support/doctype/warranty_claim/warranty_claim.json` | Warranty claim |
| `erpnext/setup/doctype/employee/employee.json` | Employee |
| `erpnext/setup/doctype/department/department.json` | Department |
| `erpnext/setup/doctype/holiday_list/holiday_list.json` | Holiday list |
| `erpnext/setup/doctype/designation/designation.json` | Designation |
| `erpnext/setup/doctype/branch/branch.json` | Branch |
