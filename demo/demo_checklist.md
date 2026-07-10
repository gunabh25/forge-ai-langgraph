# ForgeAI Demo Checklist

## Pre-Demo Prep
- [ ] Ensure Python 3.10+ is active.
- [ ] Ensure `OPENAI_API_KEY` or `GOOGLE_API_KEY` is set in `.env`.
- [ ] Ensure Java is installed and accessible via CLI (`java -version`).
- [ ] Verify `plantuml.jar` is located in the correct directory.
- [ ] Run a dry-run of the prompt to prime any local caches and verify network connectivity.
- [ ] Open the `artifacts/` folder in a file explorer to show live SVG generation.

## During Demo
- [ ] Keep `demo_script.md` open on a secondary monitor.
- [ ] Have the `demo_prompt.md` ready to copy-paste.
- [ ] Terminal should be set to a large, readable font.
- [ ] Point out the parallel execution logs as they happen.
- [ ] Explicitly highlight the Compiler Validation step (force an error if possible, or explain how it catches them).
- [ ] Show the rendered SVGs natively in the browser or an image viewer.
- [ ] Execute the Incremental Update to demonstrate caching speed.
