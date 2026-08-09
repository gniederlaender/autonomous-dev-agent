"""Main orchestrator for the autonomous dev agent."""

import yaml
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add agent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from health_checker import HealthChecker
from feedback_collector import FeedbackCollector
from task_processor import TaskProcessor
from executor import Executor
from escalator import Escalator
from reporter import Reporter


class Orchestrator:
    """Orchestrate the autonomous development workflow."""

    def __init__(self, config_path: str):
        """Initialize orchestrator with configuration."""
        self.config = self._load_config(config_path)
        self.state_file = '/opt/autonomous-dev-agent/state/state.json'

        # Initialize components
        self.health_checker = HealthChecker(self.config)
        self.feedback_collector = FeedbackCollector(self.config)
        self.task_processor = TaskProcessor(self.config)
        self.executor = Executor(self.config)
        self.escalator = Escalator(self.config)
        self.reporter = Reporter(self.config)

        # Load state
        self.state = self._load_state()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_state(self) -> Dict[str, Any]:
        """Load agent state from file."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)

        return {
            'runs': [],
            'last_run': None,
            'pending_escalations': []
        }

    def _save_state(self):
        """Save agent state to file."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def run(self) -> Dict[str, Any]:
        """Execute the main workflow."""
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        print(f"🤖 Autonomous Dev Agent - Starting Run {run_id}")
        print(f"📁 Project: {self.config.get('project', {}).get('name')}")
        print("-" * 60)

        run_result = {
            'run_id': run_id,
            'started_at': datetime.now().isoformat(),
            'health': {},
            'feedback': {},
            'tasks': [],
            'executed': [],
            'escalated': [],
            'errors': []
        }

        try:
            # Step 1: Health Check
            print("\n🏥 Step 1: Checking application health...")
            health = self.health_checker.check_all()
            run_result['health'] = health
            print(f"   Status: {health.get('status', 'unknown').upper()}")

            if health.get('critical_issues'):
                print(f"   ⚠️ Critical issues detected: {len(health.get('critical_issues', []))}")

            # Step 2: Collect Feedback
            print("\n📝 Step 2: Collecting feedback...")
            feedback = self.feedback_collector.collect_all()
            run_result['feedback'] = feedback
            print(f"   Feedback items found: {len(feedback.get('items', []))}")

            # Step 3: Derive Tasks
            print("\n📋 Step 3: Processing tasks...")
            tasks = self.task_processor.process_feedback(feedback, health)
            run_result['tasks'] = tasks
            print(f"   Tasks identified: {len(tasks)}")

            # Step 4: Execute Tasks
            print("\n⚙️ Step 4: Executing tasks...")
            for task in tasks:
                print(f"\n   Processing: {task.get('title', 'Untitled')}")

                # Step 5: Check if escalation is needed
                escalation_check = self.task_processor.should_escalate(task)

                if escalation_check.get('should_escalate'):
                    print(f"      🚨 Escalating to human...")
                    escalation = self.escalator.escalate_task(
                        task,
                        escalation_check.get('reasons', [])
                    )
                    run_result['escalated'].append(escalation)
                    print(f"      ✓ Escalation {'sent' if escalation.get('sent') else 'logged'}")

                else:
                    # Execute the task
                    print(f"      ⚙️ Executing task...")
                    try:
                        exec_result = self.executor.execute_task(task)
                        run_result['executed'].append({
                            'task': task,
                            'result': exec_result
                        })

                        if exec_result.get('success'):
                            print(f"      ✓ Task completed successfully")
                            if exec_result.get('commit_hash'):
                                print(f"      ✓ Commit: {exec_result.get('commit_hash')}")

                            # Update feedback status with verification details
                            if task.get('source') == 'feedback_file':
                                feedback_item = task.get('feedback_item', {})
                                item_id = feedback_item.get('id')
                                if item_id:
                                    # Build completion notes with verification info
                                    verification = exec_result.get('verification', {})
                                    completion_notes = f"Completed by agent in run {run_id}"
                                    if verification:
                                        if verification.get('passed'):
                                            completion_notes += f"\n✓ Verification: PASSED"
                                        else:
                                            completion_notes += f"\n✗ Verification: FAILED - {verification.get('issues', 'Unknown')}"
                                    if exec_result.get('commit_hash'):
                                        completion_notes += f"\nCommit: {exec_result.get('commit_hash')}"

                                    self.feedback_collector.update_feedback_status(
                                        item_id,
                                        'done',
                                        completion_notes
                                    )
                        else:
                            if exec_result.get('timed_out'):
                                print(f"      ⏱ Task timed out: {exec_result.get('error')}")
                                print(f"      → Session saved. Re-run agent to continue where it left off.")
                            else:
                                print(f"      ❌ Task failed: {exec_result.get('error')}")
                            run_result['errors'].append({
                                'context': f"Task execution: {task.get('title')}",
                                'message': exec_result.get('error')
                            })

                    except Exception as e:
                        print(f"      ❌ Execution error: {str(e)}")
                        run_result['errors'].append({
                            'context': f"Task execution: {task.get('title')}",
                            'message': str(e)
                        })

            # Step 6: Generate Report
            print("\n📊 Step 5: Generating report...")
            report = self.reporter.generate_report(
                health=run_result['health'],
                feedback=run_result['feedback'],
                tasks=run_result['tasks'],
                executed=run_result['executed'],
                escalated=run_result['escalated'],
                errors=run_result['errors']
            )

            # Save report
            report_path = self.reporter.save_report(report)
            print(f"   ✓ Report saved: {report_path}")

            # Send report
            if self.reporter.send_report(report, report_path):
                print(f"   ✓ Report sent via email")
            else:
                print(f"   ℹ️ Email not configured or failed")

            run_result['report_path'] = report_path

        except Exception as e:
            print(f"\n❌ Fatal error during execution: {str(e)}")
            run_result['errors'].append({
                'context': 'Orchestrator',
                'message': str(e),
                'fatal': True
            })

        finally:
            # Save run result to state
            run_result['completed_at'] = datetime.now().isoformat()
            self.state['runs'].append(run_result)
            self.state['last_run'] = run_result
            self._save_state()

        # Summary
        print("\n" + "=" * 60)
        print("🏁 Run Complete")
        print(f"   Tasks executed: {len(run_result.get('executed', []))}")
        print(f"   Tasks escalated: {len(run_result.get('escalated', []))}")
        print(f"   Errors: {len(run_result.get('errors', []))}")
        print("=" * 60)

        return run_result


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <config_file>")
        sys.exit(1)

    config_path = sys.argv[1]

    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    orchestrator = Orchestrator(config_path)
    result = orchestrator.run()

    # Exit with error code if there were errors
    if result.get('errors'):
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
