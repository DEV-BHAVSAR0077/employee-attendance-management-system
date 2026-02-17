import os
import json
import google.generativeai as genai
from datetime import datetime
import sqlite3
import hashlib

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

class GeminiReportService:
    def __init__(self, api_key=None):
        """
        Initialize Gemini API service
        Args:
            api_key: Google Gemini API key (if None, reads from environment)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Discover an available Gemini model (allow environment override)
            preferred_model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash-latest')
            self.model_name = self._discover_model(preferred_model)

            # Try to create a GenerativeModel object if the SDK supports it,
            # otherwise we'll call the top-level generate API with model name.
            try:
                if self.model_name:
                    try:
                        self.model = genai.GenerativeModel(self.model_name)
                    except Exception:
                        # Some SDK versions may not support GenerativeModel constructor
                        self.model = None
                else:
                    self.model = None
            except Exception:
                self.model = None
        else:
            self.model = None
            self.model_name = None
        
        # Cache directory for storing report summaries
        self.cache_dir = 'report_cache'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize usage tracking
        self.usage_db = 'gemini_usage.db'
        self._init_usage_db()
    
    def _init_usage_db(self):
        """Initialize database for tracking API usage"""
        conn = sqlite3.connect(self.usage_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS api_usage
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      report_type TEXT,
                      tokens_used INTEGER,
                      cached INTEGER DEFAULT 0)''')
        conn.commit()
        conn.close()
    
    def _get_cache_key(self, data_summary, report_type):
        """Generate cache key from data summary"""
        key_string = f"{report_type}_{json.dumps(data_summary, sort_keys=True)}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _discover_model(self, preferred=None):
        """Attempt to list available models and pick a suitable Gemini model.

        Returns a model name string (without a 'models/' prefix) or the
        preferred value if no discovery is possible.
        """
        preferred = preferred or os.getenv('GEMINI_MODEL')
        model_names = []
        try:
            # Try various SDK methods to list models (compatibility across versions)
            models = None
            if hasattr(genai, 'list_models'):
                models = genai.list_models()
            elif hasattr(genai, 'Models') and hasattr(genai.Models, 'list'):
                models = genai.Models.list()
            elif hasattr(genai, 'models') and hasattr(genai.models, 'list'):
                models = genai.models.list()

            if models:
                for m in models:
                    if isinstance(m, dict):
                        name = m.get('name') or m.get('model')
                    else:
                        name = getattr(m, 'name', None) or getattr(m, 'model', None) or str(m)
                    if name:
                        # Normalize names like 'models/gemini-1.5' -> 'gemini-1.5'
                        if name.startswith('models/'):
                            name = name.split('/', 1)[1]
                        model_names.append(name)
        except Exception:
            model_names = []

        # Prefer exactly preferred if available
        if preferred and preferred in model_names:
            return preferred

        # Try to match by prefix or keywords
        if preferred:
            pref_key = preferred.split('-')[0]
            for n in model_names:
                if pref_key and pref_key.lower() in n.lower():
                    return n

        # Pick any gemini model if available
        for n in model_names:
            if 'gemini' in n.lower():
                return n

        # Last resort: return the preferred string (may cause clearer error upstream)
        return preferred
    
    def _get_cached_report(self, cache_key):
        """Retrieve cached report if available"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            # Check if cache is less than 24 hours old
            cache_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if cache_age < 86400:  # 24 hours
                with open(cache_file, 'r') as f:
                    return json.load(f)
        return None
    
    def _save_to_cache(self, cache_key, report_data):
        """Save report to cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        with open(cache_file, 'w') as f:
            json.dump(report_data, f)
    
    def _track_usage(self, report_type, tokens_used, cached=False):
        """Track API usage in database"""
        conn = sqlite3.connect(self.usage_db)
        c = conn.cursor()
        c.execute('INSERT INTO api_usage (report_type, tokens_used, cached) VALUES (?, ?, ?)',
                  (report_type, tokens_used, 1 if cached else 0))
        conn.commit()
        conn.close()
    
    def get_usage_stats(self):
        """Get API usage statistics"""
        conn = sqlite3.connect(self.usage_db)
        c = conn.cursor()
        
        # Total tokens used today
        c.execute('''SELECT COALESCE(SUM(tokens_used), 0) 
                     FROM api_usage 
                     WHERE DATE(timestamp) = DATE('now')''')
        today_tokens = c.fetchone()[0]
        
        # Total tokens this month
        c.execute('''SELECT COALESCE(SUM(tokens_used), 0) 
                     FROM api_usage 
                     WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')''')
        month_tokens = c.fetchone()[0]
        
        # Cached vs non-cached requests
        c.execute('''SELECT cached, COUNT(*) 
                     FROM api_usage 
                     WHERE DATE(timestamp) = DATE('now')
                     GROUP BY cached''')
        cache_stats = dict(c.fetchall())
        
        conn.close()
        
        return {
            'today_tokens': today_tokens,
            'month_tokens': month_tokens,
            'today_cached': cache_stats.get(1, 0),
            'today_new': cache_stats.get(0, 0)
        }
    
    def _prepare_data_summary(self, db_path, start_date=None, end_date=None):
        """
        Prepare a concise summary of attendance data for AI analysis
        This reduces token usage by sending aggregated data instead of raw records
        """
        conn = sqlite3.connect(db_path)
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE date >= ?"
            params = [start_date]
        
        # Get summary statistics
        query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT employee_id) as total_employees,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
                SUM(CASE WHEN status = 'Leave' THEN 1 ELSE 0 END) as leave_count,
                AVG(working_hours) as avg_working_hours,
                MIN(working_hours) as min_working_hours,
                MAX(working_hours) as max_working_hours
            FROM attendance_records
            {date_filter}
        """
        
        stats = conn.execute(query, params).fetchone()
        
        # Get per-employee summary
        employee_query = f"""
            SELECT 
                employee_id,
                employee_name,
                COUNT(*) as total_days,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_days,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_days,
                AVG(working_hours) as avg_hours,
                MIN(date) as first_date,
                MAX(date) as last_date
            FROM attendance_records
            {date_filter}
            GROUP BY employee_id, employee_name
            ORDER BY absent_days DESC, avg_hours ASC
            LIMIT 20
        """
        
        employees = conn.execute(employee_query, params).fetchall()
        
        # Get daily trends (last 30 days or within date range)
        trend_query = f"""
            SELECT 
                date,
                COUNT(*) as records,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present,
                AVG(working_hours) as avg_hours
            FROM attendance_records
            {date_filter}
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """
        
        daily_trends = conn.execute(trend_query, params).fetchall()
        
        conn.close()
        
        return {
            'period': {
                'start_date': start_date or 'All time',
                'end_date': end_date or datetime.now().strftime('%Y-%m-%d')
            },
            'overall': {
                'total_records': stats[0],
                'total_employees': stats[1],
                'present_count': stats[2],
                'absent_count': stats[3],
                'leave_count': stats[4],
                'attendance_rate': round((stats[2] / stats[0] * 100) if stats[0] > 0 else 0, 2),
                'avg_working_hours': round(stats[5] or 0, 2),
                'min_working_hours': round(stats[6] or 0, 2),
                'max_working_hours': round(stats[7] or 0, 2)
            },
            'employee_summary': [
                {
                    'employee_id': emp[0],
                    'employee_name': emp[1],
                    'total_days': emp[2],
                    'present_days': emp[3],
                    'absent_days': emp[4],
                    'attendance_rate': round((emp[3] / emp[2] * 100) if emp[2] > 0 else 0, 2),
                    'avg_hours': round(emp[5] or 0, 2),
                    'date_range': f"{emp[6]} to {emp[7]}"
                }
                for emp in employees
            ],
            'daily_trends': [
                {
                    'date': trend[0],
                    'total_records': trend[1],
                    'present': trend[2],
                    'attendance_rate': round((trend[2] / trend[1] * 100) if trend[1] > 0 else 0, 2),
                    'avg_hours': round(trend[3] or 0, 2)
                }
                for trend in daily_trends
            ]
        }
    
    def generate_report(self, db_path='attendance.db', report_type='daily', 
                       start_date=None, end_date=None, force_regenerate=False):
        """
        Generate AI-powered attendance analysis report
        
        Args:
            db_path: Path to attendance database
            report_type: Type of report ('daily', 'weekly', 'monthly', 'custom')
            start_date: Start date for report (YYYY-MM-DD)
            end_date: End date for report (YYYY-MM-DD)
            force_regenerate: Skip cache and generate new report
            
        Returns:
            dict: Report data with sections and insights
        """
        if not self.model:
            return {
                'error': 'Gemini API key not configured',
                'message': 'Please configure GEMINI_API_KEY environment variable'
            }
        
        # Prepare data summary
        data_summary = self._prepare_data_summary(db_path, start_date, end_date)
        
        # Check cache
        cache_key = self._get_cache_key(data_summary, report_type)
        if not force_regenerate:
            cached_report = self._get_cached_report(cache_key)
            if cached_report:
                self._track_usage(report_type, 0, cached=True)
                cached_report['cached'] = True
                return cached_report
        
        # Prepare prompt for Gemini
        prompt = self._create_report_prompt(data_summary, report_type)
        
        try:
            # Generate report using Gemini (support multiple SDK versions)
            response_text = None

            if getattr(self, 'model', None) is not None and hasattr(self.model, 'generate_content'):
                response = self.model.generate_content(prompt)
            else:
                # Fallback to top-level generate API with model name
                if not getattr(self, 'model_name', None):
                    # try to list models to include in error
                    available = []
                    try:
                        if hasattr(genai, 'list_models'):
                            available = genai.list_models()
                        elif hasattr(genai, 'Models') and hasattr(genai.Models, 'list'):
                            available = genai.Models.list()
                        elif hasattr(genai, 'models') and hasattr(genai.models, 'list'):
                            available = genai.models.list()
                    except Exception:
                        available = []
                    return {
                        'error': 'No Gemini model available',
                        'message': 'Model not discovered. Set GEMINI_MODEL or check available models.',
                        'available_models': available
                    }

                try:
                    if hasattr(genai, 'generate'):
                        response = genai.generate(model=self.model_name, prompt=prompt)
                    elif hasattr(genai, 'generate_text'):
                        response = genai.generate_text(model=self.model_name, prompt=prompt)
                    else:
                        raise Exception('GenAI SDK does not expose a generate() entrypoint')
                except Exception as inner_e:
                    # Try to include available model list for better diagnosis
                    available = []
                    try:
                        if hasattr(genai, 'list_models'):
                            available = genai.list_models()
                        elif hasattr(genai, 'Models') and hasattr(genai.Models, 'list'):
                            available = genai.Models.list()
                        elif hasattr(genai, 'models') and hasattr(genai.models, 'list'):
                            available = genai.models.list()
                    except Exception:
                        available = []
                    return {
                        'error': str(inner_e),
                        'message': f"Failed to call generate() for model '{self.model_name}'",
                        'available_models': available
                    }

            # Extract text from response (support multiple response formats)
            try:
                if hasattr(response, 'text'):
                    response_text = response.text
                elif getattr(response, 'candidates', None):
                    cand = response.candidates[0]
                    response_text = getattr(cand, 'output', None) or getattr(cand, 'content', None) or str(cand)
                    if isinstance(response_text, list) and len(response_text) > 0 and hasattr(response_text[0], 'text'):
                        response_text = response_text[0].text
                    elif isinstance(response_text, list):
                        response_text = json.dumps(response_text)
                elif isinstance(response, dict):
                    # Look for common keys
                    if 'text' in response:
                        response_text = response['text']
                    elif 'candidates' in response and len(response['candidates']) > 0:
                        c = response['candidates'][0]
                        if isinstance(c, dict) and 'output' in c:
                            response_text = c['output']
                        else:
                            response_text = json.dumps(c)
                    else:
                        response_text = json.dumps(response)
                else:
                    response_text = str(response)
            except Exception:
                response_text = str(response)

            # Track token usage (approximate)
            tokens_used = len(prompt.split()) + len(response_text.split()) if response_text else len(prompt.split())
            self._track_usage(report_type, tokens_used, cached=False)

            # Parse response
            report_data = self._parse_gemini_response(response_text, data_summary)
            report_data['cached'] = False
            report_data['generated_at'] = datetime.now().isoformat()
            
            # Save to cache
            self._save_to_cache(cache_key, report_data)
            
            return report_data
            
        except Exception as e:
            return {
                'error': str(e),
                'message': 'Failed to generate report with Gemini API'
            }
    
    def _create_report_prompt(self, data_summary, report_type):
        """Create optimized prompt for Gemini API"""
        
        prompt = f"""You are an expert HR analytics consultant analyzing employee attendance data. 
Generate a comprehensive yet concise attendance report based on the following data.

REPORT TYPE: {report_type.upper()}
PERIOD: {data_summary['period']['start_date']} to {data_summary['period']['end_date']}

OVERALL STATISTICS:
- Total Records: {data_summary['overall']['total_records']}
- Total Employees: {data_summary['overall']['total_employees']}
- Attendance Rate: {data_summary['overall']['attendance_rate']}%
- Present: {data_summary['overall']['present_count']} | Absent: {data_summary['overall']['absent_count']} | Leave: {data_summary['overall']['leave_count']}
- Average Working Hours: {data_summary['overall']['avg_working_hours']}
- Working Hours Range: {data_summary['overall']['min_working_hours']} - {data_summary['overall']['max_working_hours']}

TOP EMPLOYEES (by attendance issues):
{json.dumps(data_summary['employee_summary'][:10], indent=2)}

RECENT DAILY TRENDS:
{json.dumps(data_summary['daily_trends'][:7], indent=2)}

Please provide a structured analysis with the following sections (use JSON format):

1. **executive_summary**: A 2-3 sentence overview of key findings
2. **key_metrics**: List 4-5 most important metrics with brief explanations
3. **attendance_analysis**: Detailed analysis of attendance patterns and trends
4. **employee_insights**: Insights about employee performance (highlight both concerns and commendations)
5. **recommendations**: 3-5 actionable recommendations for management
6. **trend_forecast**: Brief prediction about attendance trends
7. **alerts**: Any critical issues requiring immediate attention

Format your response as valid JSON with these exact keys. Be concise but insightful."""

        return prompt
    
    def _parse_gemini_response(self, response_text, data_summary):
        """Parse Gemini's response into structured report data"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                # Fallback to basic structure
                parsed = {
                    'executive_summary': response_text[:500],
                    'full_response': response_text
                }
            
            # Add data summary for context
            parsed['data_summary'] = data_summary
            
            return parsed
            
        except Exception as e:
            return {
                'executive_summary': 'Report generated successfully',
                'full_response': response_text,
                'data_summary': data_summary,
                'parse_error': str(e)
            }
