Act like a senior developer writing documentation for an open-source API automation tool. Optimize for clarity, usability, and real-world execution.

You are generating a production-quality README.md file for a GitHub repository.

Repository Name:
YouTubePlaylistOrganizer

Purpose:
This project is an API-driven automation tool that connects to a user's YouTube account using OAuth2 and the YouTube Data API v3 to analyze, clean, and reorganize playlists.

Core Capabilities:
- Authenticate via Google OAuth2
- Retrieve all user playlists and playlist items
- Export playlist data to JSON and CSV
- Analyze playlists for duplicates, inefficiencies, and grouping opportunities
- Perform AI-assisted categorization of videos
- Generate a reorganization plan before making changes
- Apply changes only after explicit confirmation
- Default to dry-run mode for safety

Tech Stack:
- Python 3.12
- google-api-python-client
- google-auth-oauthlib
- typer (CLI interface)
- pandas (data processing)
- pydantic (data models)
- rich (CLI output formatting)
- python-dotenv (environment management)

Instructions:
Generate a complete, well-structured README.md file with the following sections:

1. Project Title and short description (clear and concise, no fluff)
2. Features (bullet list)
3. How It Works (step-by-step workflow)
4. Project Structure (realistic folder layout)
5. Setup Instructions:
   - Google Cloud project creation
   - Enabling YouTube Data API v3
   - Creating OAuth credentials
   - Installing dependencies
   - Environment variable setup
6. Required OAuth scopes
7. Usage Examples:
   - Authenticate
   - List playlists
   - Export data
   - Analyze playlists
   - Generate plan
   - Apply changes
8. Safety Model (dry-run, confirmation requirement)
9. API Quota Considerations (mention high cost of reorder operations)
10. Tech Stack summary
11. Roadmap (future enhancements)
12. Use Cases (practical scenarios)
13. Contributing guidelines
14. License section (MIT)

Formatting Requirements:
- Use clean markdown with headers, code blocks, and spacing
- Include example CLI commands in bash blocks
- Include sample output file names like playlist-plan.json
- Keep tone professional, direct, and developer-focused
- Do NOT include emojis
- Do NOT include unnecessary marketing language
- Avoid vague statements; be specific and practical

Output:
Return only the README.md content, fully formatted and ready to paste into a repository.