"""Task executor using Claude Code CLI for autonomous development."""

import subprocess
import os
import json
import uuid
from typing import Dict, Any
from datetime import datetime


class Executor:
    """Execute tasks by invoking Claude Code CLI."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_path = config.get('project', {}).get('path')
        self.git_config = config.get('execution', {})
        self.session_file = '/opt/autonomous-dev-agent/state/sessions.json'
        self.sessions = self._load_sessions()

    def _load_sessions(self) -> Dict[str, str]:
        """Load session IDs for projects."""
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_sessions(self):
        """Save session IDs."""
        os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
        with open(self.session_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)

    def _get_project_session_id(self) -> str:
        """Get or create session ID for this project."""
        project_name = self.config.get('project', {}).get('name', 'default')

        if project_name not in self.sessions:
            self.sessions[project_name] = str(uuid.uuid4())
            self._save_sessions()

        return self.sessions[project_name]

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using Claude Code."""
        result = {
            'task_id': task.get('id'),
            'success': False,
            'changes_made': [],
            'commit_hash': None,
            'error': None,
            'execution_time': datetime.now().isoformat(),
            'output': '',
            'verification': None
        }

        try:
            # Build the prompt for Claude Code
            prompt = self._build_prompt(task)

            # Execute via Claude Code CLI
            execution_result = self._execute_via_claude_code(prompt, task)

            if execution_result.get('success'):
                result['output'] = execution_result.get('output', '')

                # Check if files were changed
                git_status = self._check_git_status()

                if git_status.get('has_changes'):
                    # Commit changes
                    commit_result = self._commit_changes(task)
                    result['commit_hash'] = commit_result.get('hash')
                    result['changes_made'] = commit_result.get('files', [])

                    # Push to remote if configured
                    if self.git_config.get('git_push', True):
                        self._push_changes()

                    # Fix permissions for web-accessible projects
                    self._fix_web_permissions()

                    # VERIFICATION: Test the implementation (only for critical tasks)
                    task_priority = task.get('priority', 'medium')
                    if task_priority == 'critical':
                        print(f"  → Running verification tests (critical task)...")
                        verification_result = self._verify_implementation(task)
                        result['verification'] = verification_result

                        if verification_result.get('passed'):
                            result['success'] = True
                            print(f"  ✓ Verification passed")
                        else:
                            result['success'] = False
                            result['error'] = f"Verification failed: {verification_result.get('issues', 'Unknown issue')}"
                            print(f"  ✗ Verification failed")
                    else:
                        # Skip verification for non-critical tasks
                        print(f"  → Skipping verification (priority: {task_priority}, only critical tasks are verified)")
                        result['success'] = True
                        result['verification'] = {'skipped': True, 'reason': 'Non-critical task'}
                else:
                    result['output'] += "\n\nNote: No file changes were made."
                    result['success'] = True  # No changes needed is OK

            else:
                result['error'] = execution_result.get('error')

        except Exception as e:
            result['error'] = str(e)

        return result

    def _get_project_context(self) -> str:
        """Get project-specific context for the prompt."""
        project_name = self.config.get('project', {}).get('name', '')

        if 'Banking' in project_name or 'banking' in project_name.lower():
            return f"""PROJECT CONTEXT:
- This is a UI prototype repository for banking interfaces
- Located at: {self.project_path}
- Tech stack: Pure HTML5/CSS3/JavaScript (no frameworks)
- Prototypes should be in the prototypes/ directory
- Use modern, clean UI design with banking aesthetics
- Make prototypes responsive and user-friendly
- Files are served directly by Apache web server
- Live URL: https://smartprototypes.net/UI_Prototypes/Banking_Prototypes/"""

        elif 'Family Run' in project_name:
            return f"""PROJECT CONTEXT:
- This is a Flask web application for tracking family running activities
- Located at: {self.project_path}
- Tech stack: Python/Flask, HTML/CSS/JavaScript, JSON storage
- Deployed at: https://smartprototypes.net/family_run/"""

        else:
            # Generic context
            return f"""PROJECT CONTEXT:
- Located at: {self.project_path}
- Review the existing codebase to understand the project structure"""

    def _build_prompt(self, task: Dict[str, Any]) -> str:
        """Build a detailed prompt for Claude Code."""
        task_type = task.get('type', 'feature')
        title = task.get('title', '')
        description = task.get('description', '')
        priority = task.get('priority', 'medium')

        # Get project-specific context
        project_name = self.config.get('project', {}).get('name', 'Unknown Project')
        project_context = self._get_project_context()

        prompt = f"""You are an autonomous developer working on the {project_name} project.

{project_context}

TASK DETAILS:
Type: {task_type}
Priority: {priority}
Title: {title}

Description:
{description}

INSTRUCTIONS:
"""

        if task_type == 'bug':
            prompt += """1. Analyze the codebase to understand the bug
2. Identify the root cause
3. Implement a fix
4. Test that the fix works
5. Ensure no regressions
6. Document any important changes in comments if needed"""

        elif task_type in ['feature', 'enhancement']:
            prompt += """1. Review the existing codebase to understand the architecture
2. Plan the implementation approach
3. Implement the feature following existing patterns
4. Test the implementation thoroughly
5. Ensure it integrates well with existing functionality
6. Keep the code clean and simple (avoid over-engineering)"""

        elif task_type == 'refactor':
            prompt += """1. Analyze the current code structure
2. Plan the refactoring approach
3. Refactor while maintaining all functionality
4. Test to ensure nothing broke
5. Keep changes focused and minimal"""

        elif task_type == 'docs':
            prompt += """1. Review what needs documentation
2. Write clear, concise documentation
3. Include examples where helpful
4. Update README if necessary"""

        elif task_type == 'test':
            prompt += """1. Identify what needs testing
2. Write comprehensive tests
3. Ensure tests pass
4. Add test documentation"""

        prompt += f"""

IMPORTANT GUIDELINES:
- Make all changes directly - no need to ask for approval
- Test your changes to verify they work
- Use git to commit changes when done (with a clear commit message)
- Keep changes simple and focused on the task
- Follow existing code style and patterns
- Don't over-engineer - implement what's needed, nothing more

WORKING DIRECTORY: {self.project_path}

Please implement this task now."""

        return prompt

    def _execute_via_claude_code(self, prompt: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task using Claude Code CLI."""
        try:
            # Get session ID for context persistence
            session_id = self._get_project_session_id()

            # Build the Claude Code command
            # Note: We use --no-session-persistence for stateless execution
            # This prevents "session already in use" errors
            cmd = [
                'claude',
                '--print',  # Non-interactive mode
                '--permission-mode', 'acceptEdits',  # Auto-accept edits
                '--tools', 'default',  # Enable all tools
                '--model', 'sonnet',  # Use Sonnet model
                '--no-session-persistence',  # Don't save session (prevents conflicts)
                '--output-format', 'text',  # Text output
                prompt
            ]

            # Execute Claude Code
            print(f"  → Invoking Claude Code (stateless execution)...")

            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout,
                    'session_id': session_id
                }
            else:
                return {
                    'success': False,
                    'error': f"Claude Code exited with code {result.returncode}\n{result.stderr}"
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Execution timed out after 10 minutes'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error executing Claude Code: {str(e)}'
            }

    def _check_git_status(self) -> Dict[str, Any]:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )

            has_changes = bool(result.stdout.strip())

            return {
                'has_changes': has_changes,
                'output': result.stdout
            }

        except subprocess.CalledProcessError as e:
            return {
                'has_changes': False,
                'error': str(e)
            }

    def _commit_changes(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Commit changes to git."""
        try:
            # Configure git user
            git_user_name = self.git_config.get('git_user_name', 'Autonomous Dev Agent')
            git_user_email = self.git_config.get('git_user_email', 'agent@smartprototypes.net')

            subprocess.run(
                ['git', 'config', 'user.name', git_user_name],
                cwd=self.project_path,
                check=True
            )
            subprocess.run(
                ['git', 'config', 'user.email', git_user_email],
                cwd=self.project_path,
                check=True
            )

            # Check for changes
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )

            if not status_result.stdout.strip():
                return {
                    'hash': None,
                    'files': [],
                    'message': 'No changes to commit'
                }

            # Get list of changed files
            changed_files = [
                line.strip().split(None, 1)[1]
                for line in status_result.stdout.strip().split('\n')
                if line.strip()
            ]

            # Add all changes
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=self.project_path,
                check=True
            )

            # Create commit message
            commit_msg = self._create_commit_message(task)

            # Commit
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=self.project_path,
                check=True
            )

            # Get commit hash
            hash_result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )

            commit_hash = hash_result.stdout.strip()

            return {
                'hash': commit_hash,
                'files': changed_files,
                'message': commit_msg
            }

        except subprocess.CalledProcessError as e:
            raise Exception(f'Git commit failed: {e}')

    def _create_commit_message(self, task: Dict[str, Any]) -> str:
        """Create a commit message for the task."""
        task_type = task.get('type', 'change')
        title = task.get('title', 'Automated change')

        type_prefix = {
            'bug': 'Fix',
            'feature': 'Add',
            'enhancement': 'Enhance',
            'refactor': 'Refactor',
            'docs': 'Update docs',
            'test': 'Add tests'
        }.get(task_type, 'Update')

        message = f"{type_prefix}: {title}\n\n"
        message += f"Task ID: {task.get('id')}\n"
        message += f"Source: {task.get('source', 'unknown')}\n\n"

        description = task.get('description', '')
        if description and len(description) < 500:
            message += f"{description}\n\n"

        message += "🤖 Automated commit by Autonomous Dev Agent"

        return message

    def _push_changes(self):
        """Push changes to remote repository."""
        try:
            branch = self.config.get('project', {}).get('branch', 'main')

            subprocess.run(
                ['git', 'push', 'origin', branch],
                cwd=self.project_path,
                check=True,
                timeout=60
            )

        except subprocess.CalledProcessError as e:
            raise Exception(f'Git push failed: {e}')
        except subprocess.TimeoutExpired:
            raise Exception('Git push timed out')

    def _fix_web_permissions(self):
        """Fix file permissions for web-accessible projects."""
        try:
            # Only fix permissions for projects in /var/www (web-accessible)
            if not self.project_path.startswith('/var/www'):
                return

            print(f"  → Fixing web permissions...")

            # Fix file permissions: 644 for files, 755 for directories
            # Files (HTML, CSS, JS, JSON, images)
            subprocess.run(
                rf"find {self.project_path} -type f \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.json' -o -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.gif' -o -name '*.svg' \) -exec chmod 644 {{}} \;",
                shell=True,
                check=False  # Don't fail if no files found
            )

            # Directories
            subprocess.run(
                rf"find {self.project_path} -type d -exec chmod 755 {{}} \;",
                shell=True,
                check=False
            )

            print(f"  ✓ Permissions fixed (644 for files, 755 for directories)")

        except Exception as e:
            # Don't fail the entire execution if permission fixing fails
            print(f"  ⚠ Warning: Could not fix permissions: {e}")

    def _verify_implementation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that the implementation actually works."""
        verification_prompt = f"""You are verifying a recently completed implementation.

