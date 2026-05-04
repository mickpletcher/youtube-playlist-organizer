Act like a senior DevOps engineer designing a self-healing documentation system for a production GitHub repository. Optimize for reliability, idempotency, and low maintenance.

You are generating a complete GitHub Actions workflow and supporting script to automatically update README.md when the repository code changes.

Repository:
YouTubePlaylistOrganizer

Goal:
When code or project structure changes, automatically regenerate or update README.md so it stays accurate with the current implementation.

Requirements:

1. Create a GitHub Actions workflow file at:
   .github/workflows/update-readme.yml

2. Trigger conditions:
   - On push to main branch
   - Only when files change in:
     src/**
     requirements.txt
     pyproject.toml
     README.md (optional)
     docs/**
   - Also allow manual trigger via workflow_dispatch

3. Workflow behavior:
   - Checkout repository
   - Set up Python 3.12
   - Install dependencies (requirements.txt if present)
   - Run a script that updates README.md based on the current codebase
   - Commit and push changes ONLY if README.md was modified

4. Create a Python script at:
   scripts/update_readme.py

5. Script responsibilities:
   - Read current README.md
   - Inspect project structure (src/, CLI commands, dependencies)
   - Extract CLI commands (from typer or main entry point if possible)
   - Validate that documented commands exist
   - Update sections:
     - Project Structure
     - Setup
     - Usage examples
     - Tech stack
   - Preserve manual sections like description and roadmap
   - Do NOT overwrite the entire file blindly
   - Only update specific sections marked with tags:

       <!-- AUTO-GENERATED:START -->
       <!-- AUTO-GENERATED:END -->

6. README update strategy:
   - Only modify content between AUTO-GENERATED markers
   - Leave the rest of README untouched
   - If markers do not exist, insert them into appropriate sections

7. Git commit logic:
   - Detect changes using git diff
   - Only commit if README.md changed
   - Commit message:
     "chore: auto-update README from codebase"

8. Permissions:
   - Use GITHUB_TOKEN for authentication

9. Safety:
   - Prevent infinite loops (do not retrigger on README-only changes)
   - Ensure idempotent updates

10. Output:
   Generate:
   - Full .github/workflows/update-readme.yml
   - Full scripts/update_readme.py
   - Example README markers section

Constraints:
- Use Python standard library where possible
- Keep script fast and deterministic
- No external AI APIs required
- Clean, production-quality code
- Add comments explaining key logic

Output format:
Return all files clearly separated with file paths:

--- .github/workflows/update-readme.yml ---
<content>

--- scripts/update_readme.py ---
<content>

--- README marker example ---
<content>