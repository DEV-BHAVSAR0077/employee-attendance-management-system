// Employees Page JavaScript

let allEmployees = [];
let employeeStats = {};
let currentPage = 1;
let recordsPerPage = 10;
let currentFilteredEmployees = [];

document.addEventListener('DOMContentLoaded', function () {
    loadEmployeesData();
});

async function loadEmployeesData() {
    try {
        // Load employees list
        const empResponse = await fetch('/api/employees');
        const empData = await empResponse.json();
        allEmployees = empData.employees || [];

        // Load attendance records for stats (last 30 days default)
        const today = new Date();
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(today.getDate() - 30);

        const startDate = thirtyDaysAgo.toISOString().split('T')[0];
        const endDate = today.toISOString().split('T')[0];

        const recordsResponse = await fetch(`/api/attendance/range?startDate=${startDate}&endDate=${endDate}`);
        const recordsData = await recordsResponse.json();

        calculateEmployeeStats(recordsData.records || []);

        currentFilteredEmployees = [...allEmployees];
        updateEmployeeTable();
        updateOverallStats();

    } catch (error) {
        console.error('Error loading employees data:', error);
        showToast('Failed to load employee data', 'error');
    }
}

function calculateEmployeeStats(records) {
    employeeStats = {};

    // Initialize stats for all employees
    allEmployees.forEach(emp => {
        employeeStats[emp.employee_id] = {
            id: emp.employee_id,
            name: emp.employee_name,
            totalRecords: 0,
            present: 0,
            absent: 0,
            late: 0,
            totalHours: 0,
            records: [] // Store individual records for modal
        };
    });

    // Process records
    records.forEach(record => {
        if (!employeeStats[record.employee_id]) {
            // Handle case where employee might not be in the initial list (though unlikely if synced)
            employeeStats[record.employee_id] = {
                id: record.employee_id,
                name: record.employee_name,
                totalRecords: 0,
                present: 0,
                absent: 0,
                late: 0,
                totalHours: 0,
                records: []
            };
            // Add to allEmployees if not present
            if (!allEmployees.find(e => e.employee_id === record.employee_id)) {
                allEmployees.push({ employee_id: record.employee_id, employee_name: record.employee_name });
            }
        }

        const stats = employeeStats[record.employee_id];
        stats.totalRecords++;
        stats.records.push(record);

        if (record.status === 'Present' || record.status === 'Half Day') stats.present++;
        if (record.status === 'Absent') stats.absent++;
        if (record.status.includes('Late')) stats.late++;

        if (record.working_hours) {
            stats.totalHours += parseFloat(record.working_hours);
        }
    });
}

function updateOverallStats() {
    document.getElementById('totalEmployeesCount').textContent = allEmployees.length;

    // Calculate active employees (those with records in the period)
    const activeCount = Object.values(employeeStats).filter(s => s.totalRecords > 0).length;
    document.getElementById('activeEmployeesCount').textContent = activeCount;

    // Calculate Average Attendance Rate
    let totalRate = 0;
    let count = 0;
    Object.values(employeeStats).forEach(s => {
        if (s.totalRecords > 0) {
            const rate = (s.present / s.totalRecords) * 100;
            totalRate += rate;
            count++;
        }
    });
    const avgRate = count > 0 ? (totalRate / count).toFixed(1) : 0;
    document.getElementById('avgAttendanceRate').textContent = `${avgRate}%`;

    // Find Top Performer (highest attendance rate & hours)
    let topPerformer = null;
    let maxScore = -1;

    Object.values(employeeStats).forEach(s => {
        if (s.totalRecords > 0) { // Calculate for any employee with records
            const rate = (s.present / s.totalRecords) * 100;
            const avgHours = s.totalHours / s.totalRecords;
            const score = rate * avgHours; // Simple scoring

            if (score > maxScore) {
                maxScore = score;
                topPerformer = s;
            }
        }
    });

    if (topPerformer) {
        document.getElementById('topPerformerName').textContent = topPerformer.name;
    } else {
        document.getElementById('topPerformerName').textContent = '-';
    }
}

