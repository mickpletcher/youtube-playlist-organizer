# Prompt 06: README Audit Reporting

Act like a senior DevOps engineer adding audit reporting to a README automation pipeline.

Repository:
YouTubePlaylistOrganizer

Goal:
Update the existing README refresh system so every run generates a readme-change-report.md file explaining what changed, why it changed, and what was skipped.

Files to update or create:

- scripts/update_readme.py
- .github/workflows/update-readme.yml
- readme-change-report.md

Requirements:

1. Generate readme-change-report.md on every run.

2. The report must include:
   - Run timestamp in UTC
   - Git commit SHA
   - Branch name
   - Changed files detected
   - Change categories detected
   - README sections evaluated
   - README sections updated
   - README sections skipped
   - Reason for each update or skip
   - Confidence score for each section
   - Whether README.md was modified
   - Whether a commit was created
   - Any warnings or errors
   - Recommended next actions

3. Report format:
   Use clean Markdown.

4. Example sections:

   ```markdown
   # README Change Report

   ## Run Metadata

   ## Changed Files

   ## Change Categories

   ## Section Decisions

   ## Updates Applied

   ## Skipped Sections

   ## Warnings

   ## Recommended Next Actions
   ```

5. Update scripts/update_readme.py:
   - Add a report generation function
   - Track decisions during section evaluation
   - Write readme-change-report.md even when no README changes are made
   - Include deterministic output except timestamp and git metadata
   - Use Python standard library only

6. Update .github/workflows/update-readme.yml:
   - Always upload readme-change-report.md as a workflow artifact
   - Commit report only when README.md changes
   - Do not create noisy commits for report only changes
   - Include report summary in GitHub Actions step summary
   - If using pull requests, include report content in PR body

7. Commit behavior:
   - If README.md changes, commit both:
     - README.md
     - readme-change-report.md
   - If only readme-change-report.md changes, do not commit
   - Always upload report as artifact

8. Safety:
   - Do not include secrets
   - Redact values from .env or token files
   - Do not include exported YouTube playlist data
   - Do not print OAuth tokens
   - Do not expose client secrets

9. Output:
   Generate the updated workflow, updated script, and a sample readme-change-report.md.

Output format:
Return all files clearly separated by path:

--- scripts/update_readme.py ---
[content goes here]

--- .github/workflows/update-readme.yml ---
[content goes here]

--- readme-change-report.md example ---
[content goes here]
