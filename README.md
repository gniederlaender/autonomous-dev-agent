# Autonomous Dev Agent

An autonomous development agent that monitors applications, collects feedback, and automatically implements changes.

## Overview

This agent runs daily (via cron) and:
1. ✅ Checks application health
2. 📝 Collects feedback from configured sources
3. 📋 Derives actionable tasks
4. ⚙️ Executes tasks autonomously
5. 🚨 Escalates complex tasks to humans
6. 📊 Generates and sends reports

## Installation

Dependencies are installed in a virtual environment at `/opt/autonomous-dev-agent/venv/`.

**Setup API Key:**
```bash
# Copy the example env file
cp /opt/autonomous-dev-agent/.env.example /opt/autonomous-dev-agent/.env

# Edit and add your Anthropic API key
nano /opt/autonomous-dev-agent/.env
# Set: ANTHROPIC_API_KEY=sk-ant-...
```

The agent is now configured and ready to run.

## Configuration

Project configuration: `/opt/autonomous-dev-agent/config/family_run.yaml`

Key settings:
- **Project path**: `/opt/family_run`
- **Health checks**: HTTP, API, PM2 process
- **Feedback source**: `/opt/family_run/feedback.json`
- **Reports**: `/opt/autonomous-dev-agent/reports/`
- **Logs**: `/opt/autonomous-dev-agent/logs/`

## Usage

### Manual Run

```bash
/opt/autonomous-dev-agent/run_agent.sh
```

### View Logs

```bash
tail -f /opt/autonomous-dev-agent/logs/agent_*.log
```

### View Reports

```bash
ls -lt /opt/autonomous-dev-agent/reports/
cat /opt/autonomous-dev-agent/reports/<report_file>.md
```

### View State

```bash
cat /opt/autonomous-dev-agent/state/state.json | python3 -m json.tool
```

## Automated Schedule

Runs daily at 9:00 AM via cron:
```
0 9 * * * /opt/autonomous-dev-agent/run_agent.sh
```

View cron jobs:
```bash
crontab -l | grep autonomous
```

## Feedback System

Add feedback items to `/opt/family_run/feedback.json`:

```json
{
  "feedback_items": [
    {
      "id": "unique-id",
      "type": "feature|bug|enhancement|refactor|docs|test",
      "status": "open|done",
      "priority": "critical|high|medium|low",
      "title": "Short description",
      "description": "Detailed description of what needs to be done",
      "created_at": "2026-01-02",
      "notes": "Optional notes"
    }
  ]
}
```

The agent will:
- Process `status: "open"` items
- Execute tasks autonomously (based on safety rules)
- Update status to `"done"` when complete
- Escalate complex tasks to human

## Safety Rules

**Autonomous execution** (no approval needed):
- Documentation updates
- Test additions
- Bug fixes
- New features
- Refactoring
- Schema changes
- Dependency updates

**Always escalates** (requires human):
- Security vulnerabilities
- Breaking API changes
- Deployment/infrastructure changes

## Communication

- **Daily reports**: Emailed to `gabor.niederlaender@gmx.at`
- **Escalations**: Emailed when human decision needed
- **Reports saved**: `/opt/autonomous-dev-agent/reports/`

## Monitoring

Check last run:
```bash
cat /opt/autonomous-dev-agent/state/state.json | grep -A 20 '"last_run"'
```

Check health:
```bash
curl -s https://smartprototypes.net/family_run/api/data
```

## Extending to Other Projects

1. Copy config template:
   ```bash
   cp /opt/autonomous-dev-agent/config/family_run.yaml \
      /opt/autonomous-dev-agent/config/new_project.yaml
   ```

2. Update configuration for new project

3. Create `feedback.json` in project directory

4. Add cron job for new project:
   ```bash
   crontab -e
   # Add: 0 9 * * * /opt/autonomous-dev-agent/run_agent.sh new_project
   ```

## Architecture

```
orchestrator.py         Main workflow coordinator
├── health_checker.py   Monitor application health
├── feedback_collector.py  Collect requirements/issues
├── task_processor.py   Derive and prioritize tasks
├── executor.py         Execute tasks via Claude Code
├── escalator.py        Escalate to human when needed
└── reporter.py         Generate and send reports
```

## Files & Directories

- `/opt/autonomous-dev-agent/agent/` - Agent components
- `/opt/autonomous-dev-agent/config/` - Project configurations
- `/opt/autonomous-dev-agent/state/` - Agent state tracking
- `/opt/autonomous-dev-agent/reports/` - Generated reports
- `/opt/autonomous-dev-agent/logs/` - Execution logs
- `/opt/autonomous-dev-agent/run_agent.sh` - Cron entry point

## Troubleshooting

**Agent not running:**
```bash
# Check cron is active
systemctl status cron

# Check cron logs
grep autonomous /var/log/syslog
```

**No reports received:**
```bash
# Check reports directory
ls -lt /opt/autonomous-dev-agent/reports/

# Check mail configuration
echo "test" | mail -s "Test" gabor.niederlaender@gmx.at
```

**Tasks not executing:**
```bash
# Check logs
tail -100 /opt/autonomous-dev-agent/logs/agent_*.log

# Run manually for debugging
/opt/autonomous-dev-agent/run_agent.sh
```

## Version

- **Created**: 2026-01-02
- **Initial Project**: Family Run Tracker
- **Framework**: Reusable for multiple projects
