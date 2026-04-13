## Epic 3: Customer Management

### Epic Goal

Sales reps can search, create, and update customers with validated Taiwan business numbers (統一編號) and scalable lookup workflows.

### Stories

### Story 3.2: Validate Taiwan Business Number Checksum

As a system,
I want to validate Taiwan business numbers using the current Ministry of Finance checksum logic,
So that customer data stays compliant for both legacy and newly issued numbers.

**Acceptance Criteria:**

**Given** I'm creating or updating a customer
**When** I enter an 8-digit Taiwan business number
**Then** the system validates it using the weighted checksum algorithm defined by current Ministry of Finance guidance, including the special-case handling for the seventh digit
**And** the validation accepts legacy and expanded allocations permitted by the official rule
**If** the checksum or format is invalid
**Then** the system shows a clear validation error and prevents save
**And** the validation logic is reusable from both the UI and backend tests

### Story 3.3: Create Customer Record

As a sales rep,
I want to create a new customer with business number, address, contact, and credit limit,
So that I can add new B2B customers to the system without re-entering them in later flows.

**Acceptance Criteria:**

**Given** I'm creating a new customer
**When** I fill in company name, Taiwan business number validated by Story 3.2, billing address, primary contact name, contact phone, contact email, and credit limit
**Then** the customer is saved to the database
**And** tenant_id is set correctly
**And** I receive confirmation with customer ID

### Story 3.1: Search and Browse Customers

As a sales rep,
I want to search for existing customers by 統一編號 or company name and inspect the matching record,
So that I can reuse existing customer data before creating invoices or orders.

**Acceptance Criteria:**

**Given** customers exist in the system
**When** I search by 統一編號 (full or partial) or company name (full or partial)
**Then** matching customers are returned with the summary fields needed to identify the right customer
**And** I can open a selected result to view the full customer record by ID or tax ID
**And** the results experience supports pagination and/or virtualization for 5,000+ rows without visible stutter on target hardware
**And** indexed search results load in < 500ms for expected SMB datasets

### Story 3.4: Flag Duplicate Business Number

As a system,
I want to flag duplicate Taiwan business numbers during customer creation,
So that we don't create conflicting customer masters.

**Acceptance Criteria:**

**Given** a customer with the same Taiwan business number already exists
**When** I attempt to create a new customer with that business number
**Then** the system shows a clear duplicate warning that includes the existing customer name
**And** the normal create flow is blocked until I cancel or choose the existing record instead
**And** the duplicate check occurs before the database insert and is also enforced by a unique persistence constraint

### Story 3.5: Update Customer Record

As a sales rep,
I want to update an existing customer's master data,
So that contact details, address, credit limit, and business number corrections stay accurate over time.

**Acceptance Criteria:**

**Given** an existing customer record
**When** I update company name, Taiwan business number, address, contact details, or credit limit
**Then** the system validates the edited fields before save
**And** changes to the business number re-run Story 3.2 checksum validation and duplicate detection
**And** the updated record is persisted without changing the customer ID
**And** the updated customer can be retrieved immediately through the customer detail and search flows

---

