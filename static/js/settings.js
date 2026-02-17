// Settings Page JavaScript

let currentHistoryRecords = [];
let currentHistoryPage = 1;
let historyRecordsPerPage = 10;

document.addEventListener('DOMContentLoaded', function () {
    loadUploadHistory();
    loadAttendanceConfig();

    document.getElementById('attendanceConfigForm').addEventListener('submit', saveAttendanceConfig);
});

async function loadAttendanceConfig() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();

        if (data.standard_start_time) {
            document.getElementById('standardStartTime').value = data.standard_start_time;
        }
        if (data.standard_end_time) {
            document.getElementById('standardEndTime').value = data.standard_end_time;
        }
        if (data.standard_break_start) {
            document.getElementById('standardBreakStart').value = data.standard_break_start;
        }
        if (data.standard_break_end) {
            document.getElementById('standardBreakEnd').value = data.standard_break_end;
        }
        if (data.max_break_duration) {
            document.getElementById('maxBreakDuration').value = data.max_break_duration;
        }
        if (data.half_day_time) {
            document.getElementById('halfDayTime').value = data.half_day_time;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        showToast('Failed to load settings', 'error');
    }
}

async function saveAttendanceConfig(e) {
    e.preventDefault();

    const startTime = document.getElementById('standardStartTime').value;
    const endTime = document.getElementById('standardEndTime').value;
    const breakStart = document.getElementById('standardBreakStart').value;
    const breakEnd = document.getElementById('standardBreakEnd').value;
    const maxBreak = document.getElementById('maxBreakDuration').value;

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                standard_start_time: startTime,
                standard_end_time: endTime,
                standard_break_start: breakStart,
                standard_break_end: breakEnd,
                max_break_duration: maxBreak,
                half_day_time: document.getElementById('halfDayTime').value
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Configuration saved successfully', 'success');
        } else {
            throw new Error(data.error || 'Failed to save configuration');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showToast('Failed to save settings: ' + error.message, 'error');
    }
}

async function loadUploadHistory() {
    try {
        const response = await fetch('/api/upload-history');
        const data = await response.json();
        currentHistoryRecords = data.history || [];

        // Reset to first page when loading new records
        currentHistoryPage = 1;
        displayUploadHistory(currentHistoryRecords);
    } catch (error) {
        console.error('Error loading upload history:', error);
        showToast('Failed to load upload history', 'error');
    }
}

function displayUploadHistory(history) {
    const tbody = document.getElementById('settingsHistoryTableBody');

    if (history.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">
                    <p class="no-data">No upload history available</p>
                </td>
            </tr>
        `;
        updateHistoryPaginationControls(0);
        return;
    }

    // Calculate pagination
    const totalPages = Math.ceil(history.length / historyRecordsPerPage);
    const startIndex = (currentHistoryPage - 1) * historyRecordsPerPage;
    const endIndex = startIndex + historyRecordsPerPage;
    const paginatedHistory = history.slice(startIndex, endIndex);

    // Display paginated records
    tbody.innerHTML = paginatedHistory.map(item => `
        <tr>
            <td>${item.file_name}</td>
            <td>${formatDateTime(item.upload_date)}</td>
            <td>${item.records_processed}</td>
            <td><span class="text-success">${item.records_success}</span></td>
            <td><span class="text-danger">${item.records_failed}</span></td>
            <td>
                <span class="status-badge status-${item.status.toLowerCase().replace(' ', '-')}">
                    ${item.status}
                </span>
            </td>
        </tr>
    `).join('');

    updateHistoryPaginationControls(totalPages);
}

function updateHistoryPaginationControls(totalPages) {
    const prevBtn = document.getElementById('histPrevBtn');
    const nextBtn = document.getElementById('histNextBtn');
    const pageInfo = document.getElementById('histPageInfo');

    if (totalPages <= 1) {
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        pageInfo.textContent = 'Page 1 of 1';
        return;
    }

    prevBtn.disabled = currentHistoryPage === 1;
    nextBtn.disabled = currentHistoryPage === totalPages;
    pageInfo.textContent = `Page ${currentHistoryPage} of ${totalPages}`;
}

function changeHistoryPage(delta) {
    const totalPages = Math.ceil(currentHistoryRecords.length / historyRecordsPerPage);
    const newPage = currentHistoryPage + delta;

    if (newPage >= 1 && newPage <= totalPages) {
        currentHistoryPage = newPage;
        displayUploadHistory(currentHistoryRecords);
    }
}

function exportAllData() {
    window.location.href = '/api/export/excel';
}

async function clearAllData() {
    if (!confirm('⚠️ WARNING: This will permanently delete ALL attendance data and upload history!\n\nThis action cannot be undone. Are you sure you want to continue?')) {
        return;
    }

    try {
        const response = await fetch('/api/delete-upload', {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            showToast('All data cleared successfully', 'success');
            loadUploadHistory(); // Should be empty now
        } else {
            throw new Error(data.error || 'Failed to clear data');
        }
    } catch (error) {
        console.error('Error clearing data:', error);
        showToast('Failed to clear data: ' + error.message, 'error');
    }
}

async function recalculateData() {
    if (!confirm('This will update all attendance records based on the currently saved settings.\n\nContinue?')) {
        return;
    }

    try {
        const response = await fetch('/api/recalculate', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            showToast(data.message, 'success');
        } else {
            throw new Error(data.error || 'Recalculation failed');
        }
    } catch (error) {
        console.error('Error recalculating:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
