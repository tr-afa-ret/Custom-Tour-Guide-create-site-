/*
 * Text size control. Load in <head> (not deferred) so the saved size is applied
 * before the page paints. Adds A− / A+ buttons into every [data-text-size] element.
 * All font sizes in style.css are in rem, so changing the root size scales them.
 */
(function () {
  const STEPS = [1, 1.5, 2, 3];
  const KEY = "guide.textScale";
  const root = document.documentElement;

  let step = 0;
  try {
    const saved = STEPS.indexOf(parseFloat(localStorage.getItem(KEY)));
    if (saved >= 0) step = saved;
  } catch (e) { /* storage unavailable — use default */ }

  function apply() {
    root.style.fontSize = 16 * STEPS[step] + "px";
    document.querySelectorAll("[data-text-size] button").forEach((b) => {
      b.disabled = b.dataset.dir === "-1" ? step === 0 : step === STEPS.length - 1;
    });
  }

  function change(dir) {
    step = Math.min(STEPS.length - 1, Math.max(0, step + dir));
    try { localStorage.setItem(KEY, STEPS[step]); } catch (e) { /* ignore */ }
    apply();
  }

  apply();

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-text-size]").forEach((box) => {
      box.innerHTML =
        '<button type="button" data-dir="-1" aria-label="Уменьшить текст">A−</button>' +
        '<button type="button" data-dir="1" aria-label="Увеличить текст">A+</button>';
      box.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (btn) change(Number(btn.dataset.dir));
      });
    });
    apply();
  });
})();