function updateEmployeeTable() {
    const tbody = document.getElementById('employeeTableBody');

    if (currentFilteredEmployees.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No employees found</td></tr>';
        updatePagination(0);
        return;
    }

    const totalPages = Math.ceil(currentFilteredEmployees.length / recordsPerPage);
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = startIndex + recordsPerPage;
    const paginatedEmployees = currentFilteredEmployees.slice(startIndex, endIndex);

    tbody.innerHTML = paginatedEmployees.map(emp => {
        const stats = employeeStats[emp.employee_id] || { totalRecords: 0, present: 0, absent: 0, totalHours: 0 };
        const rate = stats.totalRecords > 0 ? Math.round((stats.present / stats.totalRecords) * 100) : 0;
        const avgHours = stats.totalRecords > 0 ? (stats.totalHours / stats.totalRecords) : 0;

        return `
            <tr>
                <td>${emp.employee_id}</td>
                <td>${emp.employee_name}</td>
                <td>${stats.totalRecords}</td>
                <td><span class="text-success">${stats.present}</span></td>
                <td><span class="text-danger">${stats.absent}</span></td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="mr-2">${rate}%</span>
                        <div class="progress" style="height: 4px; width: 50px; background: #e5e7eb; margin-left: 5px;">
                            <div class="progress-bar" style="width: ${rate}%; background: ${rate > 80 ? '#10b981' : '#f59e0b'}; height: 100%;"></div>
                        </div>
                    </div>
                </td>
                <td>${formatHours(avgHours)}</td>
                <td>
                    <button onclick="viewEmployeeDetails('${emp.employee_id}')" class="btn btn-outline btn-sm">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    updatePagination(totalPages);
}

function filterEmployees() {
    const searchTerm = document.getElementById('employeeSearch').value.toLowerCase();

    currentFilteredEmployees = allEmployees.filter(emp =>
        emp.employee_name.toLowerCase().includes(searchTerm) ||
        emp.employee_id.toLowerCase().includes(searchTerm)
    );

    currentPage = 1;
    updateEmployeeTable();
}

function updatePagination(totalPages) {
    document.getElementById('empPageInfo').textContent = `Page ${currentPage} of ${totalPages || 1}`;
    document.getElementById('empPrevBtn').disabled = currentPage === 1;
    document.getElementById('empNextBtn').disabled = currentPage >= totalPages;
}

function changeEmployeePage(delta) {
    currentPage += delta;
    updateEmployeeTable();
}

function viewEmployeeDetails(employeeId) {
    const stats = employeeStats[employeeId];
    if (!stats) return;

    document.getElementById('modalEmployeeName').textContent = stats.name;
    document.getElementById('modalEmployeeId').textContent = stats.id;
    document.getElementById('modalTotalRecords').textContent = stats.totalRecords;

    const rate = stats.totalRecords > 0 ? Math.round((stats.present / stats.totalRecords) * 100) : 0;
    document.getElementById('modalAttendanceRate').textContent = `${rate}%`;

    const avgHours = stats.totalRecords > 0 ? (stats.totalHours / stats.totalRecords) : 0;
    document.getElementById('modalAvgHours').textContent = formatHours(avgHours);

    // Populate history table
    const historyBody = document.getElementById('modalAttendanceHistory');

    // Sort records by date descending
    const sortedRecords = [...stats.records].sort((a, b) => new Date(b.date) - new Date(a.date));

    if (sortedRecords.length === 0) {
        historyBody.innerHTML = '<tr><td colspan="5" class="text-center">No attendance records found</td></tr>';
    } else {
        historyBody.innerHTML = sortedRecords.slice(0, 10).map(record => `
            <tr>
                <td>${new Date(record.date).toLocaleDateString()}</td>
                <td>${record.punch_in_time || '-'}</td>
                <td>${record.punch_out_time || '-'}</td>
                <td>${formatHours(record.working_hours)}</td>
                <td><span class="status-badge status-${record.status.toLowerCase().replace(' ', '-')}">${record.status}</span></td>
            </tr>
        `).join('');
    }

    document.getElementById('employeeModal').style.display = 'flex';
}

function closeEmployeeModal() {
    document.getElementById('employeeModal').style.display = 'none';
}

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    const modal = document.getElementById('employeeModal');
    if (e.target === modal) {
        closeEmployeeModal();
    }
});

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
