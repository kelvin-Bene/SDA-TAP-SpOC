# -*- coding: utf-8 -*-
"""
Evaluation Report Generation Module

This module generates comprehensive evaluation reports for UCT processor results.
Includes JSON output and PDF reports with graphs as described by Lewis.

Lewis (transcript): "Taking all of those metrics... we compile a comprehensive report.
It's got graphs, it's got numbers, and it essentially gives an overall picture
of how well the UCT processor performs."

Author: Gabriel Lundin, UCT Benchmark Team
Date: 2025-2026
"""

import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

# Optional imports for PDF generation
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for server use
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available - PDF reports will be limited")

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available - PDF reports will use matplotlib only")


def evaluationReport(
    association_results,
    binary_results,
    state_results,
    residual_ref_results,
    residual_cand_results,
    output_path,
):
    """
    Generates and saves the JSON result file containing performance metrics.

    Args:
        association_results (Dict): Dict of association metrics.
        binary_results (Pandas DataFrame): Dataframe of binary metrics.
        state_results (Pandas DataFrame): Dataframe of residual metrics.
        residual_ref_results (Pandas DataFrame): Dataframe of residual metrics WRT reference orbits.
        residual_cand_results (Pandas DataFrame): Dataframe of residual metrics WRT candidate orbits.
        output_path (str): Output relative path for the JSON result file.

    Outputs:
        eval (Dict): The combined raw evaluation dict.
    """

    # Convert DataFrame cell arrays to nested lists
    def _convert_arrays(df):
        # B5: .applymap() deprecated in pandas 2.1+, use .map()
        return df.map(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)

    association_results.pop("Time Elapsed", None)

    residual_ref_results["Epoch"] = residual_ref_results["Epoch"].apply(
        lambda arr: [ts.isoformat() if hasattr(ts, "isoformat") else str(ts) for ts in arr]
    )

    residual_cand_results["Epoch"] = residual_cand_results["Epoch"].apply(
        lambda arr: [ts.isoformat() if hasattr(ts, "isoformat") else str(ts) for ts in arr]
    )

    combined_dict = {
        "association_results": association_results,
        "binary_results": _convert_arrays(binary_results).to_dict(orient="records"),
        "state_results": _convert_arrays(state_results).to_dict(orient="records"),
        "residual_ref_results": _convert_arrays(residual_ref_results).to_dict(orient="records"),
        "residual_cand_results": _convert_arrays(residual_cand_results).to_dict(orient="records"),
    }

    # Save to JSON
    with open(output_path, "w") as f:
        json.dump(combined_dict, f, indent=2)

    return combined_dict


# =============================================================================
# PDF REPORT GENERATION
# =============================================================================


def _create_summary_stats(combined_dict: Dict) -> Dict[str, Any]:
    """Extract summary statistics from evaluation results."""
    stats = {}

    # Association summary
    assoc = combined_dict.get("association_results", {})
    stats["total_candidates"] = assoc.get("Num Candidate Objects", 0)
    stats["total_references"] = assoc.get("Num Reference Objects", 0)
    stats["associated_count"] = assoc.get("Num Associations Made", 0)

    # Binary metrics summary — B13: default to 0 when DataFrame is empty or has NaN
    binary = combined_dict.get("binary_results", [])
    if binary:
        df = pd.DataFrame(binary)
        if "Accuracy" in df.columns:
            stats["mean_accuracy"] = float(df["Accuracy"].mean() or 0)
        if "F1" in df.columns:
            stats["mean_f1"] = float(df["F1"].mean() or 0)
        if "True Positive" in df.columns:
            stats["total_tp"] = int(df["True Positive"].sum() or 0)
        if "False Positive" in df.columns:
            stats["total_fp"] = int(df["False Positive"].sum() or 0)

    # State metrics summary — B13: default to 0 when empty
    state = combined_dict.get("state_results", [])
    if state:
        df = pd.DataFrame(state)
        if "Position Error" in df.columns:
            stats["mean_pos_error_km"] = float(df["Position Error"].mean() or 0)
            stats["max_pos_error_km"] = float(df["Position Error"].max() or 0)
        if "Velocity Error" in df.columns:
            stats["mean_vel_error_km_s"] = df["Velocity Error"].mean()

    return stats


