// Global state
let currentEmployees = [];
let currentRecords = [];
let timeChart = null;
let currentPage = 1;
let recordsPerPage = 8;
let uploadedFileInfo = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    console.log('Dashboard initializing...');
    setupFilters(); // Set filters first

    // Wait for Chart.js to be available
    if (typeof Chart !== 'undefined') {
        console.log('Chart.js loaded, initializing chart...');
        initializeChart();
    } else {
        console.error('Chart.js not loaded!');
    }

    initializeDashboard(); // Then load data using those filters
    setupFileUpload();
});

// Initialize dashboard data
async function initializeDashboard() {
    await loadStatistics();
    await loadEmployees();
    await loadAttendanceRecords();
    await checkExistingUpload(); // Check if there's already uploaded data
}

// Check if there's existing uploaded data and show the file display
async function checkExistingUpload() {
    try {
        const response = await fetch('/api/upload-history');
        const data = await response.json();

        if (data.history && data.history.length > 0) {
            // Get the most recent upload
            const latestUpload = data.history[0];

            // Check if there's actual attendance data
            const statsResponse = await fetch(`/api/statistics?startDate=${getDefaultStartDate()}&endDate=${getDefaultEndDate()}`);
            const statsData = await statsResponse.json();

            if (statsData.totalRecords > 0) {
                // Restore uploaded file info
                uploadedFileInfo = {
                    fileName: latestUpload.file_name,
                    uploadDate: new Date(latestUpload.upload_date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                    }),
                    recordsProcessed: latestUpload.records_processed,
                    recordsSuccess: latestUpload.records_success,
                    recordsFailed: latestUpload.records_failed,
                    filePath: latestUpload.file_path
                };

                // Show the uploaded file display
                showUploadedFileDisplay();
            }
        }
    } catch (error) {
        console.error('Error checking existing upload:', error);
    }
}

// Helper function to get default start date (30 days ago)
function getDefaultStartDate() {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
}

// Helper function to get default end date (today)
function getDefaultEndDate() {
    return new Date().toISOString().split('T')[0];
}

// Setup file upload
function setupFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');

    if (!uploadArea || !fileInput) return;

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#10b981';
        uploadArea.style.background = 'rgba(16, 185, 129, 0.05)';
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.style.borderColor = '#cbd5e1';
        uploadArea.style.background = '';
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#cbd5e1';
        uploadArea.style.background = '';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // Click to upload
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

// Handle file upload
async function handleFileUpload(file) {
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        showToast('Please upload an Excel file (.xlsx or .xls)', 'error');
        return;
    }

    const progressDiv = document.getElementById('uploadProgress');
    const resultDiv = document.getElementById('uploadResult');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    progressDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    progressFill.style.width = '30%';
    progressText.textContent = 'Uploading file...';

    const formData = new FormData();
    formData.append('file', file);

    // Check if we are uploading for a specific date (from Calendar)
    // Make sure we are in the context of the modal or just use selectedDate if set?
    // We should be careful. If the user closes the modal, selectedDate should be null.
    if (selectedDate) {
        formData.append('target_date', selectedDate);
        console.log('Uploading for target date:', selectedDate);
    }

    try {
        progressFill.style.width = '60%';
        progressText.textContent = 'Processing attendance data...';

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        progressFill.style.width = '100%';
        progressText.textContent = 'Upload complete!';

        setTimeout(async () => {
            progressDiv.style.display = 'none';

            if (data.success) {
                // Store uploaded file info
                uploadedFileInfo = {
                    fileName: file.name,
                    uploadDate: new Date().toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                    }),
                    recordsProcessed: data.recordsProcessed,
                    recordsSuccess: data.recordsSuccess,
                    recordsFailed: data.recordsFailed,
                    filePath: data.filePath
                };

                // Hide upload area and show uploaded file display
                document.getElementById('uploadArea').style.display = 'none';
                showUploadedFileDisplay();

                // Auto-adjust date filters to match the uploaded data
                if (data.minDate && data.maxDate) {
                    document.getElementById('startDate').value = data.minDate;
                    document.getElementById('endDate').value = data.maxDate;
                }

                // Refresh data
                loadStatistics();
                loadAttendanceRecords();

                // Refresh Calendar
                await fetchCalendarDates();
                renderCalendar();

                // If modal is open, refresh it too
                if (selectedDate && document.getElementById('dailyAnalysisModal').style.display === 'block') {
                    openDailyModal(selectedDate); // Refresh modal content
                }

                showToast('Attendance data uploaded successfully!', 'success');
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        }, 500);

    } catch (error) {
        progressDiv.style.display = 'none';
        resultDiv.className = 'upload-result error';
        resultDiv.innerHTML = `<strong>✗ Upload Failed</strong><br>${error.message}`;
        resultDiv.style.display = 'block';
        showToast('Upload failed: ' + error.message, 'error');
    }
}

