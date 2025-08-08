-- =============================================================================
-- COMPLETE DATABASE SCHEMA FOR CASE MANAGEMENT SYSTEM
-- Professional social services coordination database
-- =============================================================================

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS communication_logs;
DROP TABLE IF EXISTS case_management_tasks;
DROP TABLE IF EXISTS service_referrals;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS social_services;
DROP TABLE IF EXISTS service_providers;

-- =============================================================================
-- SERVICE PROVIDERS TABLE
-- =============================================================================
CREATE TABLE service_providers (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    organization_type TEXT, -- Government, Nonprofit, Faith-based, Private, Community-based
    
    -- Contact information
    primary_contact TEXT,
    referral_contact TEXT,
    emergency_contact TEXT,
    address TEXT,
    city TEXT,
    county TEXT,
    state TEXT DEFAULT 'CA',
    zip_code TEXT,
    
    -- Communication details
    phone_main TEXT,
    phone_referral TEXT,
    fax TEXT,
    email TEXT,
    website TEXT,
    
    -- Operational details
    hours_operation TEXT,
    appointment_types TEXT, -- Walk-in, Scheduled, Emergency
    languages_offered TEXT,
    accessibility_features TEXT,
    
    -- Professional information
    accreditation_status TEXT,
    license_number TEXT,
    accepts_medicaid INTEGER DEFAULT 1,
    sliding_scale_available INTEGER DEFAULT 0,
    
    -- Capacity and availability
    current_capacity INTEGER DEFAULT 0,
    total_capacity INTEGER DEFAULT 0,
    waitlist_length INTEGER DEFAULT 0,
    avg_wait_time_days INTEGER DEFAULT 0,
    
    -- Background check policies
    background_check_policy TEXT,
    restricted_offenses TEXT,
    case_by_case_review INTEGER DEFAULT 1,
    
    -- Service area
    service_radius_miles INTEGER DEFAULT 0,
    provides_transportation INTEGER DEFAULT 0,
    mobile_services INTEGER DEFAULT 0,
    telehealth_available INTEGER DEFAULT 0,
    
    -- Performance metrics
    success_rate REAL DEFAULT 0.0,
    completion_rate REAL DEFAULT 0.0,
    client_satisfaction REAL DEFAULT 0.0,
    referral_volume_monthly INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TEXT,
    last_updated TEXT,
    is_active INTEGER DEFAULT 1,
    notes TEXT
);

-- =============================================================================
-- SOCIAL SERVICES TABLE
-- =============================================================================
CREATE TABLE social_services (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id TEXT UNIQUE NOT NULL,
    provider_id TEXT NOT NULL,
    
    -- Service classification
    service_category TEXT NOT NULL, -- Housing, Mental Health, Medical, etc.
    service_type TEXT,              -- Specific service within category
    service_level TEXT,             -- Emergency, Ongoing, Intensive, Maintenance
    
    -- Service details
    description TEXT,
    eligibility_criteria TEXT,
    documentation_required TEXT,
    referral_process TEXT,
    intake_requirements TEXT,
    
    -- Restrictions and requirements
    age_restrictions TEXT,
    gender_restrictions TEXT,
    sobriety_required INTEGER DEFAULT 0,
    insurance_required INTEGER DEFAULT 0,
    residency_required INTEGER DEFAULT 0,
    
    -- Special populations served
    serves_veterans INTEGER DEFAULT 0,
    serves_disabled INTEGER DEFAULT 0,
    serves_pregnant_women INTEGER DEFAULT 0,
    serves_lgbtq INTEGER DEFAULT 0,
    serves_trafficking_survivors INTEGER DEFAULT 0,
    
    -- Cost and payment
    cost_structure TEXT,
    insurance_accepted TEXT,
    sliding_scale_fees INTEGER DEFAULT 0,
    free_services INTEGER DEFAULT 0,
    
    -- Availability
    current_availability TEXT, -- Accepting, Waitlist, Closed
    waitlist_status TEXT,
    estimated_wait_time TEXT,
    
    -- Performance metrics
    success_rate REAL DEFAULT 0.0,
    completion_rate REAL DEFAULT 0.0,
    avg_service_duration TEXT,
    
    -- Metadata
    created_at TEXT,
    last_updated TEXT,
    is_active INTEGER DEFAULT 1,
    
    -- Foreign key constraint
    FOREIGN KEY (provider_id) REFERENCES service_providers (provider_id)
);