def _plot_binary_metrics(binary_results: List[Dict], ax=None) -> plt.Figure:
    """Create binary metrics visualization."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.figure

    if not binary_results:
        ax.text(0.5, 0.5, "No binary metrics available",
                ha='center', va='center', fontsize=14)
        return fig

    df = pd.DataFrame(binary_results)

    # Bar chart of key metrics
    metrics = ["True Positive", "False Positive", "True Negative", "False Negative"]
    available_metrics = [m for m in metrics if m in df.columns]

    if available_metrics:
        totals = [df[m].sum() for m in available_metrics]
        colors_list = ['#2ecc71', '#e74c3c', '#3498db', '#f39c12']
        bars = ax.bar(available_metrics, totals, color=colors_list[:len(available_metrics)])
        ax.set_ylabel("Count")
        ax.set_title("Binary Classification Results")

        # Add value labels on bars
        for bar, val in zip(bars, totals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                   f'{int(val)}', ha='center', va='bottom')

    return fig


def _plot_state_errors(state_results: List[Dict], ax=None) -> plt.Figure:
    """Create state error visualization."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.figure

    if not state_results:
        ax.text(0.5, 0.5, "No state metrics available",
                ha='center', va='center', fontsize=14)
        return fig

    df = pd.DataFrame(state_results)

    if "Position Error" in df.columns:
        # Histogram of position errors
        errors = df["Position Error"].dropna()
        if not errors.empty:
            ax.hist(errors, bins=20, color='#3498db', edgecolor='black', alpha=0.7)
            ax.axvline(errors.mean(), color='red', linestyle='--',
                      label=f'Mean: {errors.mean():.2f} km')
            ax.axvline(errors.median(), color='green', linestyle=':',
                      label=f'Median: {errors.median():.2f} km')
            ax.set_xlabel("Position Error (km)")
            ax.set_ylabel("Count")
            ax.set_title("Position Error Distribution")
            ax.legend()

    return fig


