"""Feedback collector for gathering requirements and issues."""

import json
import os
from typing import Dict, List, Any
from datetime import datetime


class FeedbackCollector:
    """Collect feedback from various sources."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sources = config.get('feedback_sources', [])

    def collect_all(self) -> Dict[str, Any]:
        """Collect feedback from all configured sources."""
        feedback = {
            'items': [],
            'sources_checked': [],
            'errors': []
        }

        for source in self.sources:
            source_type = source.get('type')

            try:
                if source_type == 'file':
                    items = self._collect_from_file(source)
                elif source_type == 'logs':
                    items = self._collect_from_logs(source)
                else:
                    items = []

                feedback['items'].extend(items)
                feedback['sources_checked'].append({
                    'type': source_type,
                    'success': True,
                    'items_found': len(items)
                })

            except Exception as e:
                feedback['errors'].append({
                    'source': source_type,
                    'error': str(e)
                })
                feedback['sources_checked'].append({
                    'type': source_type,
                    'success': False,
                    'error': str(e)
                })

        return feedback

    def _collect_from_file(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect feedback from JSON file."""
        file_path = source.get('path')

        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            feedback_items = data.get('feedback_items', [])

            # Filter for open items only
            open_items = [
                item for item in feedback_items
                if item.get('status', '').lower() == 'open'
            ]

            # Enrich with source info
            for item in open_items:
                item['source'] = 'feedback_file'
                item['source_path'] = file_path

            return open_items

        except json.JSONDecodeError as e:
            raise Exception(f'Invalid JSON in feedback file: {e}')

    def _collect_from_logs(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect errors from log files."""
        log_path = source.get('path')
        max_lines = source.get('max_lines', 100)

        if not os.path.exists(log_path):
            return []

        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()

            # Get last N lines
            recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines

            # Parse errors (simple pattern matching)
            errors = []
            for i, line in enumerate(recent_lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['error', 'exception', 'traceback', 'failed']):
                    errors.append({
                        'id': f'log_error_{i}',
                        'type': 'bug',
                        'status': 'open',
                        'priority': 'high',
                        'title': f'Log error detected',
                        'description': line.strip(),
                        'source': 'error_log',
                        'source_path': log_path,
                        'created_at': datetime.now().isoformat()
                    })

            # Deduplicate similar errors (keep first occurrence)
            unique_errors = []
            seen_descriptions = set()

            for error in errors:
                desc_key = error['description'][:50]  # First 50 chars for comparison
                if desc_key not in seen_descriptions:
                    seen_descriptions.add(desc_key)
                    unique_errors.append(error)

            return unique_errors[:10]  # Return max 10 log errors

        except Exception as e:
            raise Exception(f'Error reading log file: {e}')

    def update_feedback_status(self, item_id: str, status: str, notes: str = None):
        """Update the status of a feedback item."""
        # Find the feedback file source
        feedback_file = None
        for source in self.sources:
            if source.get('type') == 'file':
                feedback_file = source.get('path')
                break

        if not feedback_file or not os.path.exists(feedback_file):
            return

        try:
            with open(feedback_file, 'r') as f:
                data = json.load(f)

            # Update the item
            updated = False
            for item in data.get('feedback_items', []):
                if item.get('id') == item_id:
                    item['status'] = status
                    if notes:
                        item['completion_notes'] = notes
                    item['completed_at'] = datetime.now().isoformat()
                    updated = True
                    break

            if updated:
                data['metadata']['last_updated'] = datetime.now().isoformat()

                with open(feedback_file, 'w') as f:
                    json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Error updating feedback status: {e}")