-- =============================================================================
-- CLIENTS TABLE
-- =============================================================================
CREATE TABLE clients (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT UNIQUE NOT NULL,
    case_manager_id TEXT,
    
    -- Personal information
    first_name TEXT,
    last_name TEXT,
    date_of_birth TEXT,
    gender TEXT,
    primary_phone TEXT,
    email TEXT,
    
    -- Address information
    address TEXT,
    city TEXT,
    county TEXT,
    zip_code TEXT,
    
    -- Emergency contact
    emergency_contact TEXT,
    emergency_phone TEXT,
    
    -- Demographics and special populations
    is_veteran INTEGER DEFAULT 0,
    has_disability INTEGER DEFAULT 0,
    special_populations TEXT, -- JSON string
    
    -- Background and status
    background_summary TEXT,
    sobriety_status TEXT,
    insurance_status TEXT,
    housing_status TEXT,
    employment_status TEXT,
    
    -- Service planning
    service_priorities TEXT, -- JSON string
    risk_level TEXT DEFAULT 'Medium', -- Low, Medium, High
    discharge_date TEXT,
    
    -- Metadata
    created_at TEXT,
    last_updated TEXT,
    is_active INTEGER DEFAULT 1,
    notes TEXT
);

-- =============================================================================
-- SERVICE REFERRALS TABLE
-- =============================================================================
CREATE TABLE service_referrals (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referral_id TEXT UNIQUE NOT NULL,
    client_id TEXT NOT NULL,
    case_manager_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    service_id TEXT NOT NULL,
    
    -- Referral details
    referral_date TEXT,
    priority_level TEXT DEFAULT 'Medium', -- Low, Medium, High, Urgent
    status TEXT DEFAULT 'Pending',        -- Pending, Submitted, Accepted, Active, Completed, Cancelled
    urgency TEXT DEFAULT 'Standard',      -- Standard, Urgent, Emergency
    
    -- Timeline
    expected_start_date TEXT,
    actual_start_date TEXT,
    expected_completion_date TEXT,
    completion_date TEXT,
    
    -- Follow-up and communication
    last_contact_date TEXT,
    next_follow_up_date TEXT,
    provider_response TEXT,
    
    -- Documentation
    referral_reason TEXT,
    notes TEXT,
    barriers_encountered TEXT,
    resolution_notes TEXT,
    
    -- Outcome tracking
    outcome TEXT,              -- Successful, Unsuccessful, Transferred, Dropped
    satisfaction_rating INTEGER DEFAULT 0, -- 1-5 scale
    client_feedback TEXT,
    
    -- Metadata
    created_at TEXT,
    last_updated TEXT,
    created_by TEXT,
    last_updated_by TEXT,
    
    -- Foreign key constraints
    FOREIGN KEY (client_id) REFERENCES clients (client_id),
    FOREIGN KEY (provider_id) REFERENCES service_providers (provider_id),
    FOREIGN KEY (service_id) REFERENCES social_services (service_id)
);