def _plot_residuals(residual_results: List[Dict], title: str, ax=None) -> plt.Figure:
    """Create residuals visualization."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.figure

    if not residual_results:
        ax.text(0.5, 0.5, "No residual metrics available",
                ha='center', va='center', fontsize=14)
        return fig

    df = pd.DataFrame(residual_results)

    if "Mean RA Residual" in df.columns and "Mean Dec Residual" in df.columns:
        ra_res = df["Mean RA Residual"].dropna()
        dec_res = df["Mean Dec Residual"].dropna()

        if not ra_res.empty and not dec_res.empty:
            ax.scatter(ra_res, dec_res, alpha=0.6, c='#3498db')
            ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
            ax.axvline(0, color='gray', linestyle='--', alpha=0.5)
            ax.set_xlabel("RA Residual (arcsec)")
            ax.set_ylabel("Dec Residual (arcsec)")
            ax.set_title(title)

            # Add circle showing 1-sigma
            from matplotlib.patches import Circle
            ra_std = ra_res.std()
            dec_std = dec_res.std()
            circle = Circle((0, 0), (ra_std + dec_std) / 2, fill=False,
                           color='red', linestyle='--', label='1-sigma')
            ax.add_patch(circle)
            ax.legend()
            ax.set_aspect('equal', adjustable='datalim')

    return fig


def generate_pdf_report_matplotlib(
    combined_dict: Dict,
    output_path: str,
    title: str = "UCT Processor Evaluation Report",
) -> bool:
    """
    Generate PDF report using matplotlib.

    Args:
        combined_dict: Combined evaluation results dictionary
        output_path: Path to save PDF file
        title: Report title

    Returns:
        True if successful, False otherwise
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available for PDF generation")
        return False

    try:
        with PdfPages(output_path) as pdf:
            # Title page
            fig = plt.figure(figsize=(11, 8.5))
            fig.text(0.5, 0.6, title, ha='center', va='center', fontsize=24, fontweight='bold')
            fig.text(0.5, 0.5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    ha='center', va='center', fontsize=12)
            fig.text(0.5, 0.4, "UCT Benchmark Evaluation System",
                    ha='center', va='center', fontsize=14, style='italic')
            pdf.savefig(fig)
            plt.close(fig)

            # Summary statistics page
            stats = _create_summary_stats(combined_dict)
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis('off')

            summary_text = "Summary Statistics\n" + "=" * 40 + "\n\n"
            summary_text += f"Total Reference Objects: {stats.get('total_references', 'N/A')}\n"
            summary_text += f"Total Candidate Objects: {stats.get('total_candidates', 'N/A')}\n"
            summary_text += f"Associations Made: {stats.get('associated_count', 'N/A')}\n\n"

            if 'mean_accuracy' in stats:
                summary_text += f"Mean Accuracy: {stats['mean_accuracy']:.4f}\n"
            if 'mean_f1' in stats:
                summary_text += f"Mean F1 Score: {stats['mean_f1']:.4f}\n"
            if 'mean_pos_error_km' in stats:
                summary_text += f"Mean Position Error: {stats['mean_pos_error_km']:.2f} km\n"
            if 'max_pos_error_km' in stats:
                summary_text += f"Max Position Error: {stats['max_pos_error_km']:.2f} km\n"

            ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
                   fontsize=12, verticalalignment='top', fontfamily='monospace')
            pdf.savefig(fig)
            plt.close(fig)

            # Binary metrics plot
            binary_results = combined_dict.get("binary_results", [])
            fig, ax = plt.subplots(figsize=(11, 8.5))
            _plot_binary_metrics(binary_results, ax)
            pdf.savefig(fig)
            plt.close(fig)

            # State errors plot
            state_results = combined_dict.get("state_results", [])
            fig, ax = plt.subplots(figsize=(11, 8.5))
            _plot_state_errors(state_results, ax)
            pdf.savefig(fig)
            plt.close(fig)

            # Reference residuals plot
            residual_ref = combined_dict.get("residual_ref_results", [])
            fig, ax = plt.subplots(figsize=(11, 8.5))
            _plot_residuals(residual_ref, "Residuals vs Reference Orbit", ax)
            pdf.savefig(fig)
            plt.close(fig)

            # Candidate residuals plot
            residual_cand = combined_dict.get("residual_cand_results", [])
            fig, ax = plt.subplots(figsize=(11, 8.5))
            _plot_residuals(residual_cand, "Residuals vs Candidate Orbit", ax)
            pdf.savefig(fig)
            plt.close(fig)

        logger.info(f"PDF report saved to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        return False


def generate_pdf_report_reportlab(
    combined_dict: Dict,
    output_path: str,
    title: str = "UCT Processor Evaluation Report",
) -> bool:
    """
    Generate PDF report using reportlab (better formatting).

    Args:
        combined_dict: Combined evaluation results dictionary
        output_path: Path to save PDF file
        title: Report title

    Returns:
        True if successful, False otherwise
    """
    if not REPORTLAB_AVAILABLE:
        logger.warning("reportlab not available, falling back to matplotlib")
        return generate_pdf_report_matplotlib(combined_dict, output_path, title)

    try:
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=1,  # Center
            spaceAfter=30
        )
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        # Date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1
        )
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            date_style
        ))
        story.append(Spacer(1, 30))

        # Summary section
        story.append(Paragraph("Summary Statistics", styles['Heading2']))
        story.append(Spacer(1, 12))

        stats = _create_summary_stats(combined_dict)
        summary_data = [
            ["Metric", "Value"],
            ["Total Reference Objects", str(stats.get('total_references', 'N/A'))],
            ["Total Candidate Objects", str(stats.get('total_candidates', 'N/A'))],
            ["Associations Made", str(stats.get('associated_count', 'N/A'))],
        ]

        if 'mean_accuracy' in stats:
            summary_data.append(["Mean Accuracy", f"{stats['mean_accuracy']:.4f}"])
        if 'mean_f1' in stats:
            summary_data.append(["Mean F1 Score", f"{stats['mean_f1']:.4f}"])
        if 'mean_pos_error_km' in stats:
            summary_data.append(["Mean Position Error", f"{stats['mean_pos_error_km']:.2f} km"])

        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(PageBreak())

        # Add matplotlib figures if available
        if MATPLOTLIB_AVAILABLE:
            story.append(Paragraph("Binary Classification Results", styles['Heading2']))
            story.append(Spacer(1, 12))

            # Create and embed binary metrics figure
            fig, ax = plt.subplots(figsize=(8, 5))
            _plot_binary_metrics(combined_dict.get("binary_results", []), ax)

            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close(fig)

            img = Image(img_buffer, width=6*inch, height=4*inch)
            story.append(img)
            story.append(PageBreak())

            # State errors figure
            story.append(Paragraph("Position Error Distribution", styles['Heading2']))
            story.append(Spacer(1, 12))

            fig, ax = plt.subplots(figsize=(8, 5))
            _plot_state_errors(combined_dict.get("state_results", []), ax)

            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close(fig)

            img = Image(img_buffer, width=6*inch, height=4*inch)
            story.append(img)

        # Build PDF
        doc.build(story)
        logger.info(f"PDF report saved to: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate PDF report with reportlab: {e}")
        # Fall back to matplotlib
        return generate_pdf_report_matplotlib(combined_dict, output_path, title)