// Load statistics
async function loadStatistics() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const employeeId = document.getElementById('employeeFilter').value;

    try {
        let url = `/api/statistics?`;
        const params = [];
        if (startDate) params.push(`startDate=${startDate}`);
        if (endDate) params.push(`endDate=${endDate}`);
        if (employeeId) params.push(`employeeId=${employeeId}`);

        url += params.join('&');

        const response = await fetch(url);
        const data = await response.json();

        document.getElementById('totalRecords').textContent = data.totalRecords || 0;
        document.getElementById('totalEmployees').textContent = data.totalEmployees || 0;
        document.getElementById('attendanceRate').textContent = (data.attendanceRate || 0) + '%';
        document.getElementById('avgHours').textContent = formatHours(data.averageWorkingHours);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load employees
async function loadEmployees() {
    try {
        const response = await fetch('/api/employees');
        const data = await response.json();
        currentEmployees = data.employees || [];

        const employeeFilter = document.getElementById('employeeFilter');
        employeeFilter.innerHTML = '<option value="">All Employees</option>';

        currentEmployees.forEach(emp => {
            const option = document.createElement('option');
            option.value = emp.employee_id;
            option.textContent = `${emp.employee_name} (${emp.employee_id})`;
            employeeFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading employees:', error);
    }
}

// Load attendance records
async function loadAttendanceRecords() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const employeeId = document.getElementById('employeeFilter').value;

    // Set default dates if not set (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    const start = startDate || thirtyDaysAgo.toISOString().split('T')[0];
    const end = endDate || today.toISOString().split('T')[0];

    try {
        let url = `/api/attendance/range?startDate=${start}&endDate=${end}`;
        if (employeeId) {
            url += `&employeeId=${employeeId}`;
        }

        const response = await fetch(url);
        const data = await response.json();
        currentRecords = data.records || [];

        // Reset to first page when loading new records
        currentPage = 1;
        displayAttendanceRecords(currentRecords);

        // Update pie chart
        const { totalWorkingHours, totalBreakHours } = calculateTimeDistribution(currentRecords);
        updateChart(totalWorkingHours, totalBreakHours);
    } catch (error) {
        console.error('Error loading attendance records:', error);
        showToast('Failed to load attendance records', 'error');
    }
}

// Display attendance records in table with pagination
function displayAttendanceRecords(records) {
    const tbody = document.getElementById('attendanceTableBody');

    if (records.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">
                    <p class="no-data">No attendance records found for the selected criteria.</p>
                </td>
            </tr>
        `;
        updatePaginationControls(0);
        return;
    }

    // Calculate pagination
    const totalPages = Math.ceil(records.length / recordsPerPage);
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = startIndex + recordsPerPage;
    const paginatedRecords = records.slice(startIndex, endIndex);

    // Display paginated records
    tbody.innerHTML = paginatedRecords.map(record => `
        <tr>
            <td>${record.employee_id}</td>
            <td>${record.employee_name}</td>
            <td>${formatDate(record.date)}</td>
            <td>${record.punch_in_time || '-'}</td>
            <td>${record.punch_out_time || '-'}</td>
            <td>${formatHours(record.working_hours)}</td>
            <td>
                <span class="status-badge status-${record.status.toLowerCase().replace(/\s+/g, '-')}">
                    ${record.status}
                </span>
            </td>
        </tr>
    `).join('');

    // Update pagination controls
    updatePaginationControls(totalPages);
}

// Update pagination controls
function updatePaginationControls(totalPages) {
    let paginationDiv = document.getElementById('paginationControls');

    if (!paginationDiv) {
        // Create pagination controls if they don't exist
        const tableCard = document.querySelector('.card-body .table-responsive').parentElement;
        paginationDiv = document.createElement('div');
        paginationDiv.id = 'paginationControls';
        paginationDiv.className = 'pagination-controls';
        tableCard.appendChild(paginationDiv);
    }

    if (totalPages <= 1) {
        paginationDiv.style.display = 'none';
        return;
    }

    paginationDiv.style.display = 'flex';

    const startRecord = (currentPage - 1) * recordsPerPage + 1;
    const endRecord = Math.min(currentPage * recordsPerPage, currentRecords.length);

    paginationDiv.innerHTML = `
        <div class="pagination-info">
            Showing ${startRecord}-${endRecord} of ${currentRecords.length} records
        </div>
        <div class="pagination-buttons">
            <button 
                onclick="changePage(${currentPage - 1})" 
                class="btn btn-outline btn-sm" 
                ${currentPage === 1 ? 'disabled' : ''}
            >
                <i class="fas fa-chevron-left"></i> Previous
            </button>
            <span class="pagination-page">Page ${currentPage} of ${totalPages}</span>
            <button 
                onclick="changePage(${currentPage + 1})" 
                class="btn btn-outline btn-sm" 
                ${currentPage === totalPages ? 'disabled' : ''}
            >
                Next <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    `;
}

// Change page
function changePage(page) {
    const totalPages = Math.ceil(currentRecords.length / recordsPerPage);

    if (page < 1 || page > totalPages) {
        return;
    }

    currentPage = page;
    displayAttendanceRecords(currentRecords);

    // Scroll to top of table
    document.querySelector('.table-responsive').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Setup filters
function setupFilters() {
    // Set default date range (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    document.getElementById('endDate').valueAsDate = today;
    document.getElementById('startDate').valueAsDate = thirtyDaysAgo;
}

// Apply filters
function applyFilters() {
    loadAttendanceRecords();
    loadStatistics();
}

// Reset filters
function resetFilters() {
    setupFilters();
    document.getElementById('employeeFilter').value = '';
    loadAttendanceRecords();
    loadStatistics();
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Initialize pie chart
function initializeChart() {
    const ctx = document.getElementById('timeChart');
    if (!ctx) {
        console.error('Canvas element #timeChart not found!');
        return;
    }

    console.log('Creating pie chart...');

    try {
        timeChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Working Time', 'Break Time'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: [
                        '#10b981', // Emerald for working time
                        '#f59e0b'  // Amber for break time
                    ],
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const hours = Math.floor(value);
                                const minutes = Math.round((value - hours) * 60);
                                return `${label}: ${hours}h ${minutes}m`;
                            }
                        }
                    }
                }
            }
        });

        console.log('Chart created successfully!');
    } catch (error) {
        console.error('Error creating chart:', error);
    }
}

// Update pie chart with new data
function updateChart(workingHours, breakHours) {
    console.log(`Updating chart: Working=${workingHours}h, Break=${breakHours}h`);

    if (!timeChart) {
        console.error('Chart not initialized! Attempting to initialize...');
        initializeChart();
        if (!timeChart) {
            console.error('Failed to initialize chart');
            return;
        }
    }

    try {
        timeChart.data.datasets[0].data = [workingHours, breakHours];
        timeChart.update();
        console.log('Chart updated successfully');

        // Update legend
        const legendDiv = document.getElementById('chartLegend');
        if (legendDiv) {
            const totalHours = workingHours + breakHours;
            const workingPercent = totalHours > 0 ? ((workingHours / totalHours) * 100).toFixed(1) : 0;
            const breakPercent = totalHours > 0 ? ((breakHours / totalHours) * 100).toFixed(1) : 0;

            legendDiv.innerHTML = `
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #10b981;"></div>
                    <span class="legend-label">Working Time:</span>
                    <span class="legend-value">${Math.floor(workingHours)}h ${Math.round((workingHours % 1) * 60)}m (${workingPercent}%)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #f59e0b;"></div>
                    <span class="legend-label">Break Time:</span>
                    <span class="legend-value">${Math.floor(breakHours)}h ${Math.round((breakHours % 1) * 60)}m (${breakPercent}%)</span>
                </div>
            `;
            console.log('Legend updated');
        } else {
            console.error('Legend element not found');
        }
    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

// Calculate time distribution from records
function calculateTimeDistribution(records) {
    console.log(`Calculating time distribution for ${records.length} records`);

    let totalWorkingHours = 0;
    let recordCount = 0;

    records.forEach(record => {
        if (record.working_hours && record.working_hours > 0) {
            const workingHours = parseFloat(record.working_hours);
            totalWorkingHours += workingHours;
            recordCount++;
        }
    });

    // Calculate average working hours per day
    const avgWorkingHours = recordCount > 0 ? totalWorkingHours / recordCount : 8;

    // Estimate break time (assuming standard 9-hour workday: 8 hours work + 1 hour break)
    // Total time at office = working hours + break hours
    const standardWorkday = 9; // hours
    const estimatedTotalTime = recordCount * standardWorkday;
    const totalBreakHours = Math.max(0, estimatedTotalTime - totalWorkingHours);

    console.log(`Total Working: ${totalWorkingHours}h, Total Break: ${totalBreakHours}h from ${recordCount} records`);

    return {
        totalWorkingHours: totalWorkingHours,
        totalBreakHours: totalBreakHours
    };
}

// Show uploaded file display
function showUploadedFileDisplay() {
    if (!uploadedFileInfo) return;

    const uploadedFileDisplay = document.getElementById('uploadedFileDisplay');
    const uploadedFileName = document.getElementById('uploadedFileName');
    const uploadedFileDate = document.getElementById('uploadedFileDate');
    const uploadedFileRecords = document.getElementById('uploadedFileRecords');

    uploadedFileName.textContent = uploadedFileInfo.fileName;
    uploadedFileDate.textContent = `Uploaded on ${uploadedFileInfo.uploadDate}`;
    uploadedFileRecords.textContent = `${uploadedFileInfo.recordsProcessed} records processed`;

    uploadedFileDisplay.style.display = 'block';
}


async function downloadUploadedFile() {
    window.location.href = '/api/download-latest-file';
}

async function deleteUploadedFile() {
    if (!confirm('Are you sure you want to delete all uploaded data? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/api/delete-upload', {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            // Reset UI
            document.getElementById('uploadedFileDisplay').style.display = 'none';
            document.getElementById('uploadArea').style.display = 'block';
            document.getElementById('fileInput').value = '';

            uploadedFileInfo = null;

            // Refresh data
            loadStatistics();
            loadAttendanceRecords();

            showToast('All data deleted successfully');
        } else {
            throw new Error(data.error || 'Failed to delete data');
        }
    } catch (error) {
        console.error('Error deleting data:', error);
        showToast('Failed to delete data', 'error');
    }
}

function replaceFile() {
    if (confirm('Replacing the file will delete the current data. Do you want to continue?')) {
        document.getElementById('fileInput').click();
    }
}

// --- Calendar Logic ---

let calendarDate = new Date();
let datesWithData = new Set();
let selectedDate = null;

// Initialize Calendar
async function initCalendar() {
    console.log('Initializing calendar...');

    // Set listeners for controls
    document.getElementById('prevMonth').addEventListener('click', () => changeMonth(-1));
    document.getElementById('nextMonth').addEventListener('click', () => changeMonth(1));

    // Modal close
    document.querySelector('.close-modal').addEventListener('click', closeDailyModal);
    window.addEventListener('click', (e) => {
        if (e.target == document.getElementById('dailyAnalysisModal')) {
            closeDailyModal();
        }
    });

    document.getElementById('btnUploadDaily').addEventListener('click', () => {
        closeDailyModal();
        document.getElementById('fileInput').click();
    });

    await fetchCalendarDates();
    renderCalendar();
}

// Fetch dates that have data
async function fetchCalendarDates() {
    try {
        const response = await fetch('/api/calendar-dates');
        const data = await response.json();
        datesWithData = new Set(data.dates); // Set of 'YYYY-MM-DD' strings
        console.log('Dates with data:', datesWithData);
    } catch (error) {
        console.error('Error fetching calendar dates:', error);
    }
}

// Change month
function changeMonth(delta) {
    calendarDate.setMonth(calendarDate.getMonth() + delta);
    renderCalendar();
}

// Render Calendar
function renderCalendar() {
    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth();

    // Update header
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    document.getElementById('currentMonthYear').textContent = `${monthNames[month]} ${year}`;

    const grid = document.getElementById('calendarGrid');
    grid.innerHTML = '';

    // First day of month
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startingDay = firstDay.getDay(); // 0 (Sun) to 6 (Sat)
    const totalDays = lastDay.getDate();

    // Previous month filler
    for (let i = 0; i < startingDay; i++) {
        const dayDiv = document.createElement('div');
        dayDiv.className = 'calendar-day empty';
        grid.appendChild(dayDiv);
    }

    // Days
    const todayStr = new Date().toISOString().split('T')[0];

    for (let day = 1; day <= totalDays; day++) {
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const dayDiv = document.createElement('div');
        dayDiv.className = 'calendar-day';

        // Determine day of week
        const currentDayObj = new Date(year, month, day);
        const isSunday = currentDayObj.getDay() === 0;

        // Classes
        if (dateStr === todayStr) dayDiv.classList.add('today');
        if (datesWithData.has(dateStr)) dayDiv.classList.add('has-data');
        if (isSunday) dayDiv.classList.add('holiday');

        // Content
        dayDiv.innerHTML = `<span class="calendar-day-number">${day}</span>`;
        if (isSunday) {
            dayDiv.innerHTML += `<span class="calendar-holiday-label">Holiday</span>`;
        }

        // Click event
        dayDiv.addEventListener('click', () => openDailyModal(dateStr, isSunday));

        grid.appendChild(dayDiv);
    }
}

// Open Daily Modal
async function openDailyModal(dateStr, isSunday = false) {
    selectedDate = dateStr;
    const modal = document.getElementById('dailyAnalysisModal');
    const title = document.getElementById('modalDateTitle');
    const statsDiv = document.getElementById('dailyStats');
    const actionDiv = document.getElementById('dailyUploadAction');
    const noDataMsg = document.getElementById('dailyNoDataMsg');

    // Format title
    const dateObj = new Date(dateStr);
    title.textContent = `Analysis for ${dateObj.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`;

    modal.style.display = 'block';

    if (isSunday) {
        // Sunday Logic
        statsDiv.style.display = 'none';
        actionDiv.style.display = 'block';
        noDataMsg.textContent = "Weekly Holiday (Sunday)";
        document.getElementById('btnUploadDaily').style.display = 'none';
        return;
    }

    // Check if data exists
    if (datesWithData.has(dateStr)) {
        // Show stats, hide upload (unless we want to allow re-upload? constraint logic handles it)
        statsDiv.style.display = 'grid';
        actionDiv.style.display = 'none'; // Or 'block' if we allow overwrite

        // Fetch stats for this day
        try {
            const response = await fetch(`/api/statistics?startDate=${dateStr}&endDate=${dateStr}`);
            const data = await response.json();

            document.getElementById('dailyPresent').textContent = data.presentCount;
            document.getElementById('dailyAbsent').textContent = data.absentCount;
            document.getElementById('dailyAvgHours').textContent = formatHours(data.averageWorkingHours);

            // Calculate Late
            const recordsResp = await fetch(`/api/attendance/date?date=${dateStr}`);
            const recordsData = await recordsResp.json();
            const records = recordsData.records || [];

            const lateCount = records.filter(r => r.is_late).length;
            document.getElementById('dailyLate').textContent = lateCount;

        } catch (e) {
            console.error(e);
            statsDiv.style.display = 'none';
            actionDiv.style.display = 'block';
            noDataMsg.textContent = "Error loading data.";
        }

    } else {
        // No data
        statsDiv.style.display = 'none';
        actionDiv.style.display = 'block';
        noDataMsg.textContent = "No data available for this date.";

        // Only show upload button if date <= today
        const todayCommon = new Date().toISOString().split('T')[0];
        if (dateStr > todayCommon) {
            document.getElementById('btnUploadDaily').style.display = 'none';
            noDataMsg.textContent = "Cannot upload data for future dates.";
        } else {
            document.getElementById('btnUploadDaily').style.display = 'inline-block';
        }
    }
}

function closeDailyModal() {
    document.getElementById('dailyAnalysisModal').style.display = 'none';
    selectedDate = null; // Clear selected date so subsequent uploads are generic unless opened again
}

// Hook into initialization
// We need to call initCalendar() when DOM is loaded. 
// Existing code has:
// document.addEventListener('DOMContentLoaded', function () { ... initializeDashboard(); setupFileUpload(); });
// I can just append initCalendar() call here or modify the top.
// Since I can't easily modify the top with 'replace_file_content' (it's far away), 
// I'll add a self-executing check or just rely on the fact that script is loaded at the end.
// Better: Add it to the end of initializeDashboard inside this file? No, I can't easily edit inside function.
// Best: Just add a new event listener.
document.addEventListener('DOMContentLoaded', function () {
    initCalendar();
});
