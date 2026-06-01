#!/usr/bin/env python3
"""
Comprehensive PDF Report Generator for HMDA Stakeholder Analysis
==============================================================

Generates professional, stakeholder-focused PDF reports with charts, tables,
and actionable insights for banking market analysis.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether)
from reportlab.platypus.flowables import HRFlowable
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io
import base64
from typing import Dict, List, Any, Optional
import logging
import tempfile
import os

from stakeholder_analytics import AdvancedStakeholderAnalytics, AnalysisConfig, StakeholderType

class PDFReportGenerator:
    """Professional PDF report generator for banking stakeholders."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analytics = AdvancedStakeholderAnalytics()

        # Configure matplotlib for PDF generation
        plt.style.use('seaborn-v0_8')
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 12
        plt.rcParams['axes.labelsize'] = 10
        plt.rcParams['xtick.labelsize'] = 9
        plt.rcParams['ytick.labelsize'] = 9
        plt.rcParams['legend.fontsize'] = 9

        # Color schemes by stakeholder type
        self.color_schemes = {
            StakeholderType.LOCAL_GOVERNMENT: {
                'primary': '#2E86AB', 'secondary': '#A23B72', 'accent': '#F18F01'
            },
            StakeholderType.COMMUNITY_ADVOCATE: {
                'primary': '#C73E1D', 'secondary': '#592D2D', 'accent': '#F2CC8F'
            },
            StakeholderType.REGULATOR: {
                'primary': '#1B4332', 'secondary': '#40916C', 'accent': '#95D5B2'
            },
            StakeholderType.RESEARCHER: {
                'primary': '#264653', 'secondary': '#2A9D8F', 'accent': '#E9C46A'
            },
            StakeholderType.BANK_EXECUTIVE: {
                'primary': '#003049', 'secondary': '#669BBC', 'accent': '#FDF0D5'
            }
        }

    def generate_comprehensive_report(self,
                                    data: pd.DataFrame,
                                    config: AnalysisConfig,
                                    geographic_id: str,
                                    output_path: str) -> str:
        """Generate comprehensive stakeholder PDF report."""

        self.logger.info(f"Generating {config.stakeholder_type.value} report for {geographic_id}")

        # Generate analysis insights
        insights = self.analytics.generate_stakeholder_insights(data, config, geographic_id)

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Build document content
        story = []
        story.extend(self._create_title_page(config, geographic_id, insights))
        story.append(PageBreak())

        story.extend(self._create_executive_summary(insights, config))
        story.append(PageBreak())

        story.extend(self._create_key_metrics_section(insights, config))
        story.append(PageBreak())

        story.extend(self._create_risk_assessment_section(insights, config))
        story.append(PageBreak())

        story.extend(self._create_opportunities_section(insights, config))
        story.append(PageBreak())

        story.extend(self._create_recommendations_section(insights, config))
        story.append(PageBreak())

        story.extend(self._create_comparative_analysis_section(insights, config))
        story.append(PageBreak())

        story.extend(self._create_detailed_charts_section(data, insights, config))
        story.append(PageBreak())

        story.extend(self._create_data_appendix(data, insights, config))

        # Build PDF
        doc.build(story)

        self.logger.info(f"Report generated successfully: {output_path}")
        return output_path

    def _create_title_page(self, config: AnalysisConfig, geographic_id: str, insights: Dict) -> List:
        """Create professional title page."""
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])
        )

        geographic_type = config.geographic_scope.title()
        title = f"Banking Market Analysis Report<br/>{geographic_type}-Level Assessment"
        story.append(Paragraph(title, title_style))

        # Subtitle
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.HexColor(self.color_schemes[config.stakeholder_type]['secondary'])
        )

        stakeholder_name = config.stakeholder_type.value.replace('_', ' ').title()
        subtitle = f"Stakeholder Report: {stakeholder_name}<br/>Geographic Area: {geographic_id}"
        story.append(Paragraph(subtitle, subtitle_style))

        story.append(Spacer(1, 30))

        # Executive highlights box
        highlight_data = [
            ['Market Health Score:', f"{insights['executive_summary']['market_health_score']:.1f}/100"],
            ['Access Score:', f"{insights['executive_summary']['access_score']:.1f}/100"],
            ['Fairness Score:', f"{insights['executive_summary']['fairness_score']:.1f}/100"],
            ['Overall Risk Level:', self._get_risk_level(insights['risk_assessment']['overall_risk_score'])]
        ]

        highlight_table = Table(highlight_data, colWidths=[3*inch, 2*inch])
        highlight_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor(self.color_schemes[config.stakeholder_type]['secondary'])),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
        ]))

        story.append(highlight_table)
        story.append(Spacer(1, 50))

        # Report metadata
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey
        )

        report_date = datetime.now().strftime("%B %d, %Y")
        metadata = f"""
        <b>Report Generated:</b> {report_date}<br/>
        <b>Analysis Period:</b> Most Recent Available Data<br/>
        <b>Report Type:</b> {config.detail_level.title()} Analysis<br/>
        <b>Data Sources:</b> HMDA, CRA, Regulatory Filings
        """
        story.append(Paragraph(metadata, metadata_style))

        return story

    def _create_executive_summary(self, insights: Dict, config: AnalysisConfig) -> List:
        """Create executive summary section."""
        styles = getSampleStyleSheet()
        story = []

        # Section header
        story.append(Paragraph("Executive Summary", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        # Top concerns
        story.append(Paragraph("Key Concerns Identified", styles['Heading2']))
        concerns_text = "<br/>".join([f"• {concern}" for concern in insights['executive_summary']['top_concerns']])
        story.append(Paragraph(concerns_text, styles['Normal']))
        story.append(Spacer(1, 15))

        # Priority actions
        story.append(Paragraph("Priority Actions Recommended", styles['Heading2']))
        actions_text = "<br/>".join([f"• {action}" for action in insights['executive_summary']['priority_actions']])
        story.append(Paragraph(actions_text, styles['Normal']))
        story.append(Spacer(1, 15))

        # Market trends
        story.append(Paragraph("Market Trends Analysis", styles['Heading2']))
        trends = insights['executive_summary']['market_trends']
        trends_text = f"""
        <b>Market Concentration:</b> {trends['concentration']}<br/>
        <b>Banking Access:</b> {trends['access']}<br/>
        <b>Digital Adoption:</b> {trends['digital_adoption']}<br/>
        <b>Branch Network:</b> {trends['branch_network']}
        """
        story.append(Paragraph(trends_text, styles['Normal']))

        return story

    def _create_key_metrics_section(self, insights: Dict, config: AnalysisConfig) -> List:
        """Create key metrics dashboard section."""
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Key Performance Indicators", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        key_metrics = insights['key_metrics']

        # Access metrics
        if 'access' in key_metrics:
            story.append(Paragraph("Banking Access Metrics", styles['Heading2']))
            access_data = [
                ['Metric', 'Value', 'Assessment'],
                ['Branches per 10,000 residents', f"{key_metrics['access']['branches_per_capita']:.1f}", self._assess_metric(key_metrics['access']['branches_per_capita'], 'branches')],
                ['ATM Density Score', f"{key_metrics['access']['atm_density']:.1f}", self._assess_metric(key_metrics['access']['atm_density'], 'atm')],
                ['Banking Desert Risk', key_metrics['access']['banking_desert_risk'], ''],
                ['Digital Access Score', f"{key_metrics['access']['digital_access_score']:.0f}/100", self._assess_metric(key_metrics['access']['digital_access_score'], 'digital')]
            ]

            access_table = Table(access_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            access_table.setStyle(self._get_table_style())
            story.append(access_table)
            story.append(Spacer(1, 15))

        # Competition metrics
        if 'competition' in key_metrics:
            story.append(Paragraph("Market Competition Metrics", styles['Heading2']))
            comp_data = [
                ['Metric', 'Value', 'Assessment'],
                ['HHI Score', f"{key_metrics['competition']['hhi_score']:.0f}", self._assess_hhi(key_metrics['competition']['hhi_score'])],
                ['Market Leader Share', f"{key_metrics['competition']['market_leader_share']:.1f}%", ''],
                ['Competition Trend', key_metrics['competition']['competition_trend'], ''],
                ['New Entrant Activity', f"{key_metrics['competition']['new_entrant_activity']} institutions", '']
            ]

            comp_table = Table(comp_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            comp_table.setStyle(self._get_table_style())
            story.append(comp_table)
            story.append(Spacer(1, 15))

        # Fairness metrics
        if 'fairness' in key_metrics:
            story.append(Paragraph("Lending Fairness Metrics", styles['Heading2']))
            fairness_data = [
                ['Metric', 'Value', 'Assessment'],
                ['Approval Rate Disparity', f"{key_metrics['fairness']['approval_rate_disparity']:.1f} pp", self._assess_disparity(key_metrics['fairness']['approval_rate_disparity'])],
                ['LMI Lending Ratio', f"{key_metrics['fairness']['lmi_lending_ratio']:.2f}", ''],
                ['Minority Lending Ratio', f"{key_metrics['fairness']['minority_lending_ratio']:.2f}", ''],
                ['Redlining Risk Score', f"{key_metrics['fairness']['redlining_risk_score']:.0f}/100", self._assess_metric(key_metrics['fairness']['redlining_risk_score'], 'risk')]
            ]

            fairness_table = Table(fairness_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            fairness_table.setStyle(self._get_table_style())
            story.append(fairness_table)

        return story

    def _create_risk_assessment_section(self, insights: Dict, config: AnalysisConfig) -> List:
        """Create comprehensive risk assessment section."""
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Risk Assessment", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        risk_assessment = insights['risk_assessment']

        # Overall risk score
        overall_risk = risk_assessment['overall_risk_score']
        risk_level = self._get_risk_level(overall_risk)

        story.append(Paragraph(f"Overall Risk Level: {risk_level} ({overall_risk:.1f}/100)", styles['Heading2']))
        story.append(Spacer(1, 10))

        # Risk breakdown table
        risk_data = [['Risk Category', 'Score', 'Level', 'Description']]

        for risk_name, risk_info in risk_assessment.items():
            if risk_name != 'overall_risk_score' and isinstance(risk_info, dict):
                risk_data.append([
                    risk_name.replace('_', ' ').title(),
                    f"{risk_info['score']:.1f}",
                    risk_info['level'],
                    risk_info['description'][:60] + "..." if len(risk_info['description']) > 60 else risk_info['description']
                ])

        risk_table = Table(risk_data, colWidths=[2*inch, 1*inch, 1*inch, 2.5*inch])
        risk_table.setStyle(self._get_table_style())
        story.append(risk_table)

        return story

    def _create_opportunities_section(self, insights: Dict, config: AnalysisConfig) -> List:
        """Create opportunities and recommendations section."""
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Market Opportunities", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        opportunities = insights['opportunities']

        for i, opp in enumerate(opportunities[:5], 1):  # Top 5 opportunities
            story.append(Paragraph(f"Opportunity {i}: {opp['description']}", styles['Heading3']))

            opp_details = f"""
            <b>Type:</b> {opp['type'].replace('_', ' ').title()}<br/>
            <b>Potential Impact:</b> {opp['potential_impact']}<br/>
            <b>Feasibility:</b> {opp['feasibility']}<br/>
            <b>Priority Score:</b> {opp['priority']:.1f}/10
            """
            story.append(Paragraph(opp_details, styles['Normal']))
            story.append(Spacer(1, 10))

        return story

    def _create_recommendations_section(self, insights: Dict, config: AnalysisConfig) -> List:
        """Create actionable recommendations section."""
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Actionable Recommendations", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        recommendations = insights['recommendations']

        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"Recommendation {i}", styles['Heading3']))

            rec_details = f"""
            <b>Category:</b> {rec['category']}<br/>
            <b>Action:</b> {rec['recommendation']}<br/>
            <b>Priority:</b> {rec['priority']}<br/>
            <b>Timeline:</b> {rec['timeline']}<br/>
            <b>Expected Impact:</b> {rec['impact']}
            """
            story.append(Paragraph(rec_details, styles['Normal']))
            story.append(Spacer(1, 15))

        return story

    def _create_comparative_analysis_section(self, insights: Dict, config: AnalysisConfig) -> List:
        """Create comparative analysis section."""
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Comparative Analysis", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        comparative = insights['comparative_analysis']

        # Regional comparison
        story.append(Paragraph("Regional Comparison", styles['Heading2']))
        regional_data = [
            ['Metric', 'Local Market', 'Regional Average'],
            ['Market Concentration', comparative['regional_comparison']['market_concentration'], 'Average'],
            ['Access Score', comparative['regional_comparison']['access_score'], 'Average'],
            ['CRA Performance', comparative['regional_comparison']['cra_performance'], 'Average']
        ]

        regional_table = Table(regional_data, colWidths=[2*inch, 2*inch, 2*inch])
        regional_table.setStyle(self._get_table_style())
        story.append(regional_table)
        story.append(Spacer(1, 15))

        # Peer markets
        story.append(Paragraph("Similar Markets", styles['Heading2']))
        peer_text = "Markets with similar characteristics:<br/>"
        for peer in comparative['peer_markets']:
            peer_text += f"• {peer['name']} (Similarity: {peer['similarity_score']:.0%})<br/>"
        story.append(Paragraph(peer_text, styles['Normal']))

        return story

    def _create_detailed_charts_section(self, data: pd.DataFrame, insights: Dict, config: AnalysisConfig) -> List:
        """Create detailed charts and visualizations section."""
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Detailed Analysis Charts", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        # Generate and include charts
        charts = self._generate_analysis_charts(data, insights, config)

        for chart_name, chart_path in charts.items():
            story.append(Paragraph(chart_name.replace('_', ' ').title(), styles['Heading2']))
            if os.path.exists(chart_path):
                story.append(Image(chart_path, width=6*inch, height=4*inch))
            story.append(Spacer(1, 15))

        return story

    def _create_data_appendix(self, data: pd.DataFrame, insights: Dict, config: AnalysisConfig) -> List:
        """Create data appendix section."""
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Data Appendix", styles['Heading1']))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(self.color_schemes[config.stakeholder_type]['primary'])))
        story.append(Spacer(1, 20))

        # Data sources
        story.append(Paragraph("Data Sources and Methodology", styles['Heading2']))
        methodology_text = """
        <b>Primary Data Sources:</b><br/>
        • Home Mortgage Disclosure Act (HMDA) data<br/>
        • Community Reinvestment Act (CRA) performance evaluations<br/>
        • Federal Deposit Insurance Corporation (FDIC) institution data<br/>
        • Census Bureau demographic data<br/><br/>

        <b>Analysis Methodology:</b><br/>
        • Market concentration measured using Herfindahl-Hirschman Index (HHI)<br/>
        • Fair lending analysis based on approval rate comparisons<br/>
        • Access scores calculated using branch density and geographic coverage<br/>
        • Risk assessments based on regulatory guidance and industry standards
        """
        story.append(Paragraph(methodology_text, styles['Normal']))
        story.append(Spacer(1, 15))

        # Regulatory context
        regulatory_context = insights.get('regulatory_context', {})
        if regulatory_context:
            story.append(Paragraph("Regulatory Context", styles['Heading2']))

            reg_text = f"""
            <b>Applicable Regulations:</b><br/>
            {', '.join(regulatory_context.get('applicable_regulations', []))}<br/><br/>

            <b>Recent Changes:</b><br/>
            {', '.join(regulatory_context.get('recent_regulatory_changes', []))}<br/><br/>

            <b>Compliance Status:</b> {regulatory_context.get('compliance_status', 'Not available')}
            """
            story.append(Paragraph(reg_text, styles['Normal']))

        return story

    def _generate_analysis_charts(self, data: pd.DataFrame, insights: Dict, config: AnalysisConfig) -> Dict[str, str]:
        """Generate analysis charts and return file paths."""
        charts = {}
        temp_dir = tempfile.mkdtemp()

        # Market concentration chart
        chart_path = os.path.join(temp_dir, 'market_concentration.png')
        self._create_market_concentration_chart(insights, chart_path, config)
        charts['Market Concentration Analysis'] = chart_path

        # Risk assessment radar chart
        chart_path = os.path.join(temp_dir, 'risk_radar.png')
        self._create_risk_radar_chart(insights, chart_path, config)
        charts['Risk Assessment Overview'] = chart_path

        # Access metrics chart
        chart_path = os.path.join(temp_dir, 'access_metrics.png')
        self._create_access_metrics_chart(insights, chart_path, config)
        charts['Banking Access Metrics'] = chart_path

        return charts

    def _create_market_concentration_chart(self, insights: Dict, output_path: str, config: AnalysisConfig):
        """Create market concentration visualization."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        colors_scheme = self.color_schemes[config.stakeholder_type]

        # HHI comparison
        hhi_data = [1500, insights['key_metrics'].get('competition', {}).get('hhi_score', 2000), 2500]
        categories = ['Competitive\nThreshold', 'Current\nMarket', 'Concentrated\nThreshold']
        bars = ax1.bar(categories, hhi_data, color=[colors_scheme['accent'], colors_scheme['primary'], colors_scheme['secondary']])
        ax1.set_title('Market Concentration (HHI Score)')
        ax1.set_ylabel('HHI Score')
        ax1.axhline(y=1500, color='green', linestyle='--', alpha=0.7, label='Competitive')
        ax1.axhline(y=2500, color='red', linestyle='--', alpha=0.7, label='Concentrated')

        # Market share pie chart
        market_shares = [35, 20, 15, 10, 20]  # Example data
        labels = ['Leader', 'Bank 2', 'Bank 3', 'Bank 4', 'Others']
        ax2.pie(market_shares, labels=labels, autopct='%1.1f%%', startangle=90,
                colors=plt.cm.Set3(np.linspace(0, 1, len(market_shares))))
        ax2.set_title('Market Share Distribution')

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def _create_risk_radar_chart(self, insights: Dict, output_path: str, config: AnalysisConfig):
        """Create risk assessment radar chart."""
        risk_data = insights['risk_assessment']

        categories = ['Market\nConcentration', 'Access\nDegradation', 'Discriminatory\nLending',
                     'Economic\nVulnerability', 'Regulatory\nCompliance']

        values = [
            risk_data.get('market_concentration_risk', {}).get('score', 0),
            risk_data.get('access_degradation_risk', {}).get('score', 0),
            risk_data.get('discriminatory_lending_risk', {}).get('score', 0),
            risk_data.get('economic_vulnerability_risk', {}).get('score', 0),
            risk_data.get('regulatory_compliance_risk', {}).get('score', 0)
        ]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]  # Complete the circle
        angles += angles[:1]

        ax.plot(angles, values, 'o-', linewidth=2, color=self.color_schemes[config.stakeholder_type]['primary'])
        ax.fill(angles, values, alpha=0.25, color=self.color_schemes[config.stakeholder_type]['primary'])
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        ax.set_title('Risk Assessment Profile', size=16, pad=20)
        ax.grid(True)

        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def _create_access_metrics_chart(self, insights: Dict, output_path: str, config: AnalysisConfig):
        """Create banking access metrics visualization."""
        access_data = insights['key_metrics'].get('access', {})

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        colors_scheme = self.color_schemes[config.stakeholder_type]

        # Branches per capita
        ax1.bar(['Current', 'Regional Avg', 'National Avg'],
               [access_data.get('branches_per_capita', 2.3), 2.5, 2.8],
               color=[colors_scheme['primary'], colors_scheme['secondary'], colors_scheme['accent']])
        ax1.set_title('Branches per 10K Residents')
        ax1.set_ylabel('Count')

        # ATM density
        ax2.bar(['Current', 'Regional Avg', 'National Avg'],
               [access_data.get('atm_density', 4.7), 5.2, 5.8],
               color=[colors_scheme['primary'], colors_scheme['secondary'], colors_scheme['accent']])
        ax2.set_title('ATM Density Score')
        ax2.set_ylabel('Score')

        # Digital access
        digital_score = access_data.get('digital_access_score', 85)
        ax3.pie([digital_score, 100-digital_score], labels=['Available', 'Gap'],
               autopct='%1.1f%%', startangle=90,
               colors=[colors_scheme['primary'], colors_scheme['accent']])
        ax3.set_title('Digital Access Score')

        # Banking desert risk
        risk_levels = ['Low', 'Moderate', 'High']
        risk_counts = [15, 8, 2]  # Example data
        ax4.bar(risk_levels, risk_counts,
               color=[colors_scheme['accent'], colors_scheme['secondary'], colors_scheme['primary']])
        ax4.set_title('Banking Desert Risk by Area')
        ax4.set_ylabel('Number of Areas')

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    # Helper methods
    def _get_table_style(self):
        """Get standard table style."""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])

    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level."""
        if score < 25:
            return "Low"
        elif score < 50:
            return "Moderate"
        elif score < 75:
            return "High"
        else:
            return "Critical"

    def _assess_metric(self, value: float, metric_type: str) -> str:
        """Assess metric value."""
        if metric_type == 'branches':
            return "Good" if value >= 2.5 else "Needs Improvement"
        elif metric_type == 'atm':
            return "Good" if value >= 5.0 else "Needs Improvement"
        elif metric_type == 'digital':
            return "Excellent" if value >= 80 else "Good" if value >= 60 else "Needs Improvement"
        elif metric_type == 'risk':
            return "Low Risk" if value < 30 else "Moderate Risk" if value < 60 else "High Risk"
        return "Average"

    def _assess_hhi(self, hhi: float) -> str:
        """Assess HHI score."""
        if hhi < 1500:
            return "Competitive"
        elif hhi < 2500:
            return "Moderately Concentrated"
        else:
            return "Highly Concentrated"

    def _assess_disparity(self, disparity: float) -> str:
        """Assess approval rate disparity."""
        if disparity < 5:
            return "Minimal Concern"
        elif disparity < 15:
            return "Moderate Concern"
        else:
            return "Significant Concern"

    def generate_quick_report(self,
                            data: pd.DataFrame,
                            config: AnalysisConfig,
                            geographic_id: str,
                            output_path: str) -> str:
        """Generate a condensed, quick-reference report."""

        self.logger.info(f"Generating quick report for {geographic_id}")

        # Generate basic insights
        insights = self.analytics.generate_stakeholder_insights(data, config, geographic_id)

        # Create simplified PDF
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        story.append(Paragraph(f"Quick Analysis: {geographic_id}", styles['Title']))
        story.append(Spacer(1, 20))

        # Key metrics summary
        summary_data = [
            ['Metric', 'Score', 'Status'],
            ['Market Health', f"{insights['executive_summary']['market_health_score']:.1f}/100",
             self._get_status(insights['executive_summary']['market_health_score'])],
            ['Access Score', f"{insights['executive_summary']['access_score']:.1f}/100",
             self._get_status(insights['executive_summary']['access_score'])],
            ['Fairness Score', f"{insights['executive_summary']['fairness_score']:.1f}/100",
             self._get_status(insights['executive_summary']['fairness_score'])],
            ['Risk Level', f"{insights['risk_assessment']['overall_risk_score']:.1f}/100",
             self._get_risk_level(insights['risk_assessment']['overall_risk_score'])]
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        summary_table.setStyle(self._get_table_style())
        story.append(summary_table)

        story.append(Spacer(1, 20))

        # Top recommendations
        story.append(Paragraph("Top Recommendations", styles['Heading2']))
        for i, rec in enumerate(insights['recommendations'][:3], 1):
            story.append(Paragraph(f"{i}. {rec['recommendation']}", styles['Normal']))

        doc.build(story)
        return output_path

    def _get_status(self, score: float) -> str:
        """Convert score to status."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Needs Attention"