def generate_pdf_report(
    combined_dict: Dict,
    output_path: str,
    title: str = "UCT Processor Evaluation Report",
    use_reportlab: bool = True,
) -> bool:
    """
    Generate a comprehensive PDF evaluation report.

    This is the main entry point for PDF generation. It creates a report
    with summary statistics, graphs, and detailed metrics as described by Lewis.

    Args:
        combined_dict: Combined evaluation results dictionary (from evaluationReport)
        output_path: Path to save PDF file
        title: Report title
        use_reportlab: Whether to use reportlab (better formatting) if available

    Returns:
        True if successful, False otherwise
    """
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if use_reportlab and REPORTLAB_AVAILABLE:
        return generate_pdf_report_reportlab(combined_dict, output_path, title)
    elif MATPLOTLIB_AVAILABLE:
        return generate_pdf_report_matplotlib(combined_dict, output_path, title)
    else:
        logger.error("No PDF generation library available (need matplotlib or reportlab)")
        return False


def evaluationReportWithPDF(
    association_results,
    binary_results,
    state_results,
    residual_ref_results,
    residual_cand_results,
    output_path,
    generate_pdf: bool = True,
    pdf_title: str = "UCT Processor Evaluation Report",
):
    """
    Generate evaluation report in both JSON and PDF formats.

    This is a convenience function that combines JSON and PDF generation.

    Args:
        association_results: Association metrics dict
        binary_results: Binary metrics DataFrame
        state_results: State metrics DataFrame
        residual_ref_results: Reference residual metrics DataFrame
        residual_cand_results: Candidate residual metrics DataFrame
        output_path: Base output path (JSON extension added automatically)
        generate_pdf: Whether to also generate PDF report
        pdf_title: Title for PDF report

    Returns:
        Dict with 'json_path', 'pdf_path', 'combined_dict'
    """
    # Ensure output path has .json extension
    if not output_path.endswith('.json'):
        json_path = output_path + '.json'
    else:
        json_path = output_path

    # Generate JSON report
    combined_dict = evaluationReport(
        association_results,
        binary_results,
        state_results,
        residual_ref_results,
        residual_cand_results,
        json_path,
    )

    result = {
        'json_path': json_path,
        'pdf_path': None,
        'combined_dict': combined_dict,
    }

    # Generate PDF report if requested
    if generate_pdf:
        pdf_path = json_path.replace('.json', '.pdf')
        if generate_pdf_report(combined_dict, pdf_path, pdf_title):
            result['pdf_path'] = pdf_path

    return result


# =============================================================================
# COMPREHENSIVE EVALUATION REPORT (Per Louis's Specification)
# =============================================================================


