# DevSync Bot

An automated bug fix assistant that processes Slack conversations, creates Jira tickets, and generates GitHub pull requests with code fixes.

## Features

- **Slack Integration**: Monitors threads and processes bug reports
- **Jira Integration**: Automatically creates tickets with structured bug information
- **GitHub Integration**: Generates pull requests with AI-powered code fixes
- **AI-Powered**: Uses Anthropic Claude for intelligent bug analysis and fix generation

## Quick Start

### 1. Setup

```bash
# Clone the repository
git clone <repository-url>
cd devsync

# Run setup script
python setup.py
```

### 2. Configuration

Create a `.env` file with the following variables:

```env
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Jira Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@domain.com
JIRA_API_TOKEN=your-jira-token
JIRA_PROJECT_KEY=YOUR_PROJECT
JIRA_ISSUE_TYPE=Task

# GitHub Configuration
GITHUB_TOKEN=ghp_your-github-token
GITHUB_REPO=owner/repository-name
GITHUB_DEFAULT_BRANCH=main

# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
```

### 3. Run the Bot

```bash
python slack_bot.py
```

## Usage

### In Slack

1. Start a thread describing a bug or issue
2. Mention `@DevSync` in the thread
3. The bot will:
   - Parse the conversation into a structured bug report
   - Create a Jira ticket
   - Analyze the codebase for context
   - Generate a code fix (if possible)
   - Create a GitHub pull request

### Example Workflow

```
User: "Login fails when users enter special characters in email field"
Support: "Error occurs in auth_handler.py line 45"
@DevSync
```

The bot will:
1. Create Jira ticket: `PROJ-123: Login fails with special characters`
2. Analyze `auth_handler.py` and related code
3. Generate a fix for the email validation issue
4. Create PR: `Fix: Email validation for special characters`

## Architecture

```
slack_bot.py          # Slack bot entry point
├── mcp_server.py     # Workflow orchestrator
├── services/
│   └── anthropic_service.py  # AI/LLM service
└── tools/
    ├── jira_tool.py      # Jira API integration
    └── github_tool.py    # GitHub API integration
```

## Requirements

- Python 3.8+
- Anthropic API key
- Jira Cloud instance
- GitHub repository
- Slack app with bot permissions

## Dependencies

- `slack-bolt` - Slack bot framework
- `anthropic` - Claude AI integration
- `PyGithub` - GitHub API client
- `jira` - Jira API client
- `python-dotenv` - Environment variable management

## Configuration Options

### Jira Settings
- `JIRA_ISSUE_TYPE`: Default issue type (Task, Bug, Story, etc.)
- `JIRA_PROJECT_KEY`: Project key for ticket creation

### GitHub Settings
- `GITHUB_DEFAULT_BRANCH`: Default branch for PR creation
- Repository must have write permissions for the bot

### AI Settings
- Uses Claude 3.5 Sonnet for bug analysis and fix generation
- Configurable temperature and token limits

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check Slack app permissions and token validity
2. **Jira ticket creation fails**: Verify project key and issue type exist
3. **GitHub PR creation fails**: Ensure repository access and branch permissions
4. **AI fix generation fails**: Check Anthropic API key and quota

### Logs

The bot outputs detailed logs to help diagnose issues:
- Workflow progress tracking
- API call results
- Error messages with context

## Development

### Project Structure

- `config.py` - Configuration management
- `mcp_server.py` - Main workflow logic
- `slack_bot.py` - Slack bot implementation
- `services/` - External service integrations
- `tools/` - API tool implementations

### Adding New Features

1. Extend the workflow in `mcp_server.py`
2. Add new tools in `tools/` directory
3. Update configuration in `config.py`
4. Test with the Slack bot

## License

[Add your license information here]

## Support

For issues and questions, please [create an issue](link-to-issues) or contact the development team.