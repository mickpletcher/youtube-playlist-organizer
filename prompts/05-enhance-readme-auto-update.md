# Prompt 05: Diff-Aware README Updates

Act like a senior DevOps engineer upgrading a documentation automation system to support diff-aware smart updates.

Repository:
YouTubePlaylistOrganizer

Goal:
Enhance the existing README auto-update system so it only updates documentation when actual code changes affect behavior, structure, or usage.

This system must detect meaningful changes in the codebase and selectively update only impacted sections of README.md.

---

## Core Requirements

1. Extend existing script:
   scripts/update_readme.py

2. Add diff analysis capability:
   - Use git to detect changed files:
       git diff --name-only HEAD~1 HEAD
   - Also support GitHub Actions context (GITHUB_SHA, GITHUB_BASE_REF)

3. Categorize changes into types:

   - CLI changes
     (files under src/cli, main.py, typer commands)

   - Dependency changes
     (requirements.txt, pyproject.toml)

   - Structure changes
     (new/removed folders in src/)

   - Docs changes
     (docs/, examples/)

   - Config changes
     (.env, config files)

4. Map change types to README sections:

   CLI changes → Usage section  
   Dependency changes → Setup section  
   Structure changes → Project Structure  
   Docs changes → Examples / Use Cases  
   Config changes → Environment Variables  

---

## Smart Update Logic

1. Only update sections that correspond to detected changes
2. Skip README update entirely if no relevant changes detected
3. Maintain section boundaries using markers:

   <!-- AUTO-GENERATED:START:SECTION_NAME -->
   <!-- AUTO-GENERATED:END:SECTION_NAME -->

   Example:
   <!-- AUTO-GENERATED:START:USAGE -->
   <!-- AUTO-GENERATED:END:USAGE -->

4. If markers do not exist:
   - Insert them cleanly under the correct header

5. Preserve:
   - manual descriptions
   - roadmap
   - contributing section

6. Generate a diff summary:

   Example output:
   - Updated Usage (CLI commands changed)
   - Updated Setup (dependencies modified)
   - Skipped Project Structure (no changes)

---

## GitHub Actions Enhancements

Update:
.github/workflows/update-readme.yml

Add:

- Step to capture changed files
- Pass changed file list to Python script
- Skip commit if script reports "no meaningful changes"

---

## Safety + Stability

- Prevent infinite commit loops
- Only commit if README.md content actually changed
- Use deterministic output (same input → same README)
- Fail gracefully if git diff is unavailable

---

## Output Requirements

Generate:

--- scripts/update_readme.py (updated) ---
Include:

- diff detection
- change categorization
- section targeting
- selective updates

--- .github/workflows/update-readme.yml (updated) ---
Include:

- changed file detection
- conditional execution
- commit guard

--- README marker examples ---
Show how to structure section markers for:

- Setup
- Usage
- Project Structure

---

## Constraints

- Use Python standard library only
- No external APIs
- Fast execution
- Clean, well-commented code
- Production-ready logic

---

## Bonus (optional but recommended)

Add a “confidence score” for updates:

- High confidence → auto-update
- Medium → update + log warning
- Low → skip and log suggestion

---

Output format:
Return all files clearly separated with file paths.
