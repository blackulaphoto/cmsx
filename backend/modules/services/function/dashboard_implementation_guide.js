// Case Management Dashboard - Implementation Guide
// Professional case management system with ClickUp-inspired workflow

// =============================================================================
// 1. GLOBAL STATE MANAGEMENT (Modern JavaScript with Real-time Updates)
// =============================================================================

class CaseManagementState {
    constructor() {
        this.state = {
            currentUser: {
                case_manager_id: 'default_cm',
                name: 'Case Manager',
                permissions: ['read', 'write', 'admin']
            },
            dashboard: {
                stats: {},
                recent_activity: [],
                last_updated: null
            },
            clients: {
                list: [],
                selected: null,
                filters: {},
                loading: false
            },
            referrals: {
                list: [],
                selected: null,
                filters: { status: 'all' },
                loading: false
            },
            tasks: {
                list: [],
                selected: null,
                filters: { status: 'pending' },
                loading: false
            },
            providers: {
                list: [],
                selected: null,
                search_results: [],
                loading: false
            },
            ui: {
                active_section: 'dashboard',
                modals: {},
                notifications: [],
                sidebar_collapsed: false
            }
        };
        
        this.subscribers = new Map();
        this.websocket = null;
        this.init();
    }
    
    // State management methods
    subscribe(component, callback) {
        if (!this.subscribers.has(component)) {
            this.subscribers.set(component, []);
        }
        this.subscribers.get(component).push(callback);
    }
    
    setState(path, value) {
        const keys = path.split('.');
        let current = this.state;
        
        for (let i = 0; i < keys.length - 1; i++) {
            current = current[keys[i]];
        }
        
        current[keys[keys.length - 1]] = value;
        this.notifySubscribers(keys[0]);
    }
    
    getState(path = null) {
        if (!path) return this.state;
        
        const keys = path.split('.');
        let current = this.state;
        
        for (const key of keys) {
            current = current[key];
            if (current === undefined) return null;
        }
        
        return current;
    }
    
    notifySubscribers(component) {
        if (this.subscribers.has(component)) {
            this.subscribers.get(component).forEach(callback => {
                callback(this.state[component]);
            });
        }
    }
    
    // WebSocket initialization for real-time updates
    init() {
        this.connectWebSocket();
        this.loadInitialData();
    }
    
    connectWebSocket() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/ws/case_management/${this.state.currentUser.case_manager_id}`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleRealtimeUpdate(data);
        };
        
        this.websocket.onclose = () => {
            // Reconnect after 5 seconds
            setTimeout(() => this.connectWebSocket(), 5000);
        };
    }
    
    handleRealtimeUpdate(data) {
        switch (data.type) {
            case 'client_updated':
                this.updateClientInList(data.client);
                break;
            case 'referral_status_changed':
                this.updateReferralInList(data.referral);
                break;
            case 'task_created':
                this.addTaskToList(data.task);
                break;
            case 'dashboard_stats':
                this.setState('dashboard.stats', data.stats);
                break;
        }
    }
    
    async loadInitialData() {
        await Promise.all([
            this.loadDashboardData(),
            this.loadClients(),
            this.loadReferrals(),
            this.loadTasks()
        ]);
    }
}

// Global state instance
const appState = new CaseManagementState();

// =============================================================================
// 2. DASHBOARD OVERVIEW COMPONENT
// =============================================================================

class DashboardOverview {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.init();
    }
    
    init() {
        appState.subscribe('dashboard', (data) => this.render(data));
        this.setupEventListeners();
    }
    
    async loadDashboardData() {
        appState.setState('dashboard.loading', true);
        
        try {
            const response = await fetch(`/api/dashboard/${appState.getState('currentUser.case_manager_id')}`);
            const data = await response.json();
            
            if (data.success) {
                appState.setState('dashboard.stats', data.dashboard);
                appState.setState('dashboard.last_updated', new Date().toISOString());
            }
        } catch (error) {
            this.showError('Failed to load dashboard data');
        } finally {
            appState.setState('dashboard.loading', false);
        }
    }
    
    render(data) {
        if (!data.stats) return;
        
        this.container.innerHTML = `
            <div class="dashboard-grid">
                <!-- Key Metrics Cards -->
                <div class="metrics-row">
                    ${this.renderMetricCard('Total Clients', data.stats.client_stats?.total_clients || 0, 'users', 'primary')}
                    ${this.renderMetricCard('High Risk', data.stats.client_stats?.high_risk_clients || 0, 'exclamation-triangle', 'danger')}
                    ${this.renderMetricCard('Pending Referrals', data.stats.referral_stats?.pending_referrals || 0, 'clock', 'warning')}
                    ${this.renderMetricCard('Overdue Tasks', data.stats.task_stats?.overdue_tasks || 0, 'calendar-times', 'danger')}
                </div>
                
