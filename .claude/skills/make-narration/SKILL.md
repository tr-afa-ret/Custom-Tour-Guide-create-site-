---
name: make-narration
description: Generate or update the Russian audio narration (MP3 + timing JSON) for the guide site's stop pages with tools/make_audio.py, using Azure, ElevenLabs or edge-tts. Covers choosing and testing voices, spoken forms of numbers (data-say), samples, caching, costs and errors. Use after the story texts are written and approved, or when a story changes.
---

# Narration

`tools/make_audio.py` voices the `<h2>`/`<p>` blocks inside `#story` of each page. It joins them into one MP3 and writes the path given in the page's `data-audio` attribute, plus a `.json` file with the start time of each block. `site/js/audio.js` uses those times to highlight the paragraph being read. Run it from the project root:

```
python tools/make_audio.py site/<section>/<slug>.html     # one page
python tools/make_audio.py site/<section>                 # a folder
python tools/make_audio.py                                # everything under site/
  --engine azure|elevenlabs|edge   (pass the engine agreed in CLAUDE.md → Project)
  --voice ID        ElevenLabs voice (default: ELEVENLABS_VOICE_ID)
  --sample-dir DIR  write test MP3s to DIR instead of the site
  --list-voices     list ElevenLabs voices (account + Russian library voices)
  --force           rebuild even if up to date
```

Azure and ElevenLabs use only the standard library, so the system Python is enough. `edge` needs `tools/.venv` with `tools/requirements.txt` (edge-tts 7.3.1 from PyPI).

## Rules

- **Batch at the end:** write and approve all pages first, then generate audio once. Don't voice text that is still changing.
- **Caching:** every block is cached in `tools/audio-cache/` under a hash of engine, voice, settings and text. Editing one paragraph re-voices only that paragraph. Pages whose blocks are all unchanged are skipped. The cache key includes the engine and voice, so switching either re-voices everything. When some pages should keep their old recording, pass explicit pages instead of the whole `site/`.
- **Paid engines:** before a batch, estimate the characters (the length of the story text) and tell the user. Run it only after their OK.
- Never edit `site/audio/` by hand.

## Choosing a voice (new site or new engine)

1. Pick one page as the test, usually the first stop.
2. ElevenLabs: run `--list-voices`. After hearing the premade multilingual voices (Charlotte, Alice, George), the user moved to **native Russian voices** from the library. Candidates already tested: **Maxim** `HcaxAsrhw4ByUo4CBCBN` (male) and **Elena** `6uI7rxtNHAo4TLzDgyqr` (female). A library voice must first be added to the account ("Add to my voices") before the API can use it.
3. Generate samples: `--sample-dir tools/samples --voice ID`. Copy them to readable names such as `tools/samples/4 Maxim (male).mp3` and let the user listen. Only the test page is touched.
4. When the user picks a voice, put it in `.env` (`ELEVENLABS_VOICE_ID`) and CLAUDE.md → Project.

## Numbers and other spoken forms

- ElevenLabs misreads digits, especially years and ranges ("1442–1444 годах"). Wrap them in `data-say` with the full spoken form in the **correct grammatical case**. The visible text stays the same:
  `в <span data-say="тысяча четыреста сорок втором – тысяча четыреста сорок четвёртом">1442–1444</span> годах`
- `data-say` also fixes a mispronounced foreign name or word: put a phonetic Russian spelling in it, and re-voice that page only.
- Centuries, measures and the like are best written as words directly in the text.
- Check the parser output before paying for audio:
  ```
  python -c "import sys; sys.path.insert(0,'tools'); import make_audio as m; p=m.PageParser(); p.feed(open('site/<section>/<slug>.html',encoding='utf-8').read()); print('\n\n'.join(p.blocks))"
  ```
- When a user asks to fix pronunciation on one page, do **only that page**. Offer to do the rest afterwards.

## Known problems and fixes (already handled in the tool)

- **edge-tts** drops requests at random ("No audio was received"). The tool retries with a backoff, but it is still slow. Use it only as a free fallback.
- **Azure:** dropped connections (`IncompleteRead`) are retried. A 401 means the key is wrong, or the resource is switched off or in a different region (check `AZURE_SPEECH_REGION`).
- **ElevenLabs:** a 401/403 on `/voices` means the key lacks the "Voices: read" permission. A 404 on a voice means it isn't in the account. A 429 makes the tool wait for `Retry-After`.
- Block times are measured from the MP3 frames, so any bitrate works. ElevenLabs uses `mp3_44100_128` (~1 MB per minute); Azure uses 48 kbit/s mono (~0.35 MB per minute). Keep the total size of the site's audio in mind for phones on mobile data.

## After generating

- Report per page: duration, size, how many blocks were new and how many came from the cache, plus the total.
- Test on the phone: play, the highlighting follows the text, speed, the seek bar, and the lock-screen controls.
