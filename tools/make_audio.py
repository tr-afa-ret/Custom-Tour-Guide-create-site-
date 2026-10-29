"""
Generate narration audio for sight pages.

For every page it reads the <h2>/<p> blocks inside #story, voices each block,
joins them into one MP3 and writes a JSON file with the start time of every block
(used by site/js/audio.js to highlight the paragraph being read).

The output path comes from the page itself: the data-audio="…" attribute of its
player (relative to the page), e.g. data-audio="../audio/old-town/crane.mp3".

Caching: every voiced block is stored in tools/audio-cache/ under a hash of
(engine, voice, settings, text). Editing one paragraph re-voices only that paragraph;
pages whose blocks are all unchanged are skipped.

Engines (keys live in the project's .env file, see .env.example):
  azure       official Azure AI Speech REST API, voice ru-RU-SvetlanaNeural.
              Needs AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.
  elevenlabs  ElevenLabs text-to-speech API. Needs ELEVENLABS_API_KEY and a voice id
              (ELEVENLABS_VOICE_ID or --voice). Model: ELEVENLABS_MODEL
              (default eleven_multilingual_v2).
  edge        free unofficial Microsoft Edge "Read aloud" service (edge-tts package).
              No key, but slow and drops requests at random.
Default engine: azure if its key is set, otherwise edge. ElevenLabs is opt-in (--engine elevenlabs).

Usage (from the project root):
    tools/.venv/Scripts/python tools/make_audio.py                 # all pages under site/
    tools/.venv/Scripts/python tools/make_audio.py site/old-town   # all pages in a folder
    tools/.venv/Scripts/python tools/make_audio.py site/old-town/crane.html --engine elevenlabs
    options: --engine azure|elevenlabs|edge   --voice ID   --force (ignore "up to date" check)
             --sample-dir DIR   write MP3s to DIR/<page>--<engine>-<voice>.mp3 instead of the site
             --list-voices      list ElevenLabs voices (your account + Russian library voices)
"""
import argparse
import asyncio
import hashlib
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / "audio-cache"

# Azure / edge settings (kept exactly as before so existing cache entries stay valid).
VOICE = "ru-RU-SvetlanaNeural"
RATE = "-5%"
AZURE_FORMAT = "audio-24khz-48kbitrate-mono-mp3"

ELEVEN_API = "https://api.elevenlabs.io/v1"
ELEVEN_FORMAT = "mp3_44100_128"


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class PageParser(HTMLParser):
    """Collects the audio output path and the text of h2/p elements inside #story.

    An element with data-say="…" is voiced as that text instead of its visible content,
    e.g. <span data-say="тысяча девятьсот сорок пятом">1945</span> году.
    """

    def __init__(self):
        super().__init__()
        self.audio_src = None
        self.depth = 0  # nesting depth inside #story (0 = outside)
        self.current = None
        self.skip = 0  # nesting depth inside a data-say element (its visible text is not voiced)
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-audio"):
            self.audio_src = attrs["data-audio"]
        if self.depth:
            self.depth += 1
            if self.skip:
                self.skip += 1
            elif self.current is not None and "data-say" in attrs:
                self.current.append(attrs["data-say"])
                self.skip = 1
            elif tag in ("h2", "p"):
                self.current = []
        elif attrs.get("id") == "story":
            self.depth = 1

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if self.skip:
            self.skip -= 1
            self.depth -= 1
            return
        if tag in ("h2", "p") and self.current is not None:
            text = " ".join("".join(self.current).split())
            if text:
                self.blocks.append(text)
            self.current = None
        self.depth -= 1

    def handle_data(self, data):
        if self.current is not None and not self.skip:
            self.current.append(data)


# ---------- MP3 helpers ----------

_BITRATES = {  # kbit/s by bitrate index, Layer III
    1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],     # MPEG-1
    2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],         # MPEG-2 / 2.5
}
_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def strip_id3(data):
    """Drop a leading ID3v2 tag so blocks can be concatenated cleanly."""
    if data[:3] == b"ID3" and len(data) > 10:
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        return data[10 + size:]
    return data


