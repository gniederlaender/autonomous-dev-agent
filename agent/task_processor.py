"""Task processor for deriving and prioritizing tasks."""

from typing import Dict, List, Any
from datetime import datetime


class TaskProcessor:
    """Process feedback into actionable tasks and prioritize them."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_tolerance = config.get('risk_tolerance', 'medium')

    def process_feedback(self, feedback: Dict[str, Any], health: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert feedback items and health issues into tasks."""
        tasks = []

        # Add health issues as high-priority tasks
        for issue in health.get('critical_issues', []):
            tasks.append({
                'id': f"health_critical_{len(tasks)}",
                'type': 'bug',
                'priority': 'critical',
                'title': f"Fix critical health issue: {issue.get('message', 'Unknown')}",
                'description': str(issue),
                'source': 'health_check',
                'auto_execute': True,
                'created_at': datetime.now().isoformat()
            })

        for warning in health.get('warnings', []):
            tasks.append({
                'id': f"health_warning_{len(tasks)}",
                'type': 'bug',
                'priority': 'high',
                'title': f"Address health warning: {warning.get('message', 'Unknown')}",
                'description': str(warning),
                'source': 'health_check',
                'auto_execute': True,
                'created_at': datetime.now().isoformat()
            })

        # Add feedback items as tasks
        for item in feedback.get('items', []):
            task = self._convert_feedback_to_task(item)
            tasks.append(task)

        # Prioritize all tasks
        prioritized = self._prioritize_tasks(tasks)

        return prioritized

    def _convert_feedback_to_task(self, feedback_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a feedback item into a task."""
        item_type = feedback_item.get('type', 'feature')
        priority = feedback_item.get('priority', 'medium')

        # Determine if task can be auto-executed
        auto_execute = self._should_auto_execute(feedback_item)

        task = {
            'id': feedback_item.get('id', f"task_{datetime.now().timestamp()}"),
            'type': item_type,
            'priority': priority,
            'title': feedback_item.get('title', 'Untitled task'),
            'description': feedback_item.get('description', ''),
            'source': feedback_item.get('source', 'feedback'),
            'source_path': feedback_item.get('source_path'),
            'auto_execute': auto_execute,
            'feedback_item': feedback_item,
            'created_at': feedback_item.get('created_at', datetime.now().isoformat())
        }

        return task

    def _should_auto_execute(self, feedback_item: Dict[str, Any]) -> bool:
        """Determine if a feedback item should be auto-executed."""
        item_type = feedback_item.get('type', '').lower()
        priority = feedback_item.get('priority', 'medium').lower()
        title = feedback_item.get('title', '').lower()
        description = feedback_item.get('description', '').lower()

        # Check for escalation keywords
        escalation_keywords = [
            'security', 'vulnerability', 'breach', 'exploit',
            'breaking change', 'major refactor', 'deployment',
            'infrastructure', 'database migration', 'apache',
            'pm2', 'nginx', 'server config'
        ]

        combined_text = f"{title} {description}"
        if any(keyword in combined_text for keyword in escalation_keywords):
            return False  # Escalate instead

        # Auto-execute based on config
        autonomous_types = self.config.get('safety_rules', {}).get('autonomous_execution', [])

        type_mapping = {
            'bug': 'bug_fixes',
            'feature': 'new_features',
            'enhancement': 'new_features',
            'refactor': 'refactoring',
            'docs': 'documentation_updates',
            'test': 'test_additions',
            'dependency': 'dependency_updates'
        }

        allowed_type = type_mapping.get(item_type, item_type)

        return allowed_type in autonomous_types

    def _prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort tasks by priority."""
        priority_order = {
            'critical': 0,
            'high': 1,
            'medium': 2,
            'low': 3
        }

        def get_priority_score(task):
            priority = task.get('priority', 'medium').lower()
            return priority_order.get(priority, 2)

        return sorted(tasks, key=get_priority_score)

    def should_escalate(self, task: Dict[str, Any]) -> Dict[str, bool]:
        """Determine if a task should be escalated to human."""
        escalate = False
        reasons = []

        # Check if auto_execute is False
        if not task.get('auto_execute', False):
            escalate = True
            reasons.append("Task marked for escalation based on type or keywords")

        # Check priority
        if task.get('priority', '').lower() == 'critical':
            # Critical tasks can be auto-executed if they're health-related
            if task.get('source') != 'health_check' and self.risk_tolerance == 'low':
                escalate = True
                reasons.append("Critical priority with low risk tolerance")

        return {
            'should_escalate': escalate,
            'reasons': reasons
        }
