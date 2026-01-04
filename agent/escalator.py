"""Escalation handler for tasks requiring human intervention."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from datetime import datetime


class Escalator:
    """Handle escalation of tasks to humans."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.escalation_config = config.get('escalation', {})

    def escalate_task(self, task: Dict[str, Any], reasons: List[str]) -> Dict[str, Any]:
        """Escalate a task to human for review."""
        escalation = {
            'task': task,
            'reasons': reasons,
            'escalated_at': datetime.now().isoformat(),
            'sent': False
        }

        method = self.escalation_config.get('method', 'email')

        if method == 'email':
            success = self._send_escalation_email(task, reasons)
            escalation['sent'] = success
            escalation['method'] = 'email'

        return escalation

    def _send_escalation_email(self, task: Dict[str, Any], reasons: List[str]) -> bool:
        """Send escalation email."""
        try:
            to_email = self.escalation_config.get('to')
            if not to_email:
                print("No escalation email configured")
                return False

            subject = f"[ESCALATION NEEDED] {task.get('title', 'Task requires review')}"

            body = self._format_escalation_email(task, reasons)

            # Use system mail command for simplicity
            import subprocess

            echo_process = subprocess.Popen(
                ['echo', body],
                stdout=subprocess.PIPE
            )

            mail_process = subprocess.Popen(
                ['mail', '-s', subject, to_email],
                stdin=echo_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            echo_process.stdout.close()
            mail_process.communicate(timeout=30)

            return mail_process.returncode == 0

        except Exception as e:
            print(f"Failed to send escalation email: {e}")
            return False

    def _format_escalation_email(self, task: Dict[str, Any], reasons: List[str]) -> str:
        """Format escalation email body."""
        body = f"""AUTONOMOUS DEV AGENT - ESCALATION REQUIRED

Task ID: {task.get('id')}
Type: {task.get('type', 'unknown')}
Priority: {task.get('priority', 'unknown')}
Title: {task.get('title', 'Untitled')}

ESCALATION REASONS:
"""

        for i, reason in enumerate(reasons, 1):
            body += f"{i}. {reason}\n"

        body += f"""

TASK DETAILS:
{task.get('description', 'No description provided')}

Source: {task.get('source', 'unknown')}
Created: {task.get('created_at', 'unknown')}

---
This task was flagged by the Autonomous Dev Agent and requires human decision-making.

Project: {self.config.get('project', {}).get('name', 'Unknown')}
Agent Run: {datetime.now().isoformat()}
"""

        return body