                <!-- Quick Actions Bar -->
                <div class="quick-actions">
                    <button class="btn btn-primary btn-lg" onclick="dashboardController.quickReferral()">
                        <i class="fas fa-plus-circle me-2"></i>Quick Referral
                    </button>
                    <button class="btn btn-success btn-lg" onclick="dashboardController.addClient()">
                        <i class="fas fa-user-plus me-2"></i>Add Client
                    </button>
                    <button class="btn btn-info btn-lg" onclick="dashboardController.emergencyResources()">
                        <i class="fas fa-ambulance me-2"></i>Emergency Resources
                    </button>
                    <button class="btn btn-secondary btn-lg" onclick="dashboardController.generateReport()">
                        <i class="fas fa-chart-bar me-2"></i>Generate Report
                    </button>
                </div>
                
                <!-- Activity Feed -->
                <div class="activity-section">
                    <h5 class="mb-3">Recent Activity</h5>
                    <div class="activity-feed">
                        ${this.renderActivityFeed(data.recent_activity || [])}
                    </div>
                </div>
                
                <!-- Performance Charts -->
                <div class="charts-section">
                    <div class="row">
                        <div class="col-md-6">
                            <canvas id="referralChart"></canvas>
                        </div>
                        <div class="col-md-6">
                            <canvas id="taskChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.initializeCharts(data.stats);
    }
    
    renderMetricCard(title, value, icon, color) {
        return `
            <div class="metric-card card border-${color}">
                <div class="card-body">
                    <div class="d-flex align-items-center">
                        <div class="metric-icon text-${color}">
                            <i class="fas fa-${icon} fa-2x"></i>
                        </div>
                        <div class="metric-content ms-3">
                            <h3 class="metric-value text-${color}">${value}</h3>
                            <p class="metric-label mb-0">${title}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderActivityFeed(activities) {
        if (!activities.length) {
            return '<p class="text-muted">No recent activity</p>';
        }
        
        return activities.map(activity => `
            <div class="activity-item" onclick="dashboardController.viewActivity('${activity.id}')">
                <div class="activity-icon">
                    <i class="fas fa-${this.getActivityIcon(activity.activity_type)}"></i>
                </div>
                <div class="activity-content">
                    <p class="activity-text">${activity.description}</p>
                    <small class="activity-time text-muted">${this.formatTime(activity.timestamp)}</small>
                </div>
                ${activity.action_required ? '<div class="activity-badge badge bg-warning">Action Required</div>' : ''}
            </div>
        `).join('');
    }
    
    setupEventListeners() {
        // Auto-refresh dashboard every 30 seconds
        setInterval(() => {
            this.loadDashboardData();
        }, 30000);
        
        // Handle quick actions
        window.dashboardController = {
            quickReferral: () => this.openQuickReferralModal(),
            addClient: () => this.openAddClientModal(), 
            emergencyResources: () => this.showEmergencyResources(),
            generateReport: () => this.generateReport(),
            viewActivity: (id) => this.viewActivityDetail(id)
        };
    }
}

// =============================================================================
// 3. CASELOAD MANAGEMENT COMPONENT
// =============================================================================

class CaseloadManagement {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentFilters = {};
        this.init();
    }
    
    init() {
        appState.subscribe('clients', (data) => this.render(data));
        this.loadClients();
    }
    
    async loadClients(filters = {}) {
        appState.setState('clients.loading', true);
        
        try {
            const queryParams = new URLSearchParams({
                case_manager_id: appState.getState('currentUser.case_manager_id'),
                ...filters
            });
            
            const response = await fetch(`/api/clients?${queryParams}`);
            const data = await response.json();
            
            if (data.success) {
                appState.setState('clients.list', data.clients);
                appState.setState('clients.filters', filters);
            }
        } catch (error) {
            this.showError('Failed to load clients');
        } finally {
            appState.setState('clients.loading', false);
        }
    }
    
    render(data) {
        this.container.innerHTML = `
            <div class="caseload-header d-flex justify-content-between align-items-center mb-4">
                <h4 class="mb-0">Client Caseload Management</h4>
                <div class="caseload-actions">
                    ${this.renderFilters()}
                    <button class="btn btn-primary ms-2" onclick="caseloadController.addClient()">
                        <i class="fas fa-plus me-1"></i>Add Client
                    </button>
                </div>
            </div>
            
            ${data.loading ? this.renderLoading() : this.renderClientTable(data.list)}
        `;
        
        this.setupEventListeners();
    }
    
    renderFilters() {
        return `
            <div class="filter-group d-flex gap-2">
                <select class="form-select form-select-sm" id="riskFilter" onchange="caseloadController.applyFilter('risk_level', this.value)">
                    <option value="">All Risk Levels</option>
                    <option value="Low">Low Risk</option>
                    <option value="Medium">Medium Risk</option>
                    <option value="High">High Risk</option>
                </select>
                
                <select class="form-select form-select-sm" id="housingFilter" onchange="caseloadController.applyFilter('housing_status', this.value)">
                    <option value="">All Housing Status</option>
                    <option value="Stable">Stable</option>
                    <option value="Transitional">Transitional</option>
                    <option value="Homeless">Homeless</option>
                </select>
                
                <input type="text" class="form-control form-control-sm" placeholder="Search clients..." 
                       onkeyup="caseloadController.searchClients(this.value)">
            </div>
        `;
    }
    
    renderClientTable(clients) {
        if (!clients || clients.length === 0) {
            return '<div class="text-center py-5"><p class="text-muted">No clients found</p></div>';
        }
        
        return `
            <div class="table-responsive">
                <table class="table table-hover client-table">
                    <thead class="table-dark">
                        <tr>
                            <th>Client Name</th>
                            <th>Age</th>
                            <th>Risk Level</th>
                            <th>Housing Status</th>
                            <th>Employment Status</th>
                            <th>Active Referrals</th>
                            <th>Last Contact</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${clients.map(client => this.renderClientRow(client)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    renderClientRow(client) {
        const riskBadgeClass = {
            'Low': 'success',
            'Medium': 'warning', 
            'High': 'danger'
        };
        
        return `
            <tr class="client-row" data-client-id="${client.client_id}" onclick="caseloadController.viewClient('${client.client_id}')">
                <td>
                    <div class="client-name">
                        <strong>${client.first_name} ${client.last_name}</strong>
                        <br><small class="text-muted">ID: ${client.client_id}</small>
                    </div>
                </td>
                <td>${client.age || 'N/A'}</td>
                <td>
                    <span class="badge bg-${riskBadgeClass[client.risk_level] || 'secondary'}">
                        ${client.risk_level}
                    </span>
                </td>
                <td>${client.housing_status}</td>
                <td>${client.employment_status}</td>
                <td>
                    <span class="badge bg-primary">${client.active_referrals || 0}</span>
                    <span class="text-muted">/ ${client.completed_referrals || 0} completed</span>
                </td>
                <td>${this.formatDate(client.last_contact_date)}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); caseloadController.viewClient('${client.client_id}')" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation(); caseloadController.createReferral('${client.client_id}')" 
                                title="Create Referral">
                            <i class="fas fa-plus"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); caseloadController.editClient('${client.client_id}')" 
                                title="Edit Client">
                            <i class="fas fa-edit"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    setupEventListeners() {
        window.caseloadController = {
            addClient: () => this.openAddClientModal(),
            viewClient: (clientId) => this.openClientDetailModal(clientId),
            editClient: (clientId) => this.openEditClientModal(clientId),
            createReferral: (clientId) => this.openCreateReferralModal(clientId),
            applyFilter: (filterType, value) => this.applyFilter(filterType, value),
            searchClients: (searchTerm) => this.searchClients(searchTerm)
        };
    }
}

// =============================================================================
// 4. REFERRAL TRACKING COMPONENT
// =============================================================================

class ReferralTracking {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentFilters = { status: 'all' };
        this.init();
    }
    
    init() {
        appState.subscribe('referrals', (data) => this.render(data));
        this.loadReferrals();
    }
    
    async loadReferrals(filters = {}) {
        appState.setState('referrals.loading', true);
        
        try {
            const queryParams = new URLSearchParams({
                case_manager_id: appState.getState('currentUser.case_manager_id'),
                ...filters
            });
            
            const response = await fetch(`/api/referrals?${queryParams}`);
            const data = await response.json();
            
            if (data.success) {
                appState.setState('referrals.list', data.referrals);
                appState.setState('referrals.filters', filters);
            }
        } catch (error) {
            this.showError('Failed to load referrals');
        } finally {
            appState.setState('referrals.loading', false);
        }
    }
    
    render(data) {
        this.container.innerHTML = `
            <div class="referral-header d-flex justify-content-between align-items-center mb-4">
                <h4 class="mb-0">Referral Tracking</h4>
                <div class="referral-filters">
                    ${this.renderStatusFilter()}
                </div>
            </div>
            
            ${data.loading ? this.renderLoading() : this.renderReferralTable(data.list)}
        `;
        
        this.setupEventListeners();
    }
    
    renderStatusFilter() {
        return `
            <div class="btn-group" role="group">
                <button class="btn btn-outline-secondary ${this.currentFilters.status === 'all' ? 'active' : ''}" 
                        onclick="referralController.filterByStatus('all')">All</button>
                <button class="btn btn-outline-warning ${this.currentFilters.status === 'pending' ? 'active' : ''}" 
                        onclick="referralController.filterByStatus('pending')">Pending</button>
                <button class="btn btn-outline-info ${this.currentFilters.status === 'active' ? 'active' : ''}" 
                        onclick="referralController.filterByStatus('active')">Active</button>
                <button class="btn btn-outline-success ${this.currentFilters.status === 'completed' ? 'active' : ''}" 
                        onclick="referralController.filterByStatus('completed')">Completed</button>
            </div>
        `;
    }
    
    renderReferralTable(referrals) {
        if (!referrals || referrals.length === 0) {
            return '<div class="text-center py-5"><p class="text-muted">No referrals found</p></div>';
        }
        
        return `
            <div class="table-responsive">
                <table class="table table-hover referral-table">
                    <thead class="table-dark">
                        <tr>
                            <th>Client</th>
                            <th>Provider</th>
                            <th>Service Type</th>
                            <th>Status</th>
                            <th>Priority</th>
                            <th>Days Since Referral</th>
                            <th>Next Follow-up</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${referrals.map(referral => this.renderReferralRow(referral)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    renderReferralRow(referral) {
        const statusBadgeClass = {
            'Pending': 'warning',
            'Active': 'primary',
            'Completed': 'success',
            'Cancelled': 'secondary'
        };
        
        const priorityBadgeClass = {
            'Low': 'success',
            'Medium': 'warning',
            'High': 'danger',
            'Urgent': 'danger'
        };
        
        return `
            <tr class="referral-row" data-referral-id="${referral.referral_id}" onclick="referralController.viewReferral('${referral.referral_id}')">
                <td>
                    <div class="client-info">
                        <strong>${referral.client_name}</strong>
                    </div>
                </td>
                <td>
                    <div class="provider-info">
                        ${referral.provider_name}
                    </div>
                </td>
                <td>${referral.service_type}</td>
                <td>
                    <span class="badge bg-${statusBadgeClass[referral.status] || 'secondary'}">
                        ${referral.status}
                    </span>
                </td>
                <td>
                    <span class="badge bg-${priorityBadgeClass[referral.priority_level] || 'secondary'}">
                        ${referral.priority_level}
                    </span>
                </td>
                <td>
                    <span class="${referral.days_since_referral > 7 ? 'text-danger' : ''}">${referral.days_since_referral} days</span>
                </td>
                <td>${this.formatDate(referral.next_follow_up)}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); referralController.viewReferral('${referral.referral_id}')" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation(); referralController.updateStatus('${referral.referral_id}')" 
                                title="Update Status">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); referralController.contactProvider('${referral.referral_id}')" 
                                title="Contact Provider">
                            <i class="fas fa-phone"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    setupEventListeners() {
        window.referralController = {
            filterByStatus: (status) => this.filterByStatus(status),
            viewReferral: (referralId) => this.openReferralDetailModal(referralId),
            updateStatus: (referralId) => this.openUpdateStatusModal(referralId),
            contactProvider: (referralId) => this.openContactProviderModal(referralId)
        };
    }
}

// =============================================================================
// 5. TASK MANAGEMENT COMPONENT
// =============================================================================

class TaskManagement {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentFilters = { status: 'pending' };
        this.init();
    }
    
    init() {
        appState.subscribe('tasks', (data) => this.render(data));
        this.loadTasks();
    }
    
    async loadTasks(filters = {}) {
        appState.setState('tasks.loading', true);
        
        try {
            const queryParams = new URLSearchParams({
                case_manager_id: appState.getState('currentUser.case_manager_id'),
                ...filters
            });
            
            const response = await fetch(`/api/tasks?${queryParams}`);
            const data = await response.json();
            
            if (data.success) {
                appState.setState('tasks.list', data.tasks);
                appState.setState('tasks.filters', filters);
            }
        } catch (error) {
            this.showError('Failed to load tasks');
        } finally {
            appState.setState('tasks.loading', false);
        }
    }
    
    render(data) {
        this.container.innerHTML = `
            <div class="task-header d-flex justify-content-between align-items-center mb-4">
                <h4 class="mb-0">Task Management</h4>
                <div class="task-actions">
                    ${this.renderTaskFilters()}
                    <button class="btn btn-primary ms-2" onclick="taskController.addTask()">
                        <i class="fas fa-plus me-1"></i>Add Task
                    </button>
                </div>
            </div>
            
            ${data.loading ? this.renderLoading() : this.renderTaskTable(data.list)}
        `;
        
        this.setupEventListeners();
    }
    
    renderTaskTable(tasks) {
        if (!tasks || tasks.length === 0) {
            return '<div class="text-center py-5"><p class="text-muted">No tasks found</p></div>';
        }
        
        return `
            <div class="table-responsive">
                <table class="table table-hover task-table">
                    <thead class="table-dark">
                        <tr>
                            <th>Task</th>
                            <th>Client</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Due Date</th>
                            <th>Type</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tasks.map(task => this.renderTaskRow(task)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    renderTaskRow(task) {
        const priorityBadgeClass = {
            'Low': 'success',
            'Medium': 'warning',
            'High': 'danger',
            'Urgent': 'danger'
        };
        
        const statusBadgeClass = {
            'Pending': 'warning',
            'In Progress': 'info',
            'Completed': 'success',
            'Overdue': 'danger'
        };
        
        const typeBadgeClass = {
            'Follow-up': 'primary',
            'Assessment': 'info',
            'Documentation': 'secondary',
            'Contact': 'success'
        };
        
        return `
            <tr class="task-row" data-task-id="${task.task_id}" onclick="taskController.viewTask('${task.task_id}')">
                <td>
                    <div class="task-info">
                        <strong>${task.title}</strong>
                        <br><small class="text-muted">${task.description}</small>
                    </div>
                </td>
                <td>${task.client_name}</td>
                <td>
                    <span class="badge bg-${priorityBadgeClass[task.priority] || 'secondary'}">
                        ${task.priority}
                    </span>
                </td>
                <td>
                    <span class="badge bg-${statusBadgeClass[task.status] || 'secondary'}">
                        ${task.status}
                    </span>
                </td>
                <td>
                    <span class="${task.days_until_due < 0 ? 'text-danger' : task.days_until_due <= 1 ? 'text-warning' : ''}">
                        ${this.formatDate(task.due_date)}
                    </span>
                </td>
                <td>
                    <span class="badge bg-${typeBadgeClass[task.task_type] || 'secondary'}">
                        ${task.task_type}
                    </span>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation(); taskController.completeTask('${task.task_id}')" 
                                title="Complete Task">
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); taskController.viewTask('${task.task_id}')" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); taskController.editTask('${task.task_id}')" 
                                title="Edit Task">
                            <i class="fas fa-edit"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    setupEventListeners() {
        window.taskController = {
            addTask: () => this.openAddTaskModal(),
            viewTask: (taskId) => this.openTaskDetailModal(taskId),
            editTask: (taskId) => this.openEditTaskModal(taskId),
            completeTask: (taskId) => this.completeTask(taskId)
        };
    }
}

// =============================================================================
// 6. PROVIDER NETWORK COMPONENT
// =============================================================================

class ProviderNetwork {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.searchFilters = {};
        this.init();
    }
    
    init() {
        appState.subscribe('providers', (data) => this.render(data));
        this.loadProviders();
    }
    
    async searchProviders(filters = {}) {
        appState.setState('providers.loading', true);
        
        try {
            const response = await fetch('/api/services/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(filters)
            });
            
            const data = await response.json();
            
            if (data.success) {
                appState.setState('providers.search_results', data.results);
                appState.setState('providers.search_summary', data.search_summary);
            }
        } catch (error) {
            this.showError('Failed to search providers');
        } finally {
            appState.setState('providers.loading', false);
        }
    }
    
    render(data) {
        this.container.innerHTML = `
            <div class="provider-header mb-4">
                <h4 class="mb-3">Service Provider Network</h4>
                ${this.renderSearchInterface()}
            </div>
            
            ${data.search_summary ? this.renderSearchSummary(data.search_summary) : ''}
            
            ${data.loading ? this.renderLoading() : this.renderProviderResults(data.search_results)}
        `;
        
        this.setupEventListeners();
    }
    
    renderSearchInterface() {
        return `
            <div class="provider-search-form">
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label">Service Category</label>
                        <select class="form-select" id="serviceCategoryFilter">
                            <option value="">All Service Categories</option>
                            <option value="Housing Services">Housing Services</option>
                            <option value="Mental Health Services">Mental Health Services</option>
                            <option value="Medical Services">Medical Services</option>
                            <option value="Substance Abuse">Substance Abuse</option>
                            <option value="Legal Services">Legal Services</option>
                            <option value="Employment Support">Employment Support</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Location</label>
                        <input type="text" class="form-control" id="locationFilter" placeholder="City or County">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Availability</label>
                        <select class="form-select" id="availabilityFilter">
                            <option value="">Any Availability</option>
                            <option value="Accepting">Accepting New Clients</option>
                            <option value="Waitlist">Waitlist Available</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">&nbsp;</label>
                        <button class="btn btn-primary w-100" onclick="providerController.search()">
                            <i class="fas fa-search me-1"></i>Search
                        </button>
                    </div>
                </div>
                
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="form-check-group">
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" id="backgroundFriendly">
                                <label class="form-check-label" for="backgroundFriendly">Background-Friendly</label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" id="servesVeterans">
                                <label class="form-check-label" for="servesVeterans">Serves Veterans</label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" id="acceptsMedicaid">
                                <label class="form-check-label" for="acceptsMedicaid">Accepts Medicaid</label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" id="slidingScale">
                                <label class="form-check-label" for="slidingScale">Sliding Scale Fees</label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    setupEventListeners() {
        window.providerController = {
            search: () => this.performSearch(),
            viewProvider: (providerId) => this.openProviderDetailModal(providerId),
            createReferral: (providerId, serviceId) => this.openCreateReferralModal(null, providerId, serviceId)
        };
    }
    
    performSearch() {
        const filters = {
            service_category: document.getElementById('serviceCategoryFilter').value,
            city: document.getElementById('locationFilter').value,
            current_availability: document.getElementById('availabilityFilter').value,
            background_friendly: document.getElementById('backgroundFriendly').checked,
            serves_veterans: document.getElementById('servesVeterans').checked,
            accepts_medicaid: document.getElementById('acceptsMedicaid').checked,
            sliding_scale: document.getElementById('slidingScale').checked
        };
        
        this.searchProviders(filters);
    }
}

// =============================================================================
// 7. MODAL MANAGEMENT SYSTEM
// =============================================================================

class ModalManager {
    constructor() {
        this.activeModals = new Map();
        this.init();
    }
    
    init() {
        // Create modal container if it doesn't exist
        if (!document.getElementById('modalContainer')) {
            const container = document.createElement('div');
            container.id = 'modalContainer';
            document.body.appendChild(container);
        }
    }
    
    show(modalId, content, options = {}) {
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog ${options.size || 'modal-lg'}">
                    <div class="modal-content">
                        ${content}
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('modalContainer').innerHTML = modalHtml;
        
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();
        
        this.activeModals.set(modalId, modal);
        
        // Auto-cleanup on hide
        document.getElementById(modalId).addEventListener('hidden.bs.modal', () => {
            this.activeModals.delete(modalId);
            document.getElementById(modalId).remove();
        });
        
        return modal;
    }
    
    hide(modalId) {
        const modal = this.activeModals.get(modalId);
        if (modal) {
            modal.hide();
        }
    }
}

// Global modal manager instance
const modalManager = new ModalManager();

// =============================================================================
// 8. MAIN APPLICATION INITIALIZATION
// =============================================================================

class CaseManagementApp {
    constructor() {
        this.components = {};
        this.init();
    }
    
    init() {
        // Initialize components when DOM is ready
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeComponents();
            this.setupNavigation();
            this.setupNotifications();
        });
    }
    
    initializeComponents() {
        // Initialize all main components
        this.components.dashboard = new DashboardOverview('dashboardContent');
        this.components.caseload = new CaseloadManagement('caseloadContent');
        this.components.referrals = new ReferralTracking('referralContent');
        this.components.tasks = new TaskManagement('taskContent');
        this.components.providers = new ProviderNetwork('providerContent');
        
        // Load initial section
        this.showSection('dashboard');
    }
    
    setupNavigation() {
        // Setup sidebar navigation
        document.querySelectorAll('[data-section]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.closest('[data-section]').dataset.section;
                this.showSection(section);
            });
        });
    }
    
    showSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.main-content > div').forEach(section => {
            section.style.display = 'none';
        });
        
        // Show selected section
        const targetSection = document.getElementById(`${sectionName}Content`);
        if (targetSection) {
            targetSection.style.display = 'block';
        }
        
        // Update navigation
        document.querySelectorAll('[data-section]').forEach(link => {
            link.classList.remove('active');
        });
        
        const activeLink = document.querySelector(`[data-section="${sectionName}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
        
        // Update app state
        appState.setState('ui.active_section', sectionName);
    }
    
    setupNotifications() {
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        
        // Setup toast container
        if (!document.getElementById('toastContainer')) {
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        const container = document.getElementById('toastContainer');
        container.insertAdjacentHTML('beforeend', toastHtml);
        
        const toast = new bootstrap.Toast(container.lastElementChild, { delay: duration });
        toast.show();
    }
}

// Initialize the application
const app = new CaseManagementApp();