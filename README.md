# Russian tour-guide site: starter kit

Building blocks for a new mobile audio-guide website (Russian, Chrome on Android), based on the Gdańsk site.

## Start a new site

1. Copy everything in this folder (including the hidden `.claude/`, `.gitignore` and `.env.example`) into a new, empty project folder.
2. Copy your `.env` from an earlier project, or copy `.env.example` to `.env` and fill it in. Set `AUDIO_ENGINE` once you've decided on audio.
3. Optional, only for the free `edge` voice engine: `python -m venv tools/.venv` then `tools/.venv/Scripts/pip install -r tools/requirements.txt`. Azure and ElevenLabs need only plain Python.
4. Open the folder in Claude Code and say hi. Claude notices there is no `site/` yet and starts the kickoff: location, audio, which places to visit, then the plan.

## What's inside

| Path | What |
|---|---|
| `CLAUDE.md` | Project rules plus a "Project" section that Claude fills in during kickoff |
| `.claude/skills/` | `new-guide-site`, `build-tour`, `build-list-page`, `make-narration` |
| `templates/site/` | Shared CSS and JS (player, text size, tour map), copied into `site/` |
| `templates/pages/` | Page skeletons with `{{PLACEHOLDERS}}` |
| `templates/examples/` | Finished Gdańsk pages, kept as a reference for quality and markup |
| `tools/make_audio.py` | Narration generator (Azure / ElevenLabs / edge), with per-paragraph caching |

Only `site/` is uploaded. `templates/`, `tools/`, `.claude/` and `.env` stay local.