def mp3_duration(data):
    """Duration in seconds, by walking the MPEG Layer III frame headers."""
    data = strip_id3(data)
    i, seconds = 0, 0.0
    while i + 4 <= len(data):
        b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
        if data[i] != 0xFF or (b1 & 0xE0) != 0xE0:
            i += 1
            continue
        version = (b1 >> 3) & 3          # 3 = MPEG-1, 2 = MPEG-2, 0 = MPEG-2.5
        layer = (b1 >> 1) & 3            # 1 = Layer III
        br_idx, sr_idx, pad = b2 >> 4, (b2 >> 2) & 3, (b2 >> 1) & 1
        if version == 1 or layer != 1 or br_idx in (0, 15) or sr_idx == 3:
            i += 1
            continue
        bitrate = _BITRATES[1 if version == 3 else 2][br_idx] * 1000
        rate = _RATES[version][sr_idx]
        samples = 1152 if version == 3 else 576
        length = samples // 8 * bitrate // rate + pad
        seconds += samples / rate
        i += length
    return seconds


# ---------- engines ----------

def http_retry(request, attempts=5, what="request"):
    """POST/GET with retries on rate limits and dropped connections."""
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < attempts:
                wait = int(e.headers.get("Retry-After") or 10)
                print(f"      rate limited, waiting {wait} s…")
                time.sleep(wait)
                continue
            if e.code in (401, 403):
                body = e.read().decode("utf-8", "replace")[:300]
                raise SystemExit(f"{what}: key rejected or not allowed ({e.code}). Check .env. {body}")
            body = e.read().decode("utf-8", "replace")[:500]
            raise SystemExit(f"{what} failed with HTTP {e.code}: {body}")
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as e:
            # Connection dropped mid-download: retry the whole block.
            if attempt == attempts:
                raise
            print(f"      connection problem ({type(e).__name__}), retry {attempt}…")
            time.sleep(3 * attempt)


async def voice_edge(text, attempts=8):
    import edge_tts

    # The service drops requests at random ("No audio was received"), so retry.
    for attempt in range(1, attempts + 1):
        audio = bytearray()
        try:
            async for chunk in edge_tts.Communicate(text, VOICE, rate=RATE).stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
            return bytes(audio)
        except edge_tts.exceptions.NoAudioReceived:
            if attempt == attempts:
                raise
            print(f"      no audio, retry {attempt}…")
            await asyncio.sleep(1.5 * attempt)


async def voice_azure(text):
    ssml = (
        "<speak version='1.0' xml:lang='ru-RU'>"
        f"<voice name='{VOICE}'><prosody rate='{RATE}'>{escape(text)}</prosody></voice>"
        "</speak>"
    )
    request = urllib.request.Request(
        f"https://{os.environ['AZURE_SPEECH_REGION']}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"],
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": AZURE_FORMAT,
            "User-Agent": "gdansk-guide",
        },
    )
    return http_retry(request, what="Azure")


def eleven_request(path, body=None):
    request = urllib.request.Request(
        ELEVEN_API + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json",
                 "Accept": "audio/mpeg" if body is not None else "application/json"},
    )
    return http_retry(request, what="ElevenLabs")


def make_voice_eleven(voice_id, model):
    async def voice_eleven(text):
        body = {"text": text, "model_id": model}
        path = f"/text-to-speech/{voice_id}?output_format={ELEVEN_FORMAT}"
        return strip_id3(eleven_request(path, body))
    return voice_eleven


def list_eleven_voices():
    mine = json.loads(eleven_request("/voices"))["voices"]
    print("Voices in your account:")
    for v in mine:
        labels = ", ".join(f"{k}: {val}" for k, val in (v.get("labels") or {}).items())
        print(f"  {v['voice_id']}  {v['name']:<28} {labels}")
    shared = json.loads(eleven_request("/shared-voices?" + urllib.parse.urlencode(
        {"language": "ru", "page_size": 30, "sort": "usage_character_count_1y"})))["voices"]
    print("\nRussian voices in the ElevenLabs library (add one to your account to use it):")
    for v in shared:
        print(f"  {v['voice_id']}  {v['name'][:28]:<28} {v.get('gender', '')}, {v.get('age', '')}, "
              f"{v.get('accent', '')}, {v.get('use_case', '')}")


# ---------- pages ----------

