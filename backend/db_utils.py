import sqlite3
import os

# Database setup
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Create employees table
    c.execute('''CREATE TABLE IF NOT EXISTS employees
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  employee_id TEXT NOT NULL,
                  employee_name TEXT NOT NULL,
                  department TEXT,
                  designation TEXT,
                  email TEXT,
                  joining_date TEXT,
                  is_active INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(employee_id))''')
    
    # Create attendance_records table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  employee_id TEXT NOT NULL,
                  employee_name TEXT NOT NULL,
                  date TEXT NOT NULL,
                  punch_in_time TEXT,
                  punch_out_time TEXT,
                  working_hours REAL,
                  status TEXT,
                  month INTEGER,
                  year INTEGER,
                  notes TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(employee_id, date))''')
    
    # Create upload_history table
    c.execute('''CREATE TABLE IF NOT EXISTS upload_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  file_name TEXT NOT NULL,
                  file_path TEXT,
                  upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  records_processed INTEGER,
                  records_success INTEGER,
                  records_failed INTEGER,
                  status TEXT,
                  error_log TEXT)''')
    
    # Migration: Add new columns if they don't exist
    new_columns = [
        ('attendance_records', 'break_start_time', 'TEXT'),
        ('attendance_records', 'break_end_time', 'TEXT'),
        ('attendance_records', 'break_duration', 'REAL'),
        ('attendance_records', 'is_late', 'INTEGER DEFAULT 0'),
        ('attendance_records', 'break_exceeded', 'INTEGER DEFAULT 0'),
        ('attendance_records', 'is_break_outside_window', 'INTEGER DEFAULT 0'),
        ('attendance_records', 'is_early_departure', 'INTEGER DEFAULT 0'),
        ('upload_history', 'target_date', 'TEXT')
    ]
    
    for table, col, dtype in new_columns:
        try:
            c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {dtype}')
            print(f"Added column {col} to {table}")
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
    # Create settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY,
                  value TEXT)''')
                  
    # Insert default settings if not exist
    defaults = {
        'standard_start_time': '09:30',
        'standard_end_time': '18:30',
        'standard_break_start': '13:00',
        'standard_break_end': '14:00',
        'max_break_duration': '60',
        'half_day_time': '14:00'
    }
    
    for key, value in defaults.items():
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    conn.commit()
    conn.close()

def get_settings():
    """Get system settings from database"""
    defaults = {
        'standard_start_time': '09:30',
        'standard_end_time': '18:30',
        'standard_break_start': '13:00',
        'standard_break_end': '14:00',
        'max_break_duration': '60',
        'half_day_time': '14:00'
    }
    
    try:
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        c.execute('SELECT key, value FROM settings')
        settings = dict(c.fetchall())
        conn.close()
        
        # Merge with defaults
        return {**defaults, **settings}
    except:
        return defaults
