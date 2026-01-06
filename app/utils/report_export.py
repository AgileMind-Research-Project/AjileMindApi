"""
Report Export Utility

Export reports to PDF and DOCX formats with template styling.
"""

from typing import Dict, Any, Optional
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.core.logger import logger
import json


class ReportExporter:
    """Export reports to various formats"""
    
    @staticmethod
    def _parse_color(color_str: str) -> tuple:
        """Parse hex color to RGB tuple"""
        try:
            color_str = color_str.lstrip('#')
            return tuple(int(color_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        except:
            return (0, 0, 0)  # Default to black
    
    @staticmethod
    def _parse_color_docx(color_str: str) -> RGBColor:
        """Parse hex color to RGBColor for docx"""
        try:
            color_str = color_str.lstrip('#')
            r, g, b = tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4))
            return RGBColor(r, g, b)
        except:
            return RGBColor(0, 0, 0)  # Default to black
    
    @staticmethod
    def export_to_pdf(
        report_data: Dict[str, Any],
        report_type: str,
        template_config: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Export report to PDF format.
        
        Args:
            report_data: Report content dictionary
            report_type: Type of report (daily_standup, sprint_meeting, retrospective)
            template_config: Optional template configuration with header, footer, styles
        
        Returns:
            PDF file as bytes
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch)
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Apply custom styles if provided
            if template_config and 'styles' in template_config:
                custom_styles = template_config['styles']
                
                # Update heading style
                if 'heading_color' in custom_styles:
                    color = ReportExporter._parse_color(custom_styles['heading_color'])
                    styles['Heading1'].textColor = colors.Color(*color)
                
                if 'font_size' in custom_styles:
                    styles['Normal'].fontSize = int(custom_styles['font_size'])
            
            story = []
            
            # Add header if provided
            if template_config and 'header_content' in template_config:
                header = template_config['header_content']
                if header.get('text'):
                    alignment = TA_CENTER if header.get('alignment') == 'center' else TA_LEFT
                    header_style = ParagraphStyle(
                        'CustomHeader',
                        parent=styles['Heading1'],
                        alignment=alignment,
                        fontSize=int(header.get('font_size', 14)),
                        textColor=colors.Color(*ReportExporter._parse_color(header.get('color', '#000000')))
                    )
                    story.append(Paragraph(header['text'], header_style))
                    story.append(Spacer(1, 0.3*inch))
            
            # Add report title
            title = f"{report_type.replace('_', ' ').title()} Report"
            story.append(Paragraph(title, styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))
            
            # Add report content based on type
            if report_type == 'daily_standup':
                ReportExporter._add_daily_standup_content(story, report_data, styles)
            elif report_type == 'sprint_meeting':
                ReportExporter._add_sprint_meeting_content(story, report_data, styles)
            elif report_type == 'retrospective':
                ReportExporter._add_retrospective_content(story, report_data, styles)
            
            # Add footer if provided
            if template_config and 'footer_content' in template_config:
                footer = template_config['footer_content']
                if footer.get('text'):
                    story.append(Spacer(1, 0.5*inch))
                    alignment = TA_CENTER if footer.get('alignment') == 'center' else TA_LEFT
                    footer_style = ParagraphStyle(
                        'CustomFooter',
                        parent=styles['Normal'],
                        alignment=alignment,
                        fontSize=int(footer.get('font_size', 10)),
                        textColor=colors.Color(*ReportExporter._parse_color(footer.get('color', '#666666')))
                    )
                    story.append(Paragraph(footer['text'], footer_style))
            
            # Build PDF
            doc.build(story)
            
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            return pdf_bytes
        
        except Exception as e:
            logger.error(f"Error exporting report to PDF: {e}")
            raise
    
    @staticmethod
    def _add_daily_standup_content(story, data, styles):
        """Add daily standup content to PDF"""
        # Yesterday's work
        story.append(Paragraph("Yesterday's Work:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('yesterday_work', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Today's plan
        story.append(Paragraph("Today's Plan:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('today_plan', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Blockers
        story.append(Paragraph("Blockers & Issues:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        blockers = data.get('blockers', [])
        if blockers:
            for item in blockers:
                story.append(Paragraph(f"• {item}", styles['Normal']))
        else:
            story.append(Paragraph("No blockers reported.", styles['Normal']))
    
    @staticmethod
    def _add_sprint_meeting_content(story, data, styles):
        """Add sprint meeting content to PDF"""
        # Sprint goals
        story.append(Paragraph("Sprint Goals:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('sprint_goals', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Progress summary
        story.append(Paragraph("Progress Summary:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('progress_summary', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Issues & risks
        story.append(Paragraph("Issues & Risks:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('issues_risks', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Action items
        story.append(Paragraph("Action Items:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        action_items = data.get('action_items', [])
        if action_items:
            for item in action_items:
                assignee = item.get('assignee', 'Unassigned')
                due_date = item.get('due_date', 'No deadline')
                story.append(Paragraph(
                    f"• {item['action']} (Assignee: {assignee}, Due: {due_date})",
                    styles['Normal']
                ))
        else:
            story.append(Paragraph("No action items.", styles['Normal']))
    
    @staticmethod
    def _add_retrospective_content(story, data, styles):
        """Add retrospective content to PDF"""
        # What went well
        story.append(Paragraph("What Went Well:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('what_went_well', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # What didn't go well
        story.append(Paragraph("What Didn't Go Well:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('what_didnt_go_well', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Improvements
        story.append(Paragraph("Improvements:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('improvements', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Action points
        story.append(Paragraph("Action Points:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        for item in data.get('action_points', []):
            story.append(Paragraph(f"• {item}", styles['Normal']))
    
    @staticmethod
    def export_to_docx(
        report_data: Dict[str, Any],
        report_type: str,
        template_config: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Export report to DOCX format.
        
        Args:
            report_data: Report content dictionary
            report_type: Type of report
            template_config: Optional template configuration
        
        Returns:
            DOCX file as bytes
        """
        try:
            doc = Document()
            
            # Add header if provided
            if template_config and 'header_content' in template_config:
                header = template_config['header_content']
                if header.get('text'):
                    p = doc.add_paragraph(header['text'])
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if header.get('alignment') == 'center' else WD_ALIGN_PARAGRAPH.LEFT
                    p.runs[0].font.size = Pt(int(header.get('font_size', 14)))
                    p.runs[0].font.color.rgb = ReportExporter._parse_color_docx(header.get('color', '#000000'))
                    doc.add_paragraph()
            
            # Add title
            title = doc.add_heading(f"{report_type.replace('_', ' ').title()} Report", 0)
            
            # Add report content based on type
            if report_type == 'daily_standup':
                ReportExporter._add_daily_standup_content_docx(doc, report_data)
            elif report_type == 'sprint_meeting':
                ReportExporter._add_sprint_meeting_content_docx(doc, report_data)
            elif report_type == 'retrospective':
                ReportExporter._add_retrospective_content_docx(doc, report_data)
            
            # Add footer if provided
            if template_config and 'footer_content' in template_config:
                footer = template_config['footer_content']
                if footer.get('text'):
                    doc.add_paragraph()
                    p = doc.add_paragraph(footer['text'])
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if footer.get('alignment') == 'center' else WD_ALIGN_PARAGRAPH.LEFT
                    p.runs[0].font.size = Pt(int(footer.get('font_size', 10)))
                    p.runs[0].font.color.rgb = ReportExporter._parse_color_docx(footer.get('color', '#666666'))
            
            # Save to bytes
            buffer = io.BytesIO()
            doc.save(buffer)
            docx_bytes = buffer.getvalue()
            buffer.close()
            
            return docx_bytes
        
        except Exception as e:
            logger.error(f"Error exporting report to DOCX: {e}")
            raise
    
    @staticmethod
    def _add_daily_standup_content_docx(doc, data):
        """Add daily standup content to DOCX"""
        doc.add_heading("Yesterday's Work:", level=2)
        for item in data.get('yesterday_work', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("Today's Plan:", level=2)
        for item in data.get('today_plan', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("Blockers & Issues:", level=2)
        blockers = data.get('blockers', [])
        if blockers:
            for item in blockers:
                doc.add_paragraph(item, style='List Bullet')
        else:
            doc.add_paragraph("No blockers reported.")
    
    @staticmethod
    def _add_sprint_meeting_content_docx(doc, data):
        """Add sprint meeting content to DOCX"""
        doc.add_heading("Sprint Goals:", level=2)
        for item in data.get('sprint_goals', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("Progress Summary:", level=2)
        for item in data.get('progress_summary', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("Issues & Risks:", level=2)
        for item in data.get('issues_risks', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("Action Items:", level=2)
        action_items = data.get('action_items', [])
        if action_items:
            for item in action_items:
                assignee = item.get('assignee', 'Unassigned')
                due_date = item.get('due_date', 'No deadline')
                doc.add_paragraph(
                    f"{item['action']} (Assignee: {assignee}, Due: {due_date})",
                    style='List Bullet'
                )
        else:
            doc.add_paragraph("No action items.")
    
    @staticmethod
    def _add_retrospective_content_docx(doc, data):
        """Add retrospective content to DOCX"""
        doc.add_heading("What Went Well:", level=2)
        for item in data.get('what_went_well', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("What Didn't Go Well:", level=2)
        for item in data.get('what_didnt_go_well', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("Improvements:", level=2)
        for item in data.get('improvements', []):
            doc.add_paragraph(item, style='List Bullet')
        
        doc.add_heading("Action Points:", level=2)
        for item in data.get('action_points', []):
            doc.add_paragraph(item, style='List Bullet')


def export_report(
    report_data: Dict[str, Any],
    report_type: str,
    export_format: str,
    template_config: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Helper function to export report.
    
    Args:
        report_data: Report content dictionary
        report_type: Type of report
        export_format: 'pdf' or 'docx'
        template_config: Optional template configuration
    
    Returns:
        Exported file as bytes
    """
    if export_format.lower() == 'pdf':
        return ReportExporter.export_to_pdf(report_data, report_type, template_config)
    elif export_format.lower() == 'docx':
        return ReportExporter.export_to_docx(report_data, report_type, template_config)
    else:
        raise ValueError(f"Unsupported export format: {export_format}")
