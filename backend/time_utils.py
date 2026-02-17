from datetime import datetime

# Constants for attendance rules
LATE_THRESHOLD_TIME = "10:00:00"  # 10:00 AM
HALF_DAY_HOURS = 5.0

def calculate_working_hours(punch_in, punch_out, date_str):
    """Calculate working hours from punch in/out times"""
    if not punch_in or not punch_out:
        return None
    
    try:
        # Parse time strings (support formats like "09:00", "9:00 AM", "09:00:00")
        def parse_time(time_str, date_str):
            time_str = str(time_str).strip()
            
            # Handle 12-hour format with AM/PM
            if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                try:
                    time_obj = datetime.strptime(time_str, '%I:%M %p')
                except ValueError:
                    time_obj = datetime.strptime(time_str, '%I:%M:%S %p')
            else:
                # Try 24-hour format
                if time_str.count(':') == 2:
                    time_obj = datetime.strptime(time_str, '%H:%M:%S')
                else:
                    time_obj = datetime.strptime(time_str, '%H:%M')
            
            # Combine with date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return datetime.combine(date_obj.date(), time_obj.time())
        
        punch_in_dt = parse_time(punch_in, date_str)
        punch_out_dt = parse_time(punch_out, date_str)
        
        # Calculate difference in hours
        diff = punch_out_dt - punch_in_dt
        hours = diff.total_seconds() / 3600
        
        return max(0, round(hours, 2))
    except Exception as e:
        print(f"Error calculating working hours: {e}")
        return None

def calculate_status(punch_in, punch_out, working_hours, date_str, settings, break_start=None, break_end=None):
    """Calculate attendance status and flags based on rules"""
    # Settings are now passed as an argument
    standard_start = settings.get('standard_start_time', '09:30')
    standard_end = settings.get('standard_end_time', '18:30')
    max_break = float(settings.get('max_break_duration', 60))
    std_break_start_str = settings.get('standard_break_start', '13:00')
    std_break_end_str = settings.get('standard_break_end', '14:00')
    half_day_time_str = settings.get('half_day_time', '14:00')
    
    result = {
        'status': 'Absent',
        'is_late': False,
        'break_duration': 0.0,
        'break_exceeded': False,
        'is_break_outside_window': False,
        'is_early_departure': False
    }
    
    if not punch_in:
        return result
    
    if not punch_out:
        result['status'] = 'Incomplete'
        # Can still check late
    else:
        result['status'] = 'Present'
        
    # Function to parse time
    def parse_time_simple(t_str):
        formats = ['%I:%M %p', '%I:%M:%S %p', '%H:%M:%S', '%H:%M']
        for fmt in formats:
            try:
                return datetime.strptime(str(t_str).strip(), fmt).time()
            except ValueError:
                continue
        return None

    in_time = parse_time_simple(punch_in)
    out_time = parse_time_simple(punch_out)
    half_day_threshold = datetime.strptime(half_day_time_str, '%H:%M').time()

    # Half Day Logic
    is_half_day = False
    
    # Condition 1: Total working hours < 5 (Legacy backup)
    if working_hours is not None and working_hours < HALF_DAY_HOURS:
        is_half_day = True
        
    # Condition 2: Leave before Half Day Time (Morning Shift leaving early)
    if out_time and out_time < half_day_threshold:
        is_half_day = True
        
    # Condition 3: Arrive after Half Day Time (Afternoon Shift arriving late)
    if in_time and in_time > half_day_threshold:
        is_half_day = True
        
    if is_half_day:
        result['status'] = 'Half Day'
        
    # Check for Late or Early Departure
    try:
        # Parse punch_in/out
        def parse_time(t_str):
            formats = ['%I:%M %p', '%I:%M:%S %p', '%H:%M:%S', '%H:%M']
            for fmt in formats:
                try:
                    return datetime.strptime(str(t_str).strip(), fmt).time()
                except ValueError:
                    continue
            return None

        in_time = parse_time(punch_in)
        out_time = parse_time(punch_out)
        
        if in_time:
            # Check Late
            try:
                start_threshold = datetime.strptime(standard_start, '%H:%M').time()
            except:
                start_threshold = datetime.strptime('09:30', '%H:%M').time()
            
            if in_time > start_threshold:
                result['is_late'] = True
                if result['status'] == 'Present':
                   result['status'] = 'Late'
        
        if out_time:
            # Check Early Departure
            try:
                end_threshold = datetime.strptime(standard_end, '%H:%M').time()
            except:
                end_threshold = datetime.strptime('18:30', '%H:%M').time()
            
            if out_time < end_threshold:
                 result['is_early_departure'] = True
            
    except Exception as e:
        print(f"Error checking late/early status: {e}")
    
    # Check Break
    if break_start and break_end:
        try:
            def parse_time_obj(t_str):
                for fmt in ['%I:%M %p', '%I:%M:%S %p', '%H:%M:%S', '%H:%M']:
                    try:
                        return datetime.strptime(str(t_str).strip(), fmt)
                    except ValueError:
                        continue
                return None

            bs = parse_time_obj(break_start)
            be = parse_time_obj(break_end)
            
            if bs and be:
                # Assuming break is on same day
                duration_mins = (be - bs).total_seconds() / 60
                result['break_duration'] = round(duration_mins, 2)
                
                if duration_mins > max_break:
                    result['break_exceeded'] = True
                
                # Check Window Violation
                try:
                     # We need to construct full datetimes for the standard window on the same date as the break
                     # But since bs/be might be just times or datetimes, let's normalize to time() objects
                     bs_time = bs.time()
                     be_time = be.time()
                     
                     std_bs = datetime.strptime(std_break_start_str, '%H:%M').time()
                     std_be = datetime.strptime(std_break_end_str, '%H:%M').time()
                     
                     # Simple logic: If Break Start is BEFORE Std Start OR Break End is AFTER Std End
                     if bs_time < std_bs or be_time > std_be:
                         result['is_break_outside_window'] = True
                         
                except Exception as e:
                     print(f"Error checking break window: {e}")
                    
        except Exception as e:
            print(f"Error calculating break: {e}")
            
    return result

def format_hours(decimal_hours):
    """Format decimal hours to Xh Ym string"""
    if decimal_hours is None:
        return ""
    
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    
    if minutes == 60:
        hours += 1
        minutes = 0
        
    if hours == 0 and minutes == 0:
        return "0h 0m"
        
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
        
    return " ".join(parts)
