Act like a senior DevOps engineer designing a Claude skill pipeline for self maintaining GitHub documentation.

Repository:
YouTubePlaylistOrganizer

Goal:
Tie README.md into the existing Claude skill pipeline so the README stays fresh automatically when the repository changes.

Create a Claude skill that audits and updates README.md using the current repository code, docs, examples, and project metadata.

Skill name:
readme-refresh

Shortcut:
rr

Primary behavior:
When invoked, the skill should inspect the repository, compare README.md against the current implementation, and generate a safe update plan before modifying anything.

The skill must:

1. Read these files when present:
   - README.md
   - pyproject.toml
   - requirements.txt
   - package files
   - src/**
   - scripts/**
   - docs/**
   - examples/**
   - tests/**
   - .github/workflows/**

2. Detect:
   - outdated setup instructions
   - missing dependencies
   - incorrect CLI commands
   - stale project structure
   - undocumented features
   - roadmap items that are now implemented
   - safety notes that need updating
   - missing OAuth or API quota warnings

3. Preserve manual README sections unless they are clearly wrong.

4. Only modify auto managed sections between:

   <!-- README-REFRESH:START -->
   <!-- README-REFRESH:END -->

5. If markers do not exist, add them under appropriate sections.

6. Generate three outputs:
   - README audit summary
   - proposed README patch
   - updated README.md content

7. Default to dry run mode.
   Do not overwrite README.md unless the user explicitly says:
   apply README refresh

8. Include a weekly automation design:
   - GitHub Action runs on schedule
   - Action invokes Claude or uses a generated prompt file
   - Claude audits README.md
   - Changes are committed on a new branch
   - Pull request is opened for review

9. Create these files:

   .claude/skills/readme-refresh/SKILL.md
   .github/prompts/readme-refresh.prompt.md
   .github/workflows/readme-refresh.yml
   scripts/readme_refresh_context.py
   docs/readme-refresh.md

10. The GitHub Action should:
   - run weekly
   - run on workflow_dispatch
   - collect repo context
   - generate a README refresh prompt
   - avoid committing directly to main
   - create a pull request instead
   - label the PR as documentation and automation

11. Include security notes:
   - do not expose OAuth client secrets
   - do not print tokens
   - do not include user playlist data in README
   - do not commit generated exports
   - redact .env values

12. Include repo specific documentation expectations:
   - YouTube Data API v3 setup
   - OAuth scope explanation
   - playlist export workflow
   - dry run safety model
   - quota warnings
   - CLI command examples
   - JSON and CSV output examples

Style requirements:
- direct
- technical
- no fluff
- no emojis
- clean Markdown
- production ready
- compatible with GitHub Copilot and Claude

Output:
Generate all required files with full content, clearly separated by file path.