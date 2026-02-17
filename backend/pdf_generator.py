"""
Enhanced PDF Report Generator for Attendance Analysis
Generates professional, visually appealing PDF reports with improved readability
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.platypus import Image as RLImage, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import io
import json
import re
from .time_utils import format_hours

class AttendanceReportPDF:
    """Enhanced PDF Report Generator with modern design"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.primary_color = colors.HexColor('#2563eb')  # Modern blue
        self.success_color = colors.HexColor('#10b981')  # Green
        self.warning_color = colors.HexColor('#f59e0b')  # Orange
        self.danger_color = colors.HexColor('#ef4444')   # Red
        self.dark_text = colors.HexColor('#1f2937')
        self.light_bg = colors.HexColor('#f9fafb')
    
    def _ensure_string(self, value):
        """Convert any data type to string safe for Paragraph"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, dict)):
            return json.dumps(value, indent=2) if isinstance(value, dict) else '\n'.join(str(item) for item in value)
        return str(value)
    
    def _setup_custom_styles(self):
        """Setup enhanced custom paragraph styles with modern design"""
        
        # Helper function to safely add styles
        def add_style_if_not_exists(style):
            if style.name not in self.styles:
                self.styles.add(style)
        
        # Main Title - Large and bold
        add_style_if_not_exists(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=10,
            spaceBefore=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=34
        ))
        
        # Subtitle
        add_style_if_not_exists(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica',
            leading=16
        ))
        
        # Section Header - Eye-catching
        add_style_if_not_exists(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            spaceBefore=15,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#3b82f6'),
            borderWidth=0,
            borderPadding=8,
            leading=20,
            leftIndent=0
        ))
        
        # Subsection Header
        add_style_if_not_exists(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=colors.HexColor('#374151'),
            spaceAfter=10,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            leading=16
        ))
        
        # Custom Body text - Readable (using unique name to avoid conflict)
        add_style_if_not_exists(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14,
            fontName='Helvetica'
        ))
        
        # Highlight box - Information
        add_style_if_not_exists(ParagraphStyle(
            name='HighlightBox',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1e40af'),
            backColor=colors.HexColor('#eff6ff'),
            borderColor=colors.HexColor('#3b82f6'),
            borderWidth=1,
            borderPadding=10,
            borderRadius=4,
            spaceAfter=12,
            leading=14
        ))
        
        # Success message
        add_style_if_not_exists(ParagraphStyle(
            name='SuccessBox',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#065f46'),
            backColor=colors.HexColor('#d1fae5'),
            borderColor=colors.HexColor('#10b981'),
            borderWidth=1,
            borderPadding=12,
            spaceAfter=12,
            leading=15,
            fontName='Helvetica'
        ))
        
        # Warning message
        add_style_if_not_exists(ParagraphStyle(
            name='WarningBox',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#92400e'),
            backColor=colors.HexColor('#fef3c7'),
            borderColor=colors.HexColor('#f59e0b'),
            borderWidth=1,
            borderPadding=12,
            spaceAfter=12,
            leading=15,
            fontName='Helvetica-Bold'
        ))
        
        # Alert/Danger message
        add_style_if_not_exists(ParagraphStyle(
            name='AlertBox',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#991b1b'),
            backColor=colors.HexColor('#fee2e2'),
            borderColor=colors.HexColor('#ef4444'),
            borderWidth=2,
            borderPadding=12,
            spaceAfter=12,
            leading=15,
            fontName='Helvetica-Bold'
        ))
        
        # Bullet point style
        add_style_if_not_exists(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            leftIndent=20,
            spaceAfter=6,
            leading=13,
            bulletIndent=10
        ))
        
        # Caption style
        add_style_if_not_exists(ParagraphStyle(
            name='Caption',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER,
            spaceAfter=5,
            italic=True
        ))
    
    def _create_header_footer(self, canvas, doc):
        """Create modern header and footer"""
        canvas.saveState()
        
        # Header with colored bar
        canvas.setFillColor(colors.HexColor('#1e40af'))
        canvas.rect(0, letter[1] - 0.6*inch, letter[0], 0.6*inch, fill=1, stroke=0)
        
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 14)
        canvas.drawString(inch, letter[1] - 0.42*inch, "Attendance Analytics Report")
        
        # Footer
        canvas.setFillColor(colors.HexColor('#e5e7eb'))
        canvas.rect(0, 0, letter[0], 0.5*inch, fill=1, stroke=0)
        
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6b7280'))
        canvas.drawString(inch, 0.25*inch, f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        canvas.drawRightString(letter[0] - inch, 0.25*inch, f"Page {doc.page}")
        
        canvas.restoreState()
    
    def _create_stat_card(self, title, value, subtitle="", icon="", status="normal"):
        """Create a modern statistic card"""
        # Determine colors based on status
        if status == "success":
            bg_color = colors.HexColor('#d1fae5')
            border_color = colors.HexColor('#10b981')
            text_color = colors.HexColor('#065f46')
        elif status == "warning":
            bg_color = colors.HexColor('#fef3c7')
            border_color = colors.HexColor('#f59e0b')
            text_color = colors.HexColor('#92400e')
        elif status == "danger":
            bg_color = colors.HexColor('#fee2e2')
            border_color = colors.HexColor('#ef4444')
            text_color = colors.HexColor('#991b1b')
        else:
            bg_color = colors.HexColor('#eff6ff')
            border_color = colors.HexColor('#3b82f6')
            text_color = colors.HexColor('#1e40af')
        
        # Create icon if provided
        icon_text = f"{icon} " if icon else ""
        
        data = [
            [f"{icon_text}{title}"],
            [str(value)]
        ]
        if subtitle:
            data.append([subtitle])
        
        table = Table(data, colWidths=[2.05*inch], rowHeights=[0.35*inch, 0.45*inch, 0.3*inch if subtitle else None])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), border_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 18),
            ('TEXTCOLOR', (0, 1), (-1, 1), text_color),
            ('BACKGROUND', (0, 1), (-1, -1), bg_color),
            ('FONTSIZE', (0, 2), (-1, -1), 8),
            ('TEXTCOLOR', (0, 2), (-1, -1), colors.HexColor('#6b7280')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 2, border_color),
        ]))
        
        return table
    
    def _create_enhanced_charts(self, data_summary):
        """Create enhanced, modern visualizations"""
        fig = plt.figure(figsize=(12, 5))
        
        # Set modern style
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Pie chart for attendance distribution
        ax1 = plt.subplot(1, 2, 1)
        overall = data_summary['overall']
        
        labels = ['Present', 'Absent', 'Leave']
        sizes = [
            overall.get('present_count', 0),
            overall.get('absent_count', 0),
            overall.get('leave_count', 0)
        ]
        colors_pie = ['#10b981', '#ef4444', '#f59e0b']
        explode = (0.05, 0.05, 0.05)
        
        wedges, texts, autotexts = ax1.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%',
            colors=colors_pie, 
            startangle=90,
            explode=explode,
            shadow=True,
            textprops={'fontsize': 10, 'weight': 'bold'}
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)
            autotext.set_weight('bold')
        
        ax1.set_title('Attendance Distribution', fontsize=13, fontweight='bold', pad=20)
        
        # Bar chart for daily trends
        ax2 = plt.subplot(1, 2, 2)
        if 'daily_trends' in data_summary and data_summary['daily_trends']:
            trends = data_summary['daily_trends'][:10]
            dates = [t['date'][-5:] for t in trends]
            attendance_rates = [t['attendance_rate'] for t in trends]
            
            # Color bars based on attendance rate
            bar_colors = []
            for rate in attendance_rates:
                if rate >= 80:
                    bar_colors.append('#10b981')  # Green
                elif rate >= 60:
                    bar_colors.append('#f59e0b')  # Orange
                else:
                    bar_colors.append('#ef4444')  # Red
            
            bars = ax2.bar(dates, attendance_rates, color=bar_colors, edgecolor='#374151', linewidth=1.5)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.0f}%',
                        ha='center', va='bottom', fontsize=8, fontweight='bold')
            
            # Add target line at 80%
            ax2.axhline(y=80, color='#6b7280', linestyle='--', linewidth=2, alpha=0.7, label='Target (80%)')
            
            ax2.set_xlabel('Date', fontsize=10, fontweight='bold')
            ax2.set_ylabel('Attendance Rate (%)', fontsize=10, fontweight='bold')
            ax2.set_title('Daily Attendance Trends', fontsize=13, fontweight='bold', pad=20)
            ax2.set_ylim([0, 105])
            ax2.legend(loc='lower right', fontsize=8)
            ax2.grid(axis='y', alpha=0.3)
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight', facecolor='white')
        img_buffer.seek(0)
        plt.close()
        
        return img_buffer
    
    def _parse_and_format_text(self, text, base_style):
        """Parse text with basic markdown and return formatted paragraphs"""
        if not text:
            return []
        
        paragraphs = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for bold markers
            # Use regex to replace pairs of ** with <b> and </b>
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            
            # Check for bullet points
            if line.startswith('•') or line.startswith('-'):
                paragraphs.append(Paragraph(f"• {line[1:].strip()}", self.styles['BulletPoint']))
            elif line.startswith('#'):
                # Header
                paragraphs.append(Paragraph(line.replace('#', '').strip(), self.styles['SubsectionHeader']))
            else:
                paragraphs.append(Paragraph(line, base_style))
        
        return paragraphs
    
    def generate_pdf(self, report_data, output_path=None):
        """
        Generate enhanced PDF report
        
        Args:
            report_data: Dictionary containing report sections from Gemini
            output_path: Path to save PDF (if None, returns BytesIO)
            
        Returns:
            BytesIO or str: PDF content or file path
        """
        # Create PDF buffer
        if output_path:
            buffer = output_path
        else:
            buffer = BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.8*inch,
            bottomMargin=0.7*inch
        )
        
        # Container for PDF elements
        story = []
        
        # === COVER PAGE ===
        story.append(Spacer(1, 0.3*inch))
        
        # Title
        title = Paragraph("Attendance Analytics Report", self.styles['MainTitle'])
        story.append(title)
        story.append(Spacer(1, 0.05*inch))
        
        # Report metadata
        period = report_data.get('data_summary', {}).get('period', {})
        subtitle_text = f"""
        Reporting Period: {period.get('start_date', 'N/A')} to {period.get('end_date', 'N/A')}<br/>
        Generated on {datetime.now().strftime('%B %d, %Y')}
        """
        story.append(Paragraph(subtitle_text, self.styles['Subtitle']))
        story.append(Spacer(1, 0.15*inch))
        
        # Divider line
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3b82f6'), 
                               spaceAfter=15, spaceBefore=5))
        
        # === EXECUTIVE SUMMARY ===
        if 'executive_summary' in report_data:
            story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
            summary_text = self._ensure_string(report_data['executive_summary'])
            story.append(Paragraph(summary_text, self.styles['HighlightBox']))
            story.append(Spacer(1, 0.15*inch))
        
        # === KEY METRICS DASHBOARD ===
        data_summary = report_data.get('data_summary', {})
        if 'overall' in data_summary:
            story.append(Paragraph("Key Performance Indicators", self.styles['SectionHeader']))
            story.append(Spacer(1, 0.1*inch))
            
            overall = data_summary['overall']
            attendance_rate = overall.get('attendance_rate', 0)
            
            # Determine status for attendance rate
            if attendance_rate >= 90:
                att_status = "success"
            elif attendance_rate >= 75:
                att_status = "warning"
            else:
                att_status = "danger"
            
            # Create stat cards - ROW 1
            card1 = self._create_stat_card(
                "Total Employees",
                overall.get('total_employees', 0),
                "Active Staff",
                "",
                "normal"
            )
            card2 = self._create_stat_card(
                "Attendance Rate",
                f"{attendance_rate}%",
                f"{overall.get('present_count', 0)} / {overall.get('total_records', 0)} days",
                "",
                att_status
            )
            card3 = self._create_stat_card(
                "Avg Working Hours",
                format_hours(overall.get('avg_working_hours', 0)),
                f"Range: {format_hours(overall.get('min_working_hours', 0))} - {format_hours(overall.get('max_working_hours', 0))}",
                "",
                "normal"
            )
            
            # Create table for row 1
            stats_row1_data = [[card1, card2, card3]]
            stats_table1 = Table(stats_row1_data, colWidths=[2.1*inch, 2.1*inch, 2.1*inch], spaceBefore=0, spaceAfter=0)
            stats_table1.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            story.append(stats_table1)
            story.append(Spacer(1, 0.12*inch))
            
            # Calculate absent metrics
            absent_days = overall.get('absent_count', 0)
            total_records = overall.get('total_records', 1)
            absent_pct = (absent_days / total_records * 100) if total_records > 0 else 0
            absent_status = "danger" if absent_pct > 15 else ("warning" if absent_pct > 10 else "success")
            
            # Create stat cards - ROW 2
            card4 = self._create_stat_card(
                "Absent Days",
                absent_days,
                f"{absent_pct:.1f}% of total",
                "",
                absent_status
            )
            card5 = self._create_stat_card(
                "Leave Days",
                overall.get('leave_count', 0),
                "Approved absences",
                "",
                "normal"
            )
            card6 = self._create_stat_card(
                "Total Records",
                overall.get('total_records', 0),
                "Days analyzed",
                "",
                "normal"
            )
            
            # Create table for row 2
            stats_row2_data = [[card4, card5, card6]]
            stats_table2 = Table(stats_row2_data, colWidths=[2.1*inch, 2.1*inch, 2.1*inch], spaceBefore=0, spaceAfter=0)
            stats_table2.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            story.append(stats_table2)
            story.append(Spacer(1, 0.15*inch))
        
        # === VISUALIZATIONS ===
        # Use KeepTogether to ensure title and chart stay on same page
        viz_elements = []
        viz_elements.append(Paragraph("Visual Analysis", self.styles['SectionHeader']))
        
        try:
            chart_buffer = self._create_enhanced_charts(data_summary)
            chart_img = RLImage(chart_buffer, width=6.5*inch, height=2.7*inch)
            viz_elements.append(chart_img)
            viz_elements.append(Spacer(1, 0.03*inch))
            viz_elements.append(Paragraph("Figure 1: Attendance patterns and daily trends", self.styles['Caption']))
            viz_elements.append(Spacer(1, 0.15*inch))
        except Exception as e:
            print(f"Chart generation error: {e}")
            viz_elements.append(Paragraph(f"[Chart generation error: {str(e)}]", self.styles['Caption']))
            viz_elements.append(Spacer(1, 0.1*inch))
            
        story.append(KeepTogether(viz_elements))
        
        # === DETAILED ANALYSIS ===
        if 'attendance_analysis' in report_data:
            story.append(Paragraph("Detailed Attendance Analysis", self.styles['SectionHeader']))
            analysis_text = self._ensure_string(report_data['attendance_analysis'])
            
            # Split into paragraphs and format
            analysis_paras = self._parse_and_format_text(analysis_text, self.styles['CustomBodyText'])
            for para in analysis_paras:
                story.append(para)
            
            story.append(Spacer(1, 0.15*inch))
        
        # === EMPLOYEE INSIGHTS ===
        if 'employee_insights' in report_data:
            insights_elements = []
            insights_elements.append(Paragraph("Employee Performance Insights", self.styles['SectionHeader']))
            
            insights_data = report_data['employee_insights']
            if isinstance(insights_data, dict):
                # Handle structured dictionary (e.g., concerns, commendations)
                for key, value in insights_data.items():
                    # Format key as subheader (e.g., "concerns" -> "Concerns")
                    formatted_key = key.replace('_', ' ').title()
                    insights_elements.append(Paragraph(f"<b>{formatted_key}:</b>", self.styles['CustomBodyText']))
                    
                    # Format value
                    val_text = self._ensure_string(value)
                    val_paras = self._parse_and_format_text(val_text, self.styles['CustomBodyText'])
                    for para in val_paras:
                        insights_elements.append(para)
                    
                    insights_elements.append(Spacer(1, 0.05*inch))
            else:
                # Handle plain text or other formats
                insights_text = self._ensure_string(insights_data)
                insights_paras = self._parse_and_format_text(insights_text, self.styles['CustomBodyText'])
                for para in insights_paras:
                    insights_elements.append(para)
            
            insights_elements.append(Spacer(1, 0.15*inch))
            
            # Use KeepTogether to prevent splitting header from content
            story.append(KeepTogether(insights_elements))
        
        # === TOP PERFORMERS & CONCERNS TABLE ===
        if 'employee_summary' in data_summary and data_summary['employee_summary']:
            # Create table elements that should stay together
            table_elements = []
            
            table_elements.append(Paragraph("Employee Attendance Details", self.styles['SectionHeader']))
            table_elements.append(Spacer(1, 0.1*inch))
            
            # Header row with icons
            emp_data = [[
                'Employee ID',
                'Name',
                'Attendance %',
                'Avg Hours',
                'Absent Days'
            ]]
            
            # Process employee data
            for emp in data_summary['employee_summary'][:15]:  # Show top 15
                att_rate = emp.get('attendance_rate', 0)
                
                emp_data.append([
                    emp.get('employee_id', 'N/A'),
                    emp.get('employee_name', 'N/A')[:25],
                    f"{att_rate}%",
                    format_hours(emp.get('avg_hours', 0)),
                    str(emp.get('absent_days', 0))
                ])
            
            # Create table
            # Adjusted widths to fill the space left by Status column
            emp_table = Table(emp_data, colWidths=[1.1*inch, 2.4*inch, 1.2*inch, 1.1*inch, 1.1*inch], 
                            repeatRows=1)  # Repeat header on new pages
            emp_table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                
                # Body styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                ('PADDING', (0, 0), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            table_elements.append(emp_table)
            table_elements.append(Spacer(1, 0.05*inch))
            table_elements.append(Paragraph(
                f"Table 1: Top {min(15, len(data_summary['employee_summary']))} employees by attendance record", 
                self.styles['Caption']
            ))
            
            # Use KeepTogether to prevent splitting header and table
            story.append(KeepTogether(table_elements))
            story.append(Spacer(1, 0.15*inch))
        
        # === RECOMMENDATIONS ===
        if 'recommendations' in report_data:
            rec_elements = []
            rec_elements.append(Paragraph("Strategic Recommendations", self.styles['SectionHeader']))
            
            recommendations = report_data['recommendations']
            if isinstance(recommendations, list):
                for i, rec in enumerate(recommendations, 1):
                    rec_text = self._ensure_string(rec)
                    # Remove markdown bold
                    rec_text = rec_text.replace('**', '')
                    rec_elements.append(Paragraph(
                        f"<b>{i}.</b> {rec_text}",
                        self.styles['BulletPoint']
                    ))
            else:
                rec_paras = self._parse_and_format_text(
                    self._ensure_string(recommendations),
                    self.styles['CustomBodyText']
                )
                for para in rec_paras:
                    rec_elements.append(para)
            
            rec_elements.append(Spacer(1, 0.15*inch))
            story.append(KeepTogether(rec_elements))
        
        # === CRITICAL ALERTS ===
        # === CRITICAL ALERTS ===
        if 'alerts' in report_data and report_data['alerts']:
            alert_elements = []
            alert_elements.append(Paragraph("Critical Alerts & Action Items", self.styles['SectionHeader']))
            
            alerts = report_data['alerts']
            if isinstance(alerts, list):
                for alert in alerts:
                    alert_text = self._ensure_string(alert)
                    # Remove markdown
                    alert_text = alert_text.replace('**', '').replace('*', '')
                    alert_elements.append(Paragraph(f"• {alert_text}", self.styles['AlertBox']))
            else:
                alert_text = self._ensure_string(alerts).replace('**', '').replace('*', '')
                alert_elements.append(Paragraph(alert_text, self.styles['AlertBox']))
            
            alert_elements.append(Spacer(1, 0.15*inch))
            story.append(KeepTogether(alert_elements))
        
        # === TREND FORECAST ===
        if 'trend_forecast' in report_data:
            forecast_elements = []
            forecast_elements.append(Paragraph("Trend Forecast & Outlook", self.styles['SectionHeader']))
            forecast_text = self._ensure_string(report_data['trend_forecast'])
            
            forecast_paras = self._parse_and_format_text(forecast_text, self.styles['CustomBodyText'])
            for para in forecast_paras:
                forecast_elements.append(para)
            
            forecast_elements.append(Spacer(1, 0.15*inch))
            story.append(KeepTogether(forecast_elements))
        
        # === FOOTER NOTE ===
        story.append(Spacer(1, 0.2*inch))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#d1d5db')))
        story.append(Spacer(1, 0.1*inch))
        
        footer_note = """
        <i>This report was automatically generated using AI-powered analytics. 
        The insights and recommendations are based on the attendance data provided for the specified period. 
        For questions or clarifications, please contact your HR department.</i>
        """
        story.append(Paragraph(footer_note, self.styles['Caption']))
        
        # Build PDF
        doc.build(story, onFirstPage=self._create_header_footer, 
                 onLaterPages=self._create_header_footer)
        
        if output_path:
            return output_path
        else:
            buffer.seek(0)
            return buffer