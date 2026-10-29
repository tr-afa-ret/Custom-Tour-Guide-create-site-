---
name: new-guide-site
description: Kickoff for a new Russian tour-guide website. Use when the project has no site/ folder yet, or when the user wants to plan a new site or a new batch of sections. Runs the interview (location, audio engine, which places), gives suggestions, proposes the plan (tours vs single-location pages vs list pages), asks the open questions and waits for approval before anything is built.
---

# New guide site: kickoff

Goal: agree on **what** to build before building anything. Ask one step at a time, in this order, and wait for the answer to each step. Never write pages, text or audio during the kickoff.

## Step 1: basics (ask together)

1. **Location or area:** which city or region the site is for. If it's a city, also ask whether nearby day trips should be included.
2. **Audio:** do we want narration, and with which engine?
   - **Azure AI Speech** (voice `ru-RU-SvetlanaNeural`): very cheap, with a free tier of about 0.5M characters a month. A clear, good voice that copes well with numbers written as digits. Needs `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`.
   - **ElevenLabs:** the most natural voices, paid per character from the subscription. Native Russian voices sound best. Numbers must be spelled out (see **make-narration**).
   - **No audio for now:** the player shows "Аудио скоро появится" and audio can be added later.

Then check `.env` for the matching keys, by presence only: never print or read out the values. Note the choice in CLAUDE.md → Project.

## Step 2: places

Ask: **"Do you already know the exact places to visit, or would you like suggestions?"**

If suggestions are wanted, act as the guide and give a numbered list grouped like this:
- **In town on foot:** the main walking tour (or tours) and its highlights.
- **Day trips by car:** places reachable in a day's round trip: big nature areas, major landmarks, castles, memorials, and museums that deserve a full guided tour. For each: drive time, how long to spend there, and one line on why it's worth going.
- **List pages:** groups of similar places that need a short card each, not a tour (e.g. museums for families with school-age children, beaches, viewpoints, where to try local food).

Mark the strongest picks, and let the user choose by number. Check facts you are unsure of (opening status, whether an exhibition still runs, distances) with a web search before suggesting them.

## Step 3: plan summary (after the list is agreed)

Sort each agreed place into one type and present the plan as a short table:

| Type | When | Example from Gdańsk |
|---|---|---|
| **Walking tour** | Many sights close together, in a route order | Old Town: 15 stops, a loop of ~3.2 km, ~2.5 h |
| **Day trip by car** | A place outside the city with several stops, sometimes with short car legs between them | Westerplatte (5), Sopot (6) |
| **Single-location guide** | One site that is visited as a whole: an intro plus a few stops inside it, or just one page | Malbork Castle: 4 stops that complement the castle's own audio guide |
| **List page** | Many separate places, each with a card: description, age/tips, map link and website. No audio | Museums for families |

For each tour, propose the stops in route order with rough distance and duration, and say how the landing page will be grouped.

## Step 4: questions (ask only those that apply)

- **Start and end of each tour:** a loop back to the start, or one-way? Where should it start (parking, station, main square)?
- Target duration, or number of stops.
- Walking only, or a car between parts (day trips: where to park, and an alternative by public transport)?
- Who it is for (adults, families with children) and any special interests.
- For list pages: the selection criteria, and which details each card shows (age, address, website, prices or not).
- The site name, for the title and footer (e.g. "Гданьск с гидом").
- Whether to build one **test page first** to check the look and voice before the rest (recommended for a new site or a new engine).

## Step 5: go-ahead

Sum up the final plan in a few lines and ask explicitly: **"Shall I start building?"** Build only after a clear yes. Then:

1. Fill in CLAUDE.md → **Project** with what was agreed.
2. Copy `templates/site/` into `site/`, and build the landing page from `templates/pages/landing.html`.
3. Build each section with **build-tour** or **build-list-page**, in the order the user prefers. Stop after each section, or after the test page, if the user asked for that.
4. Audio comes last, as a batch, using **make-narration**: samples on one page first, then the rest after approval.

Later requests to add sections follow the same pattern: suggest → agree on the list → plan → questions → go-ahead.
