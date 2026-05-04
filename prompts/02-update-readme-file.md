You are updating an existing README.md for the YouTubePlaylistOrganizer repository.

Act like a senior developer maintaining documentation for an open-source API automation tool.

Goal:
Update README.md so it accurately reflects the current repository code, folder structure, CLI commands, dependencies, and workflow.

Instructions:
1. Inspect the current repository structure.
2. Read existing README.md.
3. Read pyproject.toml, requirements.txt, package files, CLI entry points, config files, docs, examples, and tests if present.
4. Identify anything in README.md that is outdated, missing, vague, or inaccurate.
5. Update README.md in place.
6. Preserve useful existing content.
7. Remove claims that are not supported by the current code.
8. Add missing setup steps, usage examples, and safety notes.
9. Ensure all commands are correct and runnable.
10. Include YouTube Data API v3 OAuth setup details.
11. Include dry-run behavior and confirmation requirements.
12. Include API quota warnings, especially playlist reorder operations.
13. Keep the tone direct, technical, and practical.

Required README sections:
- Project overview
- Features
- How it works
- Project structure
- Setup
- OAuth configuration
- Environment variables
- CLI usage
- Output files
- Safety model
- API quota notes
- Roadmap
- Contributing
- License

Formatting rules:
- Use clean Markdown.
- Use bash code blocks for commands.
- Use JSON or env code blocks where appropriate.
- Do not use emojis.
- Do not add marketing fluff.
- Do not invent features that are not implemented.
- Add a “Current Status” section if some features are planned but not built yet.
- Make the README useful for someone cloning the repo for the first time.

Output:
Update README.md directly.
After updating, summarize:
1. What changed
2. What assumptions were made
3. Any gaps in the repo that should be fixed next