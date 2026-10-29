---
name: build-tour
description: Build a guided tour section of the Russian guide site (walking tour, day trip by car, or single-location guide like a castle) after the user approved the plan. Covers route order, coordinates, distances, Wikimedia photos, writing the Russian stories, the stop pages, the tour index page and the landing card. Use whenever adding, reordering or removing stops.
---

# Build a tour section

Prerequisite: the user approved this section's stops, start/end and type (see **new-guide-site**). If `site/` has no `css/` and `js/` yet, copy `templates/site/*` into `site/` first.

Files: `site/<section>/index.html` (tour overview) and `site/<section>/<slug>.html` (one per stop). Slugs are short English kebab-case (`crane`, `st-marys-basilica`). Skeletons: `templates/pages/tour-index.html`, `templates/pages/stop.html`. Quality bar: `templates/examples/`.

## 1. Route

- Order the stops so there is **no walking back and forth**. Sketch the path in words (e.g. "south along the river, west along X street, north across Y…") and check it on the map. Repeated stretches should be short and named.
- A loop ends back at stop 1. Add `data-loop` to `#tour-map`, and give the last page a "Финиш" box pointing back to the start.
- Royal or processional routes: walk them in the historical direction when possible. It makes a better story.
- Sights just off the route (~200 m or more) usually become a **tip** on the nearest stop, not a stop of their own.
- Day trips: mark car legs, say where to park, and give a public-transport alternative in the "how to get there" box.

## 2. Coordinates

- Take coordinates from Wikipedia/Wikidata, then **verify every one with Nominatim** (`https://nominatim.openstreetmap.org/search?format=json&q=…`, at most 1 request a second, with a `User-Agent` header). Wikipedia coordinates are sometimes wrong. In Gdańsk the Shakespeare Theatre was off by a lot.
- For big or long objects, use the point where the visitor actually stands: the entrance of a pier (not the middle of it), the gate of a castle, the viewpoint for a panorama.
- Use 5–6 decimal places.
- Polish or other non-ASCII queries: write them inside a Python script in the scratchpad (Git Bash mangles them as arguments) and set `PYTHONIOENCODING=utf-8`.

## 3. Distances and times

- Walking: straight-line (haversine) distance × 1.3, at 70 m/min. Round to ~10 m and whole minutes, with a minimum of 1 min. Shown as `🚶 ~230 м · 4 мин пешком`.
- Car: a realistic estimate shown as `🚗 ~15 мин на машине`, with `travelmode=driving` in the link.
- Tour facts in the index header: number of stops, total km, total time (walking time plus ~5–10 min per stop, rounded generously), and `🔄 по кругу` for a loop.

## 4. Photos (Wikimedia Commons, hotlinked)

What worked, and what went wrong:
- Find a good landscape photo on Commons, usually the Wikipedia article's lead image or a "Quality image". Prefer daytime photos without scaffolding and with the whole object in view.
- Get the URL and credits from the API: `https://commons.wikimedia.org/w/api.php?action=query&titles=File:NAME&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=960&format=json`. `extmetadata` gives `Artist` (strip the HTML) and `LicenseShortName`/`LicenseUrl`.
- Thumbnail URLs: `https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/NAME/960px-NAME` for the photo on a stop page and `/330px-` for the stop list. `a/ab` are the first 1 and 2 hex characters of the MD5 of the file name (spaces → `_`). Use the standard widths 330 and 960; other widths can be refused.
- **Rate limits:** Commons and Wikipedia return **429** when hit too fast. Send a descriptive `User-Agent`, pause ~1–2 s between requests, and on a 429 wait and retry. Don't fire many requests in parallel.
- At the end, check every image URL slowly (one by one, with pauses) and make sure each returns 200.
- Credit format in the `figcaption`: `Фото: Author, <a href="commons file page">Wikimedia Commons</a>, <a href="licence url">CC BY-SA 4.0</a>`.

## 5. Story text (`#story`): the guide's voice

- Russian, warm and lively, like a local guide talking to the group in front of the object: "Перед вами…", "Присмотритесь…". About 5–8 blocks (`<p>`, with 1–3 `<h2>` subheadings), ~1.5–2.5 min of audio per stop.
- Content: history, interesting facts, people, legends ("а теперь легенда…"), and what to look at right now.
- Tours are read in order. The first stop welcomes the visitors and introduces the route. Later stops refer back ("мы уже видели…") and forward ("впереди нас ждёт…") **in the actual stop order**. The last stop says goodbye. After any reordering, re-read these references.
- Everything in `#story` is read aloud, so:
  - Centuries are written as words: "семнадцатого века", never "XVII в.". No Roman numerals, no abbreviations ("г.", "м", "ул."), no brackets or footnotes.
  - Years and other figures may stay as digits for readers, but wrap each one in a spoken form with the correct Russian case: `<span data-say="тысяча девятьсот сорок пятом">1945</span> году`, `в <span data-say="тысяча четыреста сорок втором – тысяча четыреста сорок четвёртом">1442–1444</span> годах`. The generator voices `data-say` instead of the digits. ElevenLabs needs this; it is harmless for Azure.
  - Foreign names: write them in Russian transliteration, and put the original in the `.sub` line rather than the story.
- Check uncertain facts (dates, opening status, what an exhibition shows) with a web search. Don't invent details.

## 6. Stop page (`templates/pages/stop.html`)

Block order:
1. Top bar: back link to the section index, title, `<div class="text-size" data-text-size></div>`. Load `js/textsize.js` in `<head>`.
2. Photo plus credit.
3. `Остановка N из M`, title, and the `.sub` line (original-language name · place).
4. Google Maps embed (`https://maps.google.com/maps?q=LAT,LNG&z=17&hl=ru&output=embed`, no key) and a button for walking directions (`https://www.google.com/maps/dir/?api=1&destination=LAT,LNG&travelmode=walking`).
5. Player block `.listen` with `data-audio="../audio/<section>/<slug>.mp3"`, **above** the story.
6. `#story`.
7. `Советы гида` tips box: practical things (tickets, hours, best photo spot, nearby food). Not read aloud.
8. `Следующая остановка` box: number and name, distance/time, a one-line hint on how to get there, a link to the next page, and a Google Maps directions link to the next stop. Then `← Предыдущая: N. Name`. The last stop shows `Финиш`, or "Экскурсия окончена", with links to the tour index and to all tours.

All CSS sizes are in `rem`, so the A−/A+ control scales everything. Keep it that way in any new CSS. To hide an element, use the `hidden` attribute; `style.css` has `[hidden]{display:none!important}` because `.btn` would otherwise override it.

## 7. Tour index (`templates/pages/tour-index.html`)

Title and facts → intro (2 short paragraphs: what you'll see, and the route) → for day trips or single locations, a `🚗 Как добраться из <города>` box → `#tour-map` (Leaflet; it reads `data-lat`, `data-lng` and `data-name` from the `.stop` cards) → buttons: start the tour, and the full route in Google Maps → stop cards (330px photo, `Остановка N`, name, one-line teaser) with `.walk-link` between them.

- Full route link: `https://www.google.com/maps/dir/?api=1&origin=…&destination=…&waypoints=a|b|c&travelmode=walking`. The phone app accepts only a few waypoints, so pick a handful of key ones (6 worked for the Old Town loop).
- Leaflet 1.9.4 from unpkg with SRI:
  - css: `sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=`
  - js: `sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=`
  - footer credit: `карта © участники OpenStreetMap`

## 8. Landing card

Add an `.guide-card` in the right group on `site/index.html`, with the title, meta (`⏱ ~N часа`, `🚶 пешком, по кругу` or `🚗 N мин`), a one-line teaser, and the button `Начать экскурсию`. Planned sections that aren't built yet can be shown as "скоро".

## 9. Changing stops later

Adding, removing or reordering a stop means updating:
- the stop list, map pins and facts in `index.html`
- every `Остановка N из M` label
- the next/prev blocks on the neighbouring pages
- the "we saw / we will see" references in the stories
- the audio, which must be regenerated for every page whose story changed

## 10. Before reporting done

- Every page opens; all internal links work (check `href`s with a small script).
- Every image URL returns 200 (checked slowly).
- Numbering and next/prev links are consistent.
- Pages without audio show "Аудио скоро появится".
- Tell the user what was built, and what is still open (e.g. audio not generated yet).