-- =============================================================================
-- CASE MANAGEMENT TASKS TABLE
-- =============================================================================
CREATE TABLE case_management_tasks (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    case_manager_id TEXT NOT NULL,
    client_id TEXT,
    referral_id TEXT,
    
    -- Task details
    task_type TEXT,    -- General, Follow-up, Documentation, Contact, Assessment
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'Medium', -- Low, Medium, High, Urgent
    
    -- Timeline
    due_date TEXT,
    reminder_date TEXT,
    status TEXT DEFAULT 'Pending', -- Pending, In Progress, Completed, Cancelled, Overdue
    
    -- Assignment
    assigned_to TEXT,
    assigned_by TEXT,
    
    -- Completion
    completed_date TEXT,
    completion_notes TEXT,
    time_spent_minutes INTEGER DEFAULT 0,
    
    -- Automation
    is_automated INTEGER DEFAULT 0,
    recurring_interval TEXT, -- None, Daily, Weekly, Monthly
    parent_task_id TEXT,
    
    -- Metadata
    created_at TEXT,
    last_updated TEXT,
    created_by TEXT,
    last_updated_by TEXT
);

-- =============================================================================
-- COMMUNICATION LOGS TABLE
-- =============================================================================
CREATE TABLE communication_logs (
    -- Primary identification
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    communication_id TEXT UNIQUE NOT NULL,
    case_manager_id TEXT NOT NULL,
    provider_id TEXT,
    client_id TEXT,
    referral_id TEXT,
    
    -- Communication details
    communication_type TEXT DEFAULT 'Email', -- Email, Phone, In-Person, Secure Message
    direction TEXT DEFAULT 'Outbound',       -- Outbound, Inbound
    subject TEXT,
    content TEXT,
    priority TEXT DEFAULT 'Normal', -- Low, Normal, High, Urgent
    
    -- Participants
    to_contacts TEXT,   -- JSON string of contact list
    cc_contacts TEXT,
    from_contact TEXT,
    
    -- Status and tracking
    status TEXT DEFAULT 'Sent', -- Draft, Sent, Delivered, Read, Replied
    read_date TEXT,
    reply_date TEXT,
    follow_up_required INTEGER DEFAULT 0,
    follow_up_date TEXT,
    
    -- Attachments and references
    attachments TEXT,          -- JSON string of attachment list
    related_documents TEXT,
    tags TEXT,                 -- JSON string of tags
    
    -- Metadata
    created_at TEXT,
    created_by TEXT,
    is_confidential INTEGER DEFAULT 1,
    is_archived INTEGER DEFAULT 0
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Service provider indexes
CREATE INDEX idx_providers_county ON service_providers(county);
CREATE INDEX idx_providers_org_type ON service_providers(organization_type);
CREATE INDEX idx_providers_active ON service_providers(is_active);
CREATE INDEX idx_providers_capacity ON service_providers(current_capacity, total_capacity);

-- Social services indexes
CREATE INDEX idx_services_category ON social_services(service_category);
CREATE INDEX idx_services_provider ON social_services(provider_id);
CREATE INDEX idx_services_availability ON social_services(current_availability);
CREATE INDEX idx_services_active ON social_services(is_active);

-- Client indexes
CREATE INDEX idx_clients_case_manager ON clients(case_manager_id);
CREATE INDEX idx_clients_risk_level ON clients(risk_level);
CREATE INDEX idx_clients_housing_status ON clients(housing_status);
CREATE INDEX idx_clients_active ON clients(is_active);
CREATE INDEX idx_clients_name ON clients(first_name, last_name);

-- Referral indexes
CREATE INDEX idx_referrals_client ON service_referrals(client_id);
CREATE INDEX idx_referrals_case_manager ON service_referrals(case_manager_id);
CREATE INDEX idx_referrals_provider ON service_referrals(provider_id);
CREATE INDEX idx_referrals_status ON service_referrals(status);
CREATE INDEX idx_referrals_priority ON service_referrals(priority_level);
CREATE INDEX idx_referrals_date ON service_referrals(referral_date);
CREATE INDEX idx_referrals_follow_up ON service_referrals(next_follow_up_date);

-- Task indexes
CREATE INDEX idx_tasks_case_manager ON case_management_tasks(case_manager_id);
CREATE INDEX idx_tasks_client ON case_management_tasks(client_id);
CREATE INDEX idx_tasks_status ON case_management_tasks(status);
CREATE INDEX idx_tasks_priority ON case_management_tasks(priority);
CREATE INDEX idx_tasks_due_date ON case_management_tasks(due_date);
CREATE INDEX idx_tasks_type ON case_management_tasks(task_type);

-- Communication indexes
CREATE INDEX idx_comm_case_manager ON communication_logs(case_manager_id);
CREATE INDEX idx_comm_provider ON communication_logs(provider_id);
CREATE INDEX idx_comm_client ON communication_logs(client_id);
CREATE INDEX idx_comm_type ON communication_logs(communication_type);
CREATE INDEX idx_comm_date ON communication_logs(created_at);

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Comprehensive client view with summary statistics
CREATE VIEW client_summary AS
SELECT 
    c.*,
    COUNT(r.referral_id) as total_referrals,
    SUM(CASE WHEN r.status IN ('Pending', 'Active') THEN 1 ELSE 0 END) as active_referrals,
    SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
    COUNT(t.task_id) as total_tasks,
    SUM(CASE WHEN t.status = 'Pending' THEN 1 ELSE 0 END) as pending_tasks,
    MAX(r.last_contact_date) as last_contact_date,
    MIN(r.next_follow_up_date) as next_follow_up_date
FROM clients c
LEFT JOIN service_referrals r ON c.client_id = r.client_id
LEFT JOIN case_management_tasks t ON c.client_id = t.client_id
WHERE c.is_active = 1
GROUP BY c.client_id;

-- Provider performance view
CREATE VIEW provider_performance AS
SELECT 
    p.*,
    COUNT(r.referral_id) as total_referrals,
    SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
    SUM(CASE WHEN r.status = 'Active' THEN 1 ELSE 0 END) as active_referrals,
    SUM(CASE WHEN r.status = 'Pending' THEN 1 ELSE 0 END) as pending_referrals,
    AVG(r.satisfaction_rating) as avg_satisfaction,
    COUNT(DISTINCT r.client_id) as unique_clients_served,
    AVG(julianday(r.completion_date) - julianday(r.referral_date)) as avg_completion_days
FROM service_providers p
LEFT JOIN service_referrals r ON p.provider_id = r.provider_id
WHERE p.is_active = 1
GROUP BY p.provider_id;

-- Task dashboard view
CREATE VIEW task_dashboard AS
SELECT 
    t.*,
    c.first_name || ' ' || c.last_name as client_name,
    c.risk_level as client_risk_level,
    r.status as referral_status,
    p.name as provider_name,
    julianday(t.due_date) - julianday('now') as days_until_due,
    CASE 
        WHEN t.status = 'Completed' THEN 0
        WHEN t.due_date < datetime('now') THEN 1 
        ELSE 0 
    END as is_overdue
FROM case_management_tasks t
LEFT JOIN clients c ON t.client_id = c.client_id
LEFT JOIN service_referrals r ON t.referral_id = r.referral_id
LEFT JOIN service_providers p ON r.provider_id = p.provider_id;

-- =============================================================================
-- SAMPLE DATA INSERTION
-- =============================================================================

-- Insert sample service categories for reference
INSERT INTO service_providers (
    provider_id, name, organization_type, city, county, state, phone_main, email,
    background_check_policy, case_by_case_review, accepts_medicaid, created_at, last_updated
) VALUES 
('sample_provider_001', 'Sample Community Services', 'Nonprofit', 'Los Angeles', 'Los Angeles', 'CA',
 '(555) 123-4567', 'info@sampleservices.org', 'Background-friendly with case review', 1, 1,
 datetime('now'), datetime('now'));

INSERT INTO social_services (
    service_id, provider_id, service_category, service_type, service_level, description,
    current_availability, created_at, last_updated, is_active
) VALUES
('sample_service_001', 'sample_provider_001', 'Housing Services', 'Emergency Shelter', 'Emergency',
 'Temporary emergency housing for individuals and families', 'Accepting', datetime('now'), datetime('now'), 1);

-- Insert sample case manager and client
INSERT INTO clients (
    client_id, case_manager_id, first_name, last_name, gender, housing_status, employment_status,
    risk_level, created_at, last_updated, is_active
) VALUES
('sample_client_001', 'sample_cm_001', 'John', 'Doe', 'Male', 'Homeless', 'Unemployed',
 'High', datetime('now'), datetime('now'), 1);

-- =============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- =============================================================================

-- Update last_updated timestamp on client changes
CREATE TRIGGER update_client_timestamp 
AFTER UPDATE ON clients
BEGIN
    UPDATE clients SET last_updated = datetime('now') WHERE client_id = NEW.client_id;
END;

-- Update last_updated timestamp on referral changes
CREATE TRIGGER update_referral_timestamp 
AFTER UPDATE ON service_referrals
BEGIN
    UPDATE service_referrals SET last_updated = datetime('now') WHERE referral_id = NEW.referral_id;
END;

-- Update last_updated timestamp on task changes
CREATE TRIGGER update_task_timestamp 
AFTER UPDATE ON case_management_tasks
BEGIN
    UPDATE case_management_tasks SET last_updated = datetime('now') WHERE task_id = NEW.task_id;
END;

-- Automatically create follow-up task when high-priority referral is created
CREATE TRIGGER create_follow_up_task
AFTER INSERT ON service_referrals
WHEN NEW.priority_level IN ('High', 'Urgent')
BEGIN
    INSERT INTO case_management_tasks (
        task_id, case_manager_id, client_id, referral_id, task_type, title, description,
        priority, due_date, status, is_automated, created_at, last_updated, created_by
    ) VALUES (
        'auto_' || hex(randomblob(8)),
        NEW.case_manager_id,
        NEW.client_id,
        NEW.referral_id,
        'Follow-up',
        'Follow up on high-priority referral',
        'Check status of high-priority referral within 24 hours',
        'High',
        datetime('now', '+1 day'),
        'Pending',
        1,
        datetime('now'),
        datetime('now'),
        'system'
    );
END;

-- =============================================================================
-- STORED PROCEDURES (SQLite User-Defined Functions)
-- =============================================================================

-- Note: SQLite doesn't support stored procedures, but these would be implemented
-- in the Python application layer. Here are the function signatures for reference:

/*
-- Calculate client risk score based on multiple factors
FUNCTION calculate_risk_score(client_id TEXT) RETURNS INTEGER

-- Get case manager workload statistics
FUNCTION get_case_manager_workload(case_manager_id TEXT) RETURNS JSON

-- Find best matching providers for client needs
FUNCTION find_matching_providers(client_id TEXT, service_category TEXT) RETURNS JSON

-- Generate automated follow-up schedule
FUNCTION create_follow_up_schedule(referral_id TEXT) RETURNS JSON

-- Calculate provider performance metrics
FUNCTION calculate_provider_metrics(provider_id TEXT, period_days INTEGER) RETURNS JSON
*/

-- =============================================================================
-- DATABASE MAINTENANCE COMMANDS
-- =============================================================================

-- Vacuum database to reclaim space and optimize performance
-- VACUUM;

-- Analyze tables to update query planner statistics
-- ANALYZE;

-- Check database integrity
-- PRAGMA integrity_check;

-- =============================================================================
-- BACKUP AND RECOVERY PROCEDURES
-- =============================================================================

/*
-- Daily backup command (to be run via cron job)
-- sqlite3 social_services.db ".backup backup_$(date +%Y%m%d).db"

-- Point-in-time recovery setup
-- Enable WAL mode for better concurrency and backup
-- PRAGMA journal_mode=WAL;

-- Restore from backup
-- sqlite3 social_services.db ".restore backup_YYYYMMDD.db"
*/