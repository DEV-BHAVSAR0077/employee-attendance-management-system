// Reports Page JavaScript

let attendanceTrendChart = null;
let statusDistributionChart = null;

document.addEventListener('DOMContentLoaded', function () {
    setupDateFilters();
    loadReportData();
});

function setupDateFilters() {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    document.getElementById('reportEndDate').valueAsDate = today;
    document.getElementById('reportStartDate').valueAsDate = thirtyDaysAgo;
}

async function loadReportData() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;

    try {
        // Load statistics
        const statsResponse = await fetch(`/api/statistics?startDate=${startDate}&endDate=${endDate}`);
        const statsData = await statsResponse.json();
        updateReportStats(statsData);

        // Load detailed records for charts and summary
        const recordsResponse = await fetch(`/api/attendance/range?startDate=${startDate}&endDate=${endDate}`);
        const recordsData = await recordsResponse.json();

        if (recordsData.records) {
            updateCharts(recordsData.records);
            updateMonthlySummary(recordsData.records);
        }

        showToast('Report data updated successfully');
    } catch (error) {
        console.error('Error loading report data:', error);
        showToast('Failed to load report data', 'error');
    }
}

function updateReportStats(data) {
    // calculate days difference
    const startDate = new Date(document.getElementById('reportStartDate').value);
    const endDate = new Date(document.getElementById('reportEndDate').value);
    const diffTime = Math.abs(endDate - startDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;

    document.getElementById('reportTotalDays').textContent = diffDays;
    document.getElementById('reportAvgAttendance').textContent = (data.attendanceRate || 0) + '%';
    document.getElementById('reportAvgHours').textContent = formatHours(data.averageWorkingHours);
    document.getElementById('reportActiveEmployees').textContent = data.activeEmployees || data.totalEmployees || 0;
}

function updateCharts(records) {
    // Process data for charts
    const dateGroups = {};
    const statusCounts = { Present: 0, Absent: 0, Late: 0, HalfDay: 0 };

    records.forEach(record => {
        // Group by date
        const date = record.date.split('T')[0];
        if (!dateGroups[date]) dateGroups[date] = 0;
        if (record.status !== 'Absent') dateGroups[date]++;

        // Count statuses
        let status = record.status;
        if (status === 'Half Day') status = 'HalfDay';
        if (statusCounts[status] !== undefined) statusCounts[status]++;
        else if (status.includes('Late')) statusCounts['Late']++;
    });

    // Update Trend Chart
    const sortedDates = Object.keys(dateGroups).sort();
    const attendanceCounts = sortedDates.map(date => dateGroups[date]);

    updateTrendChart(sortedDates, attendanceCounts);
    updateStatusChart(statusCounts);
}

function updateTrendChart(labels, data) {
    const ctx = document.getElementById('attendanceTrendChart');
    if (!ctx) return;

    if (attendanceTrendChart) {
        attendanceTrendChart.destroy();
    }

    attendanceTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Present Employees',
                data: data,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function updateStatusChart(counts) {
    const ctx = document.getElementById('statusDistributionChart');
    if (!ctx) return;

    if (statusDistributionChart) {
        statusDistributionChart.destroy();
    }

    statusDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Present', 'Absent', 'Late', 'Half Day'],
            datasets: [{
                data: [counts.Present, counts.Absent, counts.Late, counts.HalfDay],
                backgroundColor: [
                    '#10b981', // Present - Green
                    '#ef4444', // Absent - Red
                    '#f59e0b', // Late - Amber
                    '#3b82f6'  // Half Day - Blue
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

function updateMonthlySummary(records) {
    const tbody = document.getElementById('monthlySummaryBody');
    const monthlyData = {};

    records.forEach(record => {
        const date = new Date(record.date);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        const monthName = date.toLocaleString('default', { month: 'long', year: 'numeric' });

        if (!monthlyData[monthKey]) {
            monthlyData[monthKey] = {
                name: monthName,
                total: 0,
                present: 0,
                absent: 0,
                late: 0
            };
        }

        monthlyData[monthKey].total++;
        if (record.status === 'Present' || record.status === 'Half Day') monthlyData[monthKey].present++;
        if (record.status === 'Absent') monthlyData[monthKey].absent++;
        if (record.status.includes('Late')) monthlyData[monthKey].late++;
    });

    const sortedMonths = Object.keys(monthlyData).sort().reverse();

    if (sortedMonths.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No data available</td></tr>';
        return;
    }

    tbody.innerHTML = sortedMonths.map(key => {
        const data = monthlyData[key];
        const rate = data.total > 0 ? Math.round((data.present / data.total) * 100) : 0;

        return `
            <tr>
                <td>${data.name}</td>
                <td>${data.total}</td>
                <td>${data.present}</td>
                <td>${data.absent}</td>
                <td>${data.late}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="mr-2">${rate}%</span>
                        <div class="progress" style="height: 6px; width: 60px; background: #e5e7eb; border-radius: 3px; margin-left: 8px;">
                            <div class="progress-bar" style="width: ${rate}%; background: ${rate >= 90 ? '#10b981' : rate >= 75 ? '#f59e0b' : '#ef4444'}; height: 100%; border-radius: 3px;"></div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function exportReport() {

    // Let's implement a simple CSV export for the current view
    showToast('Exporting data...', 'info');

    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;

    // We can use the generic export endpoint if we modify it, but for now let's just use the month of the end date
    const date = new Date(endDate);
    const month = date.getMonth() + 1;
    const year = date.getFullYear();

    window.location.href = `/api/export/excel?month=${month}&year=${year}`;
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

// AI Report Generation
async function generateAIReport() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;

    if (!startDate || !endDate) {
        showToast('Please select both start and end dates', 'error');
        return;
    }

    // Show loading state
    const button = event.target.closest('button');
    const originalHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating AI Report...';

    try {
        showToast('Generating AI-powered report... This may take 5-10 seconds', 'info');

        const response = await fetch('/api/gemini/download-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reportType: 'custom',
                startDate: startDate,
                endDate: endDate
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to generate AI report');
        }

        // Download the PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `attendance_ai_report_${startDate}_to_${endDate}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showToast('AI report generated and downloaded successfully!', 'success');

    } catch (error) {
        console.error('Error generating AI report:', error);
        showToast(error.message || 'Failed to generate AI report. Please check your API configuration.', 'error');
    } finally {
        // Restore button state
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}
