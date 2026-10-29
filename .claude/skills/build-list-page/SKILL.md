---
name: build-list-page
description: Build a list page of the Russian guide site (e.g. "museums for families", beaches, viewpoints, where to eat), with a vertical list of cards, each with a short description, an age or info chip, Google Maps links and the official website. No audio, no photos. Use after the user picked the items.
---

# Build a list page

Prerequisite: the user picked the items from your suggestions and approved the page. Skeleton: `templates/pages/list.html`. Example: `templates/examples/list-page.html` (the Gdańsk museums).

## Page

`site/<section>/index.html`:
- Top bar with a back link to `../index.html`, the title and the text-size control.
- `.tour-head` with the `h1`.
- `.intro`: one sentence on what the list is and who it is for, plus a `.muted` note: "Часы работы и цены меняются … проверяйте на сайтах перед поездкой."
- One `article.museum` card per item, in a sensible order (most popular first, or grouped by area):
  - `h2`: Russian name.
  - `.sub`: original name · area (for places outside the city, add `🚗 ~N мин от <города>`).
  - `.museum-meta` with a chip `span.age`: age (`👨‍👩‍👧 6+`) or another key fact.
  - `p`: 1–2 sentences on why it's worth going, written for the audience (e.g. what children will enjoy).
  - `.museum-links` with buttons `btn outline small`:
    - `📍 На карте` → `https://www.google.com/maps/search/?api=1&query=<Name, street number, city>`, URL-encoded. Search by **name plus address**, not by coordinates, so the app opens the place's own card with its hours and reviews. When one place has two buildings, add one button per building (`📍 Музей и «Сольдек»`, `📍 Центр морской культуры`).
    - `🌐 Сайт` → the official website (skip it if there isn't one).
- No audio player and no photos (keeps the page light).

Then add a card for the page on the landing page (`Смотреть список`, meta such as `🏛 6 музеев`).

## Checks (what we learned)

- Verify each address and website with a web search: names, addresses and URLs change. Open each website link to confirm it works.
- Verify claims about specific exhibitions (age, topic, whether it still runs). For the WWII museum's children's exhibition, the first description was wrong. When something may have closed, say "уточните на сайте".
- Geocode or search slowly (Nominatim at most 1 request a second, with a `User-Agent`).
