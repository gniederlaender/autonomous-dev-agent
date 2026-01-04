"""Health checker for monitoring application status."""

import requests
import subprocess
import json
from typing import Dict, List, Any


class HealthChecker:
    """Check application health across multiple dimensions."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.checks = config.get('health_checks', [])

    def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return results."""
        results = {
            'status': 'healthy',
            'checks': [],
            'critical_issues': [],
            'warnings': []
        }

        for check in self.checks:
            check_type = check.get('type')

            if check_type == 'http':
                result = self._check_http(check)
            elif check_type == 'api':
                result = self._check_api(check)
            elif check_type == 'pm2':
                result = self._check_pm2(check)
            else:
                result = {'status': 'unknown', 'message': f'Unknown check type: {check_type}'}

            results['checks'].append({
                'type': check_type,
                'config': check,
                'result': result
            })

            if not result.get('healthy', False):
                if result.get('critical', False):
                    results['critical_issues'].append(result)
                    results['status'] = 'critical'
                else:
                    results['warnings'].append(result)
                    if results['status'] == 'healthy':
                        results['status'] = 'degraded'

        return results

    def _check_http(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """Check HTTP endpoint availability."""
        url = check.get('url')
        expected_status = check.get('expected_status', 200)
        timeout = check.get('timeout', 10)

        try:
            response = requests.get(url, timeout=timeout, verify=True)
            healthy = response.status_code == expected_status

            return {
                'healthy': healthy,
                'status_code': response.status_code,
                'expected': expected_status,
                'message': f'HTTP check {"passed" if healthy else "failed"}: {url}',
                'critical': not healthy
            }
        except requests.exceptions.Timeout:
            return {
                'healthy': False,
                'critical': True,
                'message': f'HTTP check timeout: {url}',
                'error': 'timeout'
            }
        except Exception as e:
            return {
                'healthy': False,
                'critical': True,
                'message': f'HTTP check failed: {url}',
                'error': str(e)
            }

    def _check_api(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """Check API endpoint and validate JSON response."""
        url = check.get('url')
        timeout = check.get('timeout', 10)
        expected_json = check.get('expected_json', True)

        try:
            response = requests.get(url, timeout=timeout, verify=True)

            if response.status_code != 200:
                return {
                    'healthy': False,
                    'critical': True,
                    'message': f'API returned non-200 status: {response.status_code}',
                    'status_code': response.status_code
                }

            if expected_json:
                try:
                    data = response.json()
                    return {
                        'healthy': True,
                        'message': f'API check passed: {url}',
                        'data_preview': str(data)[:100]
                    }
                except json.JSONDecodeError:
                    return {
                        'healthy': False,
                        'critical': False,
                        'message': f'API returned invalid JSON: {url}'
                    }

            return {
                'healthy': True,
                'message': f'API check passed: {url}'
            }

        except Exception as e:
            return {
                'healthy': False,
                'critical': True,
                'message': f'API check failed: {url}',
                'error': str(e)
            }

    def _check_pm2(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """Check PM2 process status."""
        process_name = check.get('process_name')
        expected_status = check.get('expected_status', 'online')

        try:
            result = subprocess.run(
                ['pm2', 'jlist'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {
                    'healthy': False,
                    'critical': True,
                    'message': 'PM2 command failed',
                    'error': result.stderr
                }

            processes = json.loads(result.stdout)
            process = next((p for p in processes if p.get('name') == process_name), None)

            if not process:
                return {
                    'healthy': False,
                    'critical': True,
                    'message': f'PM2 process not found: {process_name}'
                }

            status = process.get('pm2_env', {}).get('status')
            healthy = status == expected_status

            return {
                'healthy': healthy,
                'status': status,
                'expected': expected_status,
                'message': f'PM2 process {process_name} is {status}',
                'critical': not healthy,
                'uptime': process.get('pm2_env', {}).get('pm_uptime'),
                'restarts': process.get('pm2_env', {}).get('restart_time', 0)
            }

        except Exception as e:
            return {
                'healthy': False,
                'critical': True,
                'message': f'PM2 check failed for {process_name}',
                'error': str(e)
            }