def generate_comprehensive_evaluation_report(
    dataset_code: str,
    binary_metrics: Dict[str, Any],
    state_metrics: Dict[str, Any],
    residual_metrics: Dict[str, Any],
    algorithm_info: Dict[str, Any],
    output_path: str,
) -> str:
    """
    Generate comprehensive PDF evaluation report per Louis's specification.

    Report sections:
    1. Executive Summary
    2. Dataset Information
    3. Binary Classification Metrics (with confusion matrix)
    4. State Estimation Metrics (with error histograms)
    5. Residual Analysis (with plots)
    6. Algorithm Performance Summary

    Args:
        dataset_code: 16-character dataset code
        binary_metrics: Dict from binaryMetrics()
        state_metrics: Dict from calculate_state_metrics()
        residual_metrics: Dict from calculate_residual_metrics()
        algorithm_info: Dict with algorithm name, version, parameters
        output_path: Path for output PDF

    Returns:
        Path to generated PDF
    """
    if not REPORTLAB_AVAILABLE:
        logger.warning("reportlab not available, using matplotlib fallback")
        return _generate_comprehensive_report_matplotlib(
            dataset_code, binary_metrics, state_metrics, residual_metrics,
            algorithm_info, output_path
        )

    try:
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Custom styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,
            spaceAfter=20,
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
        )

        # Title
        story.append(Paragraph("UCT Benchmark Evaluation Report", title_style))
        story.append(Spacer(1, 12))

        # Report metadata
        story.append(Paragraph(f"Dataset: {dataset_code}", styles['Normal']))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        ))
        story.append(Paragraph(
            f"Algorithm: {algorithm_info.get('name', 'Unknown')} "
            f"v{algorithm_info.get('version', '1.0')}",
            styles['Normal']
        ))
        story.append(Spacer(1, 24))

        # Section 1: Executive Summary
        story.append(Paragraph("1. Executive Summary", section_style))
        story.append(Spacer(1, 6))

        summary_data = [
            ['Metric', 'Value'],
            ['Accuracy', f"{binary_metrics.get('Accuracy', 0):.4f}"],
            ['F1 Score', f"{binary_metrics.get('F1Score', binary_metrics.get('F1', 0)):.4f}"],
            ['True Positives', str(binary_metrics.get('TruePositives', binary_metrics.get('True Positive', 0)))],
            ['True Negatives', str(binary_metrics.get('TrueNegatives', binary_metrics.get('True Negative', 0)))],
            ['Position Error (km)', f"{state_metrics.get('l2_position_km', state_metrics.get('position_error_mean_km', 0)):.3f}"],
            ['Velocity Error (km/s)', f"{state_metrics.get('l2_velocity_km_s', state_metrics.get('velocity_error_mean_km_s', 0)):.6f}"],
        ]
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 24))

        # Section 2: Binary Classification Metrics
        story.append(Paragraph("2. Binary Classification Metrics", section_style))
        story.append(Spacer(1, 6))

        # 2.1 Confusion Matrix
        story.append(Paragraph("2.1 Confusion Matrix", styles['Heading3']))

        tp = binary_metrics.get('TruePositives', binary_metrics.get('True Positive', 0))
        tn = binary_metrics.get('TrueNegatives', binary_metrics.get('True Negative', 0))
        fp = binary_metrics.get('FalsePositives', binary_metrics.get('False Positive', 0))
        fn = binary_metrics.get('FalseNegatives', binary_metrics.get('False Negative', 0))

        confusion_data = [
            ['', 'Predicted Positive', 'Predicted Negative'],
            ['Actual Positive', f'TP: {tp}', f'FN: {fn}'],
            ['Actual Negative', f'FP: {fp}', f'TN: {tn}'],
        ]
        confusion_table = Table(confusion_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
        confusion_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('BACKGROUND', (1, 1), (1, 1), colors.lightgreen),  # TP
            ('BACKGROUND', (2, 2), (2, 2), colors.lightgreen),  # TN
            ('BACKGROUND', (2, 1), (2, 1), colors.salmon),      # FN
            ('BACKGROUND', (1, 2), (1, 2), colors.salmon),      # FP
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(confusion_table)
        story.append(Spacer(1, 12))

        # 2.2 Detailed metrics table
        story.append(Paragraph("2.2 Detailed Metrics", styles['Heading3']))

        metrics_data = [
            ['Metric', 'Value', 'Description'],
            ['Accuracy', f"{binary_metrics.get('Accuracy', 0):.4f}", '(TP+TN)/(TP+TN+FP+FN)'],
            ['Precision', f"{binary_metrics.get('Precision', 0):.4f}", 'TP/(TP+FP)'],
            ['Sensitivity (Recall)', f"{binary_metrics.get('Sensitivity', binary_metrics.get('Recall', 0)):.4f}", 'TP/(TP+FN)'],
            ['Specificity', f"{binary_metrics.get('Specificity', 0):.4f}", 'TN/(TN+FP)'],
            ['F1 Score', f"{binary_metrics.get('F1Score', binary_metrics.get('F1', 0)):.4f}", 'Harmonic mean of P and R'],
            ["Cohen's Kappa", f"{binary_metrics.get('CohenKappa', binary_metrics.get('Kappa', 0)):.4f}", 'Inter-rater agreement'],
            ['Matthews Corr.', f"{binary_metrics.get('MatthewsCorrCoef', binary_metrics.get('MCC', 0)):.4f}", 'Balanced measure'],
        ]
        metrics_table = Table(metrics_data, colWidths=[1.8*inch, 1*inch, 2.5*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(metrics_table)
        story.append(PageBreak())

        # Section 3: State Estimation Metrics
        story.append(Paragraph("3. State Estimation Metrics", section_style))
        story.append(Spacer(1, 6))

        state_data = [
            ['Metric', 'Value', 'Unit'],
            ['L2 Position Error', f"{state_metrics.get('l2_position_km', state_metrics.get('position_error_mean_km', 0)):.6f}", 'km'],
            ['L2 Velocity Error', f"{state_metrics.get('l2_velocity_km_s', state_metrics.get('velocity_error_mean_km_s', 0)):.9f}", 'km/s'],
            ['X Bias', f"{state_metrics.get('x_bias_km', 0):.6f}", 'km'],
            ['Y Bias', f"{state_metrics.get('y_bias_km', 0):.6f}", 'km'],
            ['Z Bias', f"{state_metrics.get('z_bias_km', 0):.6f}", 'km'],
            ['Mahalanobis Distance', f"{state_metrics.get('mahalanobis_distance', 'N/A')}", ''],
            ['NEES', f"{state_metrics.get('nees', 'N/A')}", ''],
            ['NEES p-score', f"{state_metrics.get('nees_p_score', 'N/A')}", ''],
        ]
        state_table = Table(state_data, colWidths=[2*inch, 2*inch, 1*inch])
        state_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(state_table)
        story.append(Spacer(1, 24))

        # Section 4: Residual Analysis
        story.append(Paragraph("4. Residual Analysis", section_style))
        story.append(Spacer(1, 6))

        residual_data = [
            ['Statistic', 'Value (arcsec)'],
            ['Mean', f"{residual_metrics.get('residual_mean_arcsec', 0):.4f}"],
            ['Std Dev', f"{residual_metrics.get('residual_std_arcsec', 0):.4f}"],
            ['RMS', f"{residual_metrics.get('residual_rms_arcsec', 0):.4f}"],
            ['Median', f"{residual_metrics.get('residual_median_arcsec', 0):.4f}"],
            ['Max', f"{residual_metrics.get('residual_max_arcsec', 0):.4f}"],
            ['Min', f"{residual_metrics.get('residual_min_arcsec', 0):.4f}"],
        ]
        residual_table = Table(residual_data, colWidths=[2*inch, 2*inch])
        residual_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        story.append(residual_table)

        # Build PDF
        doc.build(story)
        logger.info(f"Comprehensive PDF report saved to: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"Failed to generate comprehensive PDF report: {e}")
        raise


def _generate_comprehensive_report_matplotlib(
    dataset_code: str,
    binary_metrics: Dict[str, Any],
    state_metrics: Dict[str, Any],
    residual_metrics: Dict[str, Any],
    algorithm_info: Dict[str, Any],
    output_path: str,
) -> str:
    """Fallback matplotlib-based comprehensive report generation."""
    if not MATPLOTLIB_AVAILABLE:
        logger.error("matplotlib not available for PDF generation")
        return ""

    try:
        with PdfPages(output_path) as pdf:
            # Title page
            fig = plt.figure(figsize=(11, 8.5))
            fig.text(0.5, 0.65, "UCT Benchmark Evaluation Report",
                    ha='center', va='center', fontsize=24, fontweight='bold')
            fig.text(0.5, 0.55, f"Dataset: {dataset_code}",
                    ha='center', va='center', fontsize=14)
            fig.text(0.5, 0.45, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    ha='center', va='center', fontsize=12)
            fig.text(0.5, 0.35, f"Algorithm: {algorithm_info.get('name', 'Unknown')}",
                    ha='center', va='center', fontsize=12)
            pdf.savefig(fig)
            plt.close(fig)

            # Confusion matrix page
            fig, ax = plt.subplots(figsize=(11, 8.5))
            tp = binary_metrics.get('TruePositives', binary_metrics.get('True Positive', 0))
            tn = binary_metrics.get('TrueNegatives', binary_metrics.get('True Negative', 0))
            fp = binary_metrics.get('FalsePositives', binary_metrics.get('False Positive', 0))
            fn = binary_metrics.get('FalseNegatives', binary_metrics.get('False Negative', 0))

            confusion_matrix = np.array([[tp, fn], [fp, tn]])
            im = ax.imshow(confusion_matrix, cmap='RdYlGn')

            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(['Predicted Positive', 'Predicted Negative'])
            ax.set_yticklabels(['Actual Positive', 'Actual Negative'])

            for i in range(2):
                for j in range(2):
                    text = ax.text(j, i, f"{confusion_matrix[i, j]}",
                                  ha='center', va='center', fontsize=20)

            ax.set_title('Confusion Matrix', fontsize=16)
            fig.colorbar(im)
            pdf.savefig(fig)
            plt.close(fig)

            # Metrics summary page
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis('off')

            metrics_text = "Summary Metrics\n" + "=" * 50 + "\n\n"
            metrics_text += f"Accuracy:    {binary_metrics.get('Accuracy', 0):.4f}\n"
            metrics_text += f"Precision:   {binary_metrics.get('Precision', 0):.4f}\n"
            metrics_text += f"Recall:      {binary_metrics.get('Sensitivity', 0):.4f}\n"
            metrics_text += f"F1 Score:    {binary_metrics.get('F1Score', binary_metrics.get('F1', 0)):.4f}\n\n"
            metrics_text += f"Position Error (km):   {state_metrics.get('l2_position_km', 0):.6f}\n"
            metrics_text += f"Velocity Error (km/s): {state_metrics.get('l2_velocity_km_s', 0):.9f}\n\n"
            metrics_text += f"Residual RMS (arcsec): {residual_metrics.get('residual_rms_arcsec', 0):.4f}\n"

            ax.text(0.1, 0.9, metrics_text, transform=ax.transAxes,
                   fontsize=14, verticalalignment='top', fontfamily='monospace')
            pdf.savefig(fig)
            plt.close(fig)

        logger.info(f"Comprehensive PDF report saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to generate matplotlib PDF report: {e}")
        return ""


def export_report_to_html(
    dataset_code: str,
    binary_metrics: Dict[str, Any],
    state_metrics: Dict[str, Any],
    residual_metrics: Dict[str, Any],
    algorithm_info: Dict[str, Any],
    output_path: str,
) -> str:
    """
    Export evaluation report to HTML format.

    Args:
        dataset_code: 16-character dataset code
        binary_metrics: Binary classification metrics
        state_metrics: State estimation metrics
        residual_metrics: Residual analysis metrics
        algorithm_info: Algorithm information
        output_path: Path for output HTML file

    Returns:
        Path to generated HTML file
    """
    tp = binary_metrics.get('TruePositives', binary_metrics.get('True Positive', 0))
    tn = binary_metrics.get('TrueNegatives', binary_metrics.get('True Negative', 0))
    fp = binary_metrics.get('FalsePositives', binary_metrics.get('False Positive', 0))
    fn = binary_metrics.get('FalseNegatives', binary_metrics.get('False Negative', 0))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UCT Benchmark Evaluation Report - {dataset_code}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric-value {{ font-weight: bold; }}
        .confusion-matrix {{ width: auto; }}
        .confusion-matrix td {{ text-align: center; width: 150px; }}
        .tp {{ background-color: #90EE90 !important; }}
        .tn {{ background-color: #90EE90 !important; }}
        .fp {{ background-color: #FFA07A !important; }}
        .fn {{ background-color: #FFA07A !important; }}
        .metadata {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>UCT Benchmark Evaluation Report</h1>

    <p class="metadata">
        Dataset: <strong>{dataset_code}</strong><br>
        Algorithm: {algorithm_info.get('name', 'Unknown')} v{algorithm_info.get('version', '1.0')}<br>
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>

    <h2>1. Executive Summary</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Accuracy</td><td class="metric-value">{binary_metrics.get('Accuracy', 0):.4f}</td></tr>
        <tr><td>F1 Score</td><td class="metric-value">{binary_metrics.get('F1Score', binary_metrics.get('F1', 0)):.4f}</td></tr>
        <tr><td>True Positives</td><td class="metric-value">{tp}</td></tr>
        <tr><td>True Negatives</td><td class="metric-value">{tn}</td></tr>
        <tr><td>Position Error</td><td class="metric-value">{state_metrics.get('l2_position_km', 0):.3f} km</td></tr>
        <tr><td>Velocity Error</td><td class="metric-value">{state_metrics.get('l2_velocity_km_s', 0):.6f} km/s</td></tr>
    </table>

    <h2>2. Confusion Matrix</h2>
    <table class="confusion-matrix">
        <tr><th></th><th>Predicted Positive</th><th>Predicted Negative</th></tr>
        <tr><th>Actual Positive</th><td class="tp">TP: {tp}</td><td class="fn">FN: {fn}</td></tr>
        <tr><th>Actual Negative</th><td class="fp">FP: {fp}</td><td class="tn">TN: {tn}</td></tr>
    </table>

    <h2>3. Binary Classification Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Description</th></tr>
        <tr><td>Accuracy</td><td>{binary_metrics.get('Accuracy', 0):.4f}</td><td>(TP+TN)/(TP+TN+FP+FN)</td></tr>
        <tr><td>Precision</td><td>{binary_metrics.get('Precision', 0):.4f}</td><td>TP/(TP+FP)</td></tr>
        <tr><td>Sensitivity (Recall)</td><td>{binary_metrics.get('Sensitivity', 0):.4f}</td><td>TP/(TP+FN)</td></tr>
        <tr><td>Specificity</td><td>{binary_metrics.get('Specificity', 0):.4f}</td><td>TN/(TN+FP)</td></tr>
        <tr><td>F1 Score</td><td>{binary_metrics.get('F1Score', binary_metrics.get('F1', 0)):.4f}</td><td>Harmonic mean of Precision and Recall</td></tr>
    </table>

    <h2>4. State Estimation Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Unit</th></tr>
        <tr><td>Position Error (L2)</td><td>{state_metrics.get('l2_position_km', 0):.6f}</td><td>km</td></tr>
        <tr><td>Velocity Error (L2)</td><td>{state_metrics.get('l2_velocity_km_s', 0):.9f}</td><td>km/s</td></tr>
        <tr><td>X Bias</td><td>{state_metrics.get('x_bias_km', 0):.6f}</td><td>km</td></tr>
        <tr><td>Y Bias</td><td>{state_metrics.get('y_bias_km', 0):.6f}</td><td>km</td></tr>
        <tr><td>Z Bias</td><td>{state_metrics.get('z_bias_km', 0):.6f}</td><td>km</td></tr>
    </table>

    <h2>5. Residual Analysis</h2>
    <table>
        <tr><th>Statistic</th><th>Value (arcsec)</th></tr>
        <tr><td>Mean</td><td>{residual_metrics.get('residual_mean_arcsec', 0):.4f}</td></tr>
        <tr><td>Std Dev</td><td>{residual_metrics.get('residual_std_arcsec', 0):.4f}</td></tr>
        <tr><td>RMS</td><td>{residual_metrics.get('residual_rms_arcsec', 0):.4f}</td></tr>
        <tr><td>Median</td><td>{residual_metrics.get('residual_median_arcsec', 0):.4f}</td></tr>
        <tr><td>Max</td><td>{residual_metrics.get('residual_max_arcsec', 0):.4f}</td></tr>
        <tr><td>Min</td><td>{residual_metrics.get('residual_min_arcsec', 0):.4f}</td></tr>
    </table>

    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
        Generated by UCT Benchmark Evaluation System
    </footer>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"HTML report saved to: {output_path}")
    return output_path
