import pandas as pd
from datetime import datetime
from .time_utils import calculate_working_hours, calculate_status
from .db_utils import get_settings

def parse_excel_file(file_path):
    """Parse Excel file and extract attendance records"""
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Normalize column names (case-insensitive)
        df.columns = df.columns.str.strip()
        
        # Map possible column names
        column_mapping = {
            'employee_id': ['Employee ID', 'employee_id', 'EmployeeID', 'empId', 'EmpID'],
            'employee_name': ['Employee Name', 'employee_name', 'EmployeeName', 'Name', 'name'],
            'date': ['Date', 'date', 'Attendance Date', 'AttendanceDate'],
            'punch_in': ['Punch In', 'punch_in', 'PunchIn', 'Check In', 'CheckIn'],
            'punch_out': ['Punch Out', 'punch_out', 'PunchOut', 'Check Out', 'CheckOut'],
            'break_start': ['Break Start', 'break_start', 'BreakStart', 'Lunch Start', 'LunchStart'],
            'break_end': ['Break End', 'break_end', 'BreakEnd', 'Lunch End', 'LunchEnd']
        }
        
        # Find matching columns
        col_map = {}
        for standard_name, possible_names in column_mapping.items():
            for col in df.columns:
                if col in possible_names:
                    col_map[standard_name] = col
                    break
        
        if 'employee_id' not in col_map or 'employee_name' not in col_map or 'date' not in col_map:
            raise ValueError("Excel file must contain Employee ID, Employee Name, and Date columns")
        
        settings = get_settings()
        records = []
        for _, row in df.iterrows():
            employee_id = str(row[col_map['employee_id']]).strip()
            employee_name = str(row[col_map['employee_name']]).strip()
            
            # Parse date
            date_value = row[col_map['date']]
            if isinstance(date_value, datetime):
                date_str = date_value.strftime('%Y-%m-%d')
            else:
                try:
                    date_obj = pd.to_datetime(date_value)
                    date_str = date_obj.strftime('%Y-%m-%d')
                except:
                    continue
            
            punch_in = str(row[col_map.get('punch_in', 'punch_in')]) if col_map.get('punch_in') and pd.notna(row[col_map.get('punch_in')]) else None
            punch_out = str(row[col_map.get('punch_out', 'punch_out')]) if col_map.get('punch_out') and pd.notna(row[col_map.get('punch_out')]) else None
            
            break_start = str(row[col_map.get('break_start', '')]) if col_map.get('break_start') and pd.notna(row[col_map.get('break_start')]) else None
            break_end = str(row[col_map.get('break_end', '')]) if col_map.get('break_end') and pd.notna(row[col_map.get('break_end')]) else None
            
            # Calculate working hours
            working_hours = calculate_working_hours(punch_in, punch_out, date_str)

            # Determine status
            status_result = calculate_status(punch_in, punch_out, working_hours, date_str, settings, break_start, break_end)
            
            # Get month and year
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
            
            records.append({
                'employee_id': employee_id,
                'employee_name': employee_name,
                'date': date_str,
                'punch_in_time': punch_in,
                'punch_out_time': punch_out,
                'working_hours': working_hours,
                'status': status_result['status'],
                'month': month,
                'year': year,
                'break_start_time': break_start,
                'break_end_time': break_end,
                'break_duration': status_result['break_duration'],
                'is_late': 1 if status_result['is_late'] else 0,
                'break_exceeded': 1 if status_result['break_exceeded'] else 0,
                'is_break_outside_window': 1 if status_result['is_break_outside_window'] else 0,
                'is_early_departure': 1 if status_result['is_early_departure'] else 0
            })
        
        return records
    except Exception as e:
        raise Exception(f"Failed to parse Excel file: {str(e)}")
