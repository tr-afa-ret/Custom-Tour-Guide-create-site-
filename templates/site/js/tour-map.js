/*
 * Overview map of a tour (Leaflet + OpenStreetMap tiles).
 * Reads the stops from the list on the page: <a class="stop" href data-lat data-lng data-name>.
 * Draws numbered pins in tour order, joined by a dashed line (a sketch, not the exact street path).
 * Add data-loop to #tour-map when the tour ends where it started.
 */
(function () {
  const el = document.getElementById("tour-map");
  if (!el || !window.L) return;

  const stops = Array.from(document.querySelectorAll(".stop[data-lat]")).map((a, i) => ({
    n: i + 1,
    lat: parseFloat(a.dataset.lat),
    lng: parseFloat(a.dataset.lng),
    name: a.dataset.name,
    href: a.getAttribute("href"),
  }));

  const map = L.map(el, { scrollWheelZoom: false, tap: true });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  const points = stops.map((s) => [s.lat, s.lng]);
  // data-loop: the tour returns to its first stop, so close the line.
  const line = "loop" in el.dataset ? points.concat([points[0]]) : points;
  L.polyline(line, { color: "#9b2d20", weight: 4, opacity: 0.7, dashArray: "6 8" }).addTo(map);

  stops.forEach((s) => {
    const icon = L.divIcon({ className: "", html: '<div class="map-pin">' + s.n + "</div>", iconSize: [28, 28], iconAnchor: [14, 14] });
    L.marker([s.lat, s.lng], { icon })
      .addTo(map)
      .bindPopup(s.n + ". " + s.name + '<br><a href="' + s.href + '">Открыть →</a>');
  });

  map.fitBounds(points, { padding: [24, 24] });
})();