TASK THAT WAS IMPLEMENTED:
Title: {task.get('title', '')}
Type: {task.get('type', '')}
Description: {task.get('description', '')}

YOUR JOB:
Verify that the implementation is complete and working correctly.

VERIFICATION STEPS:
1. Review the changes that were made
2. Check if the implementation matches the requirements
3. Test the functionality (run the app, test endpoints, check UI, etc.)
4. Verify no errors or broken functionality
5. Check if all edge cases are handled

IMPORTANT:
- Be thorough but practical
- Actually test the implementation (use curl, check files, run commands)
- For web features: test the HTTP endpoints work
- For UI features: check the files exist and are properly integrated
- Report ANY issues you find

OUTPUT FORMAT:
After your verification, provide a clear summary:

VERIFICATION RESULT: [PASS or FAIL]
ISSUES FOUND: [List any issues, or "None"]
CONFIDENCE: [High/Medium/Low]
NOTES: [Any additional observations]

Begin verification now."""

        try:
            # Execute verification using Claude Code
            cmd = [
                'claude',
                '--print',
                '--permission-mode', 'acceptEdits',
                '--tools', 'default',
                '--model', 'sonnet',
                '--no-session-persistence',
                '--output-format', 'text',
                verification_prompt
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for verification (critical tasks only)
            )

            if result.returncode == 0:
                output = result.stdout
                output_lower = output.lower()

                # Parse verification result - more flexible parsing
                # Look for "pass" after "verification result:" and not followed by "fail"
                passed = False
                if 'verification result:' in output_lower:
                    # Find the verification result section
                    result_section = output_lower.split('verification result:')[1].split('\n')[0]
                    # Check if it contains "pass" and doesn't contain "fail"
                    if 'pass' in result_section and 'fail' not in result_section:
                        passed = True

                # Alternative: Look for checkmark emoji or explicit PASS
                if '✅' in output or 'pass**' in output_lower or '**pass**' in output_lower:
                    # Double-check it's not a failure
                    if 'fail' not in output_lower[:output_lower.find('✅')] if '✅' in output else True:
                        passed = True

                # Extract issues if any
                issues = []
                if 'issues found:' in output_lower:
                    issues_section = output_lower.split('issues found:')[1].split('confidence:')[0].strip()
                    # Ignore "none" or empty issues
                    if issues_section and issues_section not in ['none', '**none**', 'none.']:
                        issues.append(issues_section)

                return {
                    'passed': passed,
                    'output': result.stdout,
                    'issues': '\n'.join(issues) if issues else None,
                    'verified_at': datetime.now().isoformat()
                }
            else:
                return {
                    'passed': False,
                    'output': result.stderr,
                    'issues': 'Verification process failed to run',
                    'verified_at': datetime.now().isoformat()
                }

        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'issues': 'Verification timed out after 10 minutes',
                'verified_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'passed': False,
                'issues': f'Verification error: {str(e)}',
                'verified_at': datetime.now().isoformat()
            }
