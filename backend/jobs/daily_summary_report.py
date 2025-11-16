#!/usr/bin/env python3
"""
Daily Screener Summary Report

Generates a daily email report summarizing:
- Job execution status (success/failure)
- Stocks discovered per screener
- Error statistics (data errors vs rate limiting)
- Blacklist growth
- API usage metrics

Can be run as:
1. Cloud Run Job (scheduled daily at 11:00 AM ET)
2. Cloud Function (triggered daily)
3. Manual execution

Usage:
    python backend/jobs/daily_summary_report.py
    python backend/jobs/daily_summary_report.py --date 2025-11-15
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore, run_v2, logging as cloud_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailySummaryReport:
    """Generates daily summary report for screener batch jobs."""

    def __init__(self, project_id: str = "sylvan-earth-477020-u6"):
        """Initialize report generator."""
        self.project_id = project_id
        self.region = "us-east5"
        self.db = firestore.Client()
        self.logging_client = cloud_logging.Client()

    def get_yesterdays_screener_results(self, date_str: str) -> Dict[str, Any]:
        """
        Get screener results from Firestore for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dict with screener results
        """
        results = {}

        # Only check regular screeners (Smart Money disabled)
        screener_names = ["undiscovered", "coiled_spring"]

        for screener in screener_names:
            try:
                doc_ref = (
                    self.db
                    .collection("screeners")
                    .document(screener)
                    .collection("runs")
                    .document(date_str)
                )

                doc = doc_ref.get()
                if doc.exists:
                    results[screener] = doc.to_dict()
                else:
                    results[screener] = None
                    logger.warning(f"No results found for {screener} on {date_str}")

            except Exception as e:
                logger.error(f"Error fetching {screener} results: {e}")
                results[screener] = None

        return results

    def get_job_execution_stats(self, date_str: str) -> Dict[str, Any]:
        """
        Get job execution statistics from Cloud Run Jobs.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dict with execution stats
        """
        stats = {
            "regular_screeners": [],
        }

        # Query Cloud Run Jobs API for execution history
        # Note: This requires Cloud Run Admin API
        try:
            client = run_v2.JobsClient()

            # Get regular screener jobs (batches 1-5)
            for batch in range(1, 6):
                job_name = f"projects/{self.project_id}/locations/{self.region}/jobs/prod-regular-screeners-batch-{batch}"

                try:
                    # Get latest executions
                    request = run_v2.ListExecutionsRequest(parent=job_name, page_size=5)
                    executions = client.list_executions(request=request)

                    for execution in executions:
                        # Check if execution was from yesterday
                        exec_date = execution.create_time.date().isoformat()
                        if exec_date == date_str:
                            stats["regular_screeners"].append({
                                "batch": batch,
                                "status": execution.succeeded,
                                "start_time": execution.start_time,
                                "completion_time": execution.completion_time,
                            })
                            break

                except Exception as e:
                    logger.warning(f"Could not fetch executions for batch {batch}: {e}")

            # Smart Money screeners disabled - skipping

        except Exception as e:
            logger.error(f"Error fetching job execution stats: {e}")

        return stats

    def get_blacklist_stats(self) -> Dict[str, Any]:
        """Get delisted ticker blacklist statistics."""
        try:
            docs = self.db.collection("delisted_tickers").stream()

            total = 0
            error_types = {}
            added_yesterday = 0
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()

            for doc in docs:
                total += 1
                data = doc.to_dict()

                error_type = data.get("error_type", "unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1

                # Check if added yesterday
                first_detected = data.get("first_detected")
                if first_detected:
                    detected_date = first_detected.date() if hasattr(first_detected, 'date') else None
                    if detected_date == yesterday:
                        added_yesterday += 1

            return {
                "total_blacklisted": total,
                "error_types": error_types,
                "added_yesterday": added_yesterday,
            }

        except Exception as e:
            logger.error(f"Error getting blacklist stats: {e}")
            return {}

    def generate_html_report(
        self,
        date_str: str,
        screener_results: Dict[str, Any],
        job_stats: Dict[str, Any],
        blacklist_stats: Dict[str, Any]
    ) -> str:
        """Generate HTML email report."""

        # Calculate totals
        total_stocks_found = 0
        total_screened = 0
        total_errors = 0

        for screener_name, data in screener_results.items():
            if data:
                total_stocks_found += data.get("total_results", 0)
                total_screened += data.get("total_screened", 0)
                total_errors += data.get("failed_count", 0) + data.get("not_found_count", 0)

        # Job execution summary (Regular screeners only)
        regular_success = sum(1 for job in job_stats.get("regular_screeners", []) if job.get("status"))
        regular_total = len(job_stats.get("regular_screeners", []))

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .summary-box {{ background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                .metric-label {{ font-size: 12px; color: #7f8c8d; text-transform: uppercase; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #2c3e50; }}
                .success {{ color: #27ae60; }}
                .warning {{ color: #f39c12; }}
                .error {{ color: #e74c3c; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; }}
                tr:hover {{ background: #f8f9fa; }}
                .status-badge {{ padding: 4px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; }}
                .badge-success {{ background: #d4edda; color: #155724; }}
                .badge-error {{ background: #f8d7da; color: #721c24; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Daily Screener Report - {date_str}</h1>

                <div class="summary-box">
                    <div class="metric">
                        <div class="metric-label">Stocks Found</div>
                        <div class="metric-value success">{total_stocks_found}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Total Screened</div>
                        <div class="metric-value">{total_screened:,}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Total Errors</div>
                        <div class="metric-value warning">{total_errors}</div>
                    </div>
                </div>

                <h2>🎯 Screener Results</h2>
                <table>
                    <tr>
                        <th>Screener</th>
                        <th>Stocks Found</th>
                        <th>Total Screened</th>
                        <th>Not Found</th>
                        <th>Errors</th>
                        <th>Success Rate</th>
                    </tr>
        """

        # Add screener rows (Regular screeners only)
        for screener_name in ["undiscovered", "coiled_spring"]:
            data = screener_results.get(screener_name)
            display_name = screener_name.replace("_", " ").title()

            if data:
                found = data.get("total_results", 0)
                screened = data.get("total_screened", 0)
                not_found = data.get("not_found_count", 0)
                failed = data.get("failed_count", 0)
                success_rate = ((screened - failed - not_found) / screened * 100) if screened > 0 else 0

                html += f"""
                    <tr>
                        <td><strong>{display_name}</strong></td>
                        <td class="success">{found}</td>
                        <td>{screened:,}</td>
                        <td class="warning">{not_found}</td>
                        <td class="error">{failed}</td>
                        <td>{success_rate:.1f}%</td>
                    </tr>
                """
            else:
                html += f"""
                    <tr>
                        <td><strong>{display_name}</strong></td>
                        <td colspan="5" class="error">No data available</td>
                    </tr>
                """

        html += """
                </table>

                <h2>⚙️ Job Execution Status</h2>
                <p>
                    <strong>Regular Screeners (Undiscovered + Coiled Spring):</strong>
                    <span class="status-badge badge-success">{}/{} batches successful</span>
                </p>
                <p style="color: #7f8c8d; font-size: 14px;">
                    <em>Note: Smart Money screeners temporarily disabled (moving to Polygon.io)</em>
                </p>

                <h2>🚫 Blacklist Statistics</h2>
                <p>
                    <strong>Total Blacklisted Tickers:</strong> {}
                </p>
                <p>
                    <strong>Added Yesterday:</strong> <span class="warning">{}</span>
                </p>
                <p>
                    <strong>Error Types:</strong> {}
                </p>

                <hr style="margin: 40px 0; border: none; border-top: 1px solid #ecf0f1;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Generated automatically by GoingMerry-Stonks Batch Screener System<br>
                    Project: sylvan-earth-477020-u6 | Region: us-east5
                </p>
            </div>
        </body>
        </html>
        """.format(
            regular_success, regular_total,
            blacklist_stats.get("total_blacklisted", 0),
            blacklist_stats.get("added_yesterday", 0),
            str(blacklist_stats.get("error_types", {}))
        )

        return html

    def send_email_report(self, html_content: str, recipient: str, date_str: str):
        """
        Send email report using Gmail SMTP.

        Note: Requires GMAIL_APP_PASSWORD environment variable
        """
        sender = os.getenv("GMAIL_SENDER", "your-email@gmail.com")
        app_password = os.getenv("GMAIL_APP_PASSWORD")

        if not app_password:
            logger.warning("GMAIL_APP_PASSWORD not set - skipping email send")
            logger.info("Set up Gmail App Password: https://support.google.com/accounts/answer/185833")
            return

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Daily Screener Report - {date_str}"
        msg['From'] = sender
        msg['To'] = recipient

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender, app_password)
                smtp.send_message(msg)

            logger.info(f"✓ Email report sent to {recipient}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def generate_and_send_report(self, date_str: str = None, recipient: str = "brian.boatright@gmail.com"):
        """Generate and send daily summary report."""

        if date_str is None:
            # Default to yesterday's date
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            date_str = yesterday.strftime("%Y-%m-%d")

        logger.info(f"Generating daily summary report for {date_str}")

        # Collect data
        screener_results = self.get_yesterdays_screener_results(date_str)
        job_stats = self.get_job_execution_stats(date_str)
        blacklist_stats = self.get_blacklist_stats()

        # Generate HTML
        html_report = self.generate_html_report(
            date_str, screener_results, job_stats, blacklist_stats
        )

        # Save to file (for debugging)
        report_file = f"/tmp/screener_report_{date_str}.html"
        with open(report_file, "w") as f:
            f.write(html_report)
        logger.info(f"Report saved to {report_file}")

        # Send email
        self.send_email_report(html_report, recipient, date_str)

        logger.info("✓ Daily summary report complete")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description='Generate daily screener summary report')
    parser.add_argument('--date', help='Date to generate report for (YYYY-MM-DD)')
    parser.add_argument('--email', default='brian.boatright@gmail.com', help='Recipient email')
    parser.add_argument('--no-send', action='store_true', help='Generate report but don\'t send email')

    args = parser.parse_args()

    reporter = DailySummaryReport()

    if args.no_send:
        # Just generate and save to file
        date_str = args.date or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        screener_results = reporter.get_yesterdays_screener_results(date_str)
        job_stats = reporter.get_job_execution_stats(date_str)
        blacklist_stats = reporter.get_blacklist_stats()
        html_report = reporter.generate_html_report(date_str, screener_results, job_stats, blacklist_stats)

        report_file = f"/tmp/screener_report_{date_str}.html"
        with open(report_file, "w") as f:
            f.write(html_report)
        logger.info(f"Report saved to {report_file}")
        logger.info("Open in browser to preview")
    else:
        reporter.generate_and_send_report(date_str=args.date, recipient=args.email)


if __name__ == "__main__":
    main()