def block_hash(engine_key, text):
    return hashlib.sha256(f"{engine_key}|{text}".encode("utf-8")).hexdigest()[:20]


def find_pages(targets):
    pages = []
    for t in targets:
        path = Path(t)
        pages.extend(sorted(path.rglob("*.html")) if path.is_dir() else [path])
    return pages


async def build_page(page, engine, engine_key, voice_fn, force, sample_dir):
    parser = PageParser()
    parser.feed(page.read_text(encoding="utf-8"))
    if not parser.audio_src or not parser.blocks:
        return "skipped"  # not a sight page with narration

    if sample_dir:
        label = re.sub(r"[^\w.-]+", "_", engine_key.split("|")[1])[:40]
        out = Path(sample_dir).resolve() / f"{page.stem}--{engine}-{label}.mp3"
    else:
        out = (page.parent / parser.audio_src).resolve()
    timings_path = out.with_suffix(".json")
    hashes = [block_hash(engine_key, text) for text in parser.blocks]

    rel = page.resolve().relative_to(ROOT)
    if not force and out.exists() and timings_path.exists():
        old = json.loads(timings_path.read_text(encoding="utf-8"))
        if old.get("blocks") == hashes:
            print(f"✓ {rel}: up to date")
            return "up to date"

    print(f"● {rel}")
    audio = bytearray()
    starts = []
    elapsed = 0.0
    new = 0
    for i, (text, h) in enumerate(zip(parser.blocks, hashes), 1):
        cached = CACHE / f"{h}.mp3"
        if cached.exists():
            data = cached.read_bytes()
        else:
            print(f"    [{i}/{len(hashes)}] {text[:60]}…")
            data = await voice_fn(text)
            CACHE.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(data)
            new += 1
        starts.append(round(elapsed, 2))
        elapsed += mp3_duration(data)
        audio.extend(data)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    timings = {"engine": engine, "voice": engine_key.split("|", 2)[1], "duration": round(elapsed, 2),
               "starts": starts, "blocks": hashes}
    timings_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"    saved {shown} ({len(audio) // 1024} KB, {elapsed:.0f} s, "
          f"{new} new / {len(hashes) - new} cached blocks)")
    return "built"


async def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()

    ap = argparse.ArgumentParser(description="Generate narration MP3s for sight pages.")
    ap.add_argument("targets", nargs="*", default=[str(ROOT / "site")], help="pages or folders (default: site/)")
    ap.add_argument("--engine", choices=["azure", "elevenlabs", "edge"],
                    default="azure" if os.environ.get("AZURE_SPEECH_KEY") else "edge")
    ap.add_argument("--voice", help="ElevenLabs voice id (overrides ELEVENLABS_VOICE_ID)")
    ap.add_argument("--force", action="store_true", help="rebuild pages even if up to date")
    ap.add_argument("--sample-dir", help="write test MP3s here instead of into the site")
    ap.add_argument("--list-voices", action="store_true", help="list ElevenLabs voices and exit")
    args = ap.parse_args()

    if args.list_voices or args.engine == "elevenlabs":
        if not os.environ.get("ELEVENLABS_API_KEY"):
            raise SystemExit("ELEVENLABS_API_KEY is not set in .env")
    if args.list_voices:
        return list_eleven_voices()

    if args.engine == "elevenlabs":
        voice_id = args.voice or os.environ.get("ELEVENLABS_VOICE_ID")
        if not voice_id:
            raise SystemExit("No ElevenLabs voice: pass --voice ID or set ELEVENLABS_VOICE_ID (see --list-voices)")
        model = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
        engine_key = f"elevenlabs|{voice_id}|{model}"
        voice_fn = make_voice_eleven(voice_id, model)
    else:
        engine_key = f"{args.engine}|{VOICE}|{RATE}"
        voice_fn = voice_azure if args.engine == "azure" else voice_edge
    print(f"Engine: {args.engine}, voice: {engine_key.split('|', 1)[1]}\n")

    results = []
    for page in find_pages(args.targets):
        results.append(await build_page(page, args.engine, engine_key, voice_fn, args.force, args.sample_dir))
    print(f"\nDone: {results.count('built')} built, {results.count('up to date')} up to date.")


if __name__ == "__main__":
    asyncio.run(main())
