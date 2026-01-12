"""Reporter for generating and sending execution reports."""

import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from datetime import datetime


class Reporter:
    """Generate and send execution reports."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.comm_config = config.get('communication', {})

    def generate_report(
        self,
        health: Dict[str, Any],
        feedback: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        executed: List[Dict[str, Any]],
        escalated: List[Dict[str, Any]],
        errors: List[Dict[str, Any]]
    ) -> str:
        """Generate a markdown report."""

        report = f"""# Autonomous Dev Agent Report
**Project:** {self.config.get('project', {}).get('name', 'Unknown')}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Status:** {'🟢 Healthy' if health.get('status') == 'healthy' else '🔴 Issues Detected'}

---

## Executive Summary

- **Health Status:** {health.get('status', 'unknown').upper()}
- **Feedback Items Processed:** {len(feedback.get('items', []))}
- **Tasks Identified:** {len(tasks)}
- **Tasks Executed:** {len(executed)}
- **Tasks Escalated:** {len(escalated)}
- **Errors:** {len(errors)}

---

## 🏥 Health Check Results

"""

        # Health check details
        if health.get('status') == 'healthy':
            report += "✅ All health checks passed successfully.\n\n"
        else:
            report += f"**Status:** {health.get('status', 'unknown').upper()}\n\n"

            if health.get('critical_issues'):
                report += "### Critical Issues\n"
                for issue in health.get('critical_issues', []):
                    report += f"- ❌ {issue.get('message', 'Unknown issue')}\n"
                report += "\n"

            if health.get('warnings'):
                report += "### Warnings\n"
                for warning in health.get('warnings', []):
                    report += f"- ⚠️ {warning.get('message', 'Unknown warning')}\n"
                report += "\n"

        # Health check details
        report += "### Check Details\n"
        for check in health.get('checks', []):
            check_type = check.get('type', 'unknown')
            result = check.get('result', {})
            status = '✅' if result.get('healthy') else '❌'
            report += f"- {status} **{check_type.upper()}**: {result.get('message', 'No message')}\n"

        report += "\n---\n\n"

        # Feedback section
        report += "## 📝 Feedback Processed\n\n"
        if feedback.get('items'):
            report += f"Collected {len(feedback.get('items', []))} feedback items:\n\n"
            for item in feedback.get('items', []):
                report += f"- **{item.get('title', 'Untitled')}** ({item.get('type', 'unknown')} - {item.get('priority', 'unknown')})\n"
                report += f"  - ID: {item.get('id')}\n"
                report += f"  - Source: {item.get('source', 'unknown')}\n"
        else:
            report += "No new feedback items found.\n"

        report += "\n---\n\n"

        # Tasks section
        report += "## 📋 Tasks Identified\n\n"
        if tasks:
            report += f"Identified {len(tasks)} tasks:\n\n"
            for task in tasks:
                priority_emoji = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(task.get('priority', 'medium').lower(), '⚪')

                report += f"{priority_emoji} **{task.get('title', 'Untitled')}**\n"
                report += f"   - Type: {task.get('type', 'unknown')}\n"
                report += f"   - Priority: {task.get('priority', 'unknown')}\n"
                report += f"   - Auto-execute: {'Yes' if task.get('auto_execute') else 'No'}\n\n"
        else:
            report += "No tasks identified.\n"

        report += "\n---\n\n"

        # Executed tasks section
        report += "## ✅ Tasks Executed\n\n"
        if executed:
            report += f"Successfully executed {len(executed)} tasks:\n\n"
            for exec_result in executed:
                task = exec_result.get('task', {})
                result = exec_result.get('result', {})

                status_emoji = '✅' if result.get('success') else '❌'
                report += f"{status_emoji} **{task.get('title', 'Untitled')}**\n"
                report += f"   - Task ID: {task.get('id')}\n"
                report += f"   - Type: {task.get('type', 'unknown')}\n"
                report += f"   - Priority: {task.get('priority', 'unknown')}\n"

                # Add task description if available
                if task.get('description'):
                    desc = task.get('description', '')
                    # Limit description length
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    report += f"   - Description: {desc}\n"

                if result.get('commit_hash'):
                    report += f"   - Commit: `{result.get('commit_hash')}`\n"

                if result.get('changes_made'):
                    files = result.get('changes_made', [])
                    report += f"   - Files changed ({len(files)}):\n"
                    for file in files[:10]:  # Limit to first 10 files
                        report += f"     - `{file}`\n"
                    if len(files) > 10:
                        report += f"     - ... and {len(files) - 10} more files\n"

                # Add verification results if available
                verification = result.get('verification', {})
                if verification and not verification.get('skipped'):
                    if verification.get('passed'):
                        report += f"   - ✓ Verification: PASSED\n"
                    else:
                        report += f"   - ✗ Verification: FAILED\n"
                        if verification.get('issues'):
                            report += f"     - Issues: {verification.get('issues')}\n"
                elif verification and verification.get('skipped'):
                    report += f"   - Verification: Skipped ({verification.get('reason', 'Non-critical task')})\n"

                # Add execution output summary (first 500 chars)
                if result.get('output'):
                    output = result.get('output', '')
                    # Extract meaningful parts (skip empty lines, limit length)
                    output_lines = [line.strip() for line in output.split('\n') if line.strip()]
                    if output_lines:
                        report += f"   - Execution Summary:\n"
                        summary = '\n'.join(output_lines[:15])  # First 15 non-empty lines
                        if len(summary) > 800:
                            summary = summary[:800] + "..."
                        # Indent each line for better formatting
                        for line in summary.split('\n'):
                            report += f"     {line}\n"

                if result.get('error'):
                    report += f"   - ❌ Error: {result.get('error')}\n"

                report += "\n"
        else:
            report += "No tasks were executed in this run.\n"

        report += "\n---\n\n"

        # Escalated tasks section
        report += "## 🚨 Tasks Escalated\n\n"
        if escalated:
            report += f"Escalated {len(escalated)} tasks for human review:\n\n"
            for escalation in escalated:
                task = escalation.get('task', {})
                reasons = escalation.get('reasons', [])

                report += f"🚨 **{task.get('title', 'Untitled')}**\n"
                report += f"   - Task ID: {task.get('id')}\n"
                report += f"   - Type: {task.get('type', 'unknown')}\n"
                report += f"   - Reasons:\n"

                for reason in reasons:
                    report += f"     - {reason}\n"

                report += "\n"
        else:
            report += "No tasks required escalation.\n"

        report += "\n---\n\n"

        # Errors section
        if errors:
            report += "## ❌ Errors\n\n"
            for error in errors:
                report += f"- **{error.get('context', 'Unknown context')}**: {error.get('message', 'Unknown error')}\n"
            report += "\n---\n\n"

        # Footer
        report += f"""
---

*Generated by Autonomous Dev Agent*
*Run ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}*
"""

        return report

    def save_report(self, report: str) -> str:
        """Save report to file."""
        report_path = self.comm_config.get('report_path', '/opt/autonomous-dev-agent/reports')
        os.makedirs(report_path, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_report.md"
        filepath = os.path.join(report_path, filename)

        with open(filepath, 'w') as f:
            f.write(report)

        return filepath

    def send_report(self, report: str, filepath: str) -> bool:
        """Send report via email using SMTP with authentication."""
        if not self.comm_config.get('email', {}).get('enabled', False):
            return False

        try:
            email_config = self.comm_config.get('email', {})

            to_email = email_config.get('to')
            from_email = email_config.get('from')
            smtp_host = email_config.get('smtp_host', 'localhost')
            smtp_port = email_config.get('smtp_port', 587)
            use_tls = email_config.get('use_tls', True)

            if not to_email or not from_email:
                print("Email 'to' and 'from' addresses must be configured")
                return False

            # Get password from environment
            email_password = os.environ.get('EMAIL_PASSWORD')
            if not email_password and smtp_host != 'localhost':
                print("EMAIL_PASSWORD environment variable not set")
                return False

            subject_prefix = email_config.get('subject_prefix', '[Auto-Agent]')
            project_name = self.config.get('project', {}).get('name', 'Unknown Project')
            subject = f"{subject_prefix} Daily Report - {project_name}"

            # Send complete report in email body (not just summary)
            # Users want to see all execution details in the email
            body = f"{report}\n\n---\n\nFull report also saved to:\n{filepath}"

            # Create email message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # Connect to SMTP server and send
            if smtp_host == 'localhost':
                # Local mail server (no auth needed)
                with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                    server.send_message(msg)
            else:
                # Remote SMTP server with authentication
                with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                    if use_tls:
                        server.starttls()
                    server.login(from_email, email_password)
                    server.send_message(msg)

            print(f"Report email sent successfully to {to_email}")
            return True

        except Exception as e:
            print(f"Failed to send report email: {e}")
            import traceback
            traceback.print_exc()
            return False
