// Capturas de la página construida: escritorio y móvil, claro y oscuro.
// Uso: node scripts/shots.cjs  (después de python3 scripts/build.py)
const { chromium } = require("playwright");
const path = require("path");

const page_url = "file://" + path.resolve(__dirname, "..", "dist", "index.html");
const out = path.resolve(__dirname, "..", "screenshots");
const views = [
  { name: "escritorio", viewport: { width: 1360, height: 900 } },
  { name: "movil", viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
];

(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const browser = await chromium.launch({ proxy });
  for (const v of views) {
    for (const scheme of ["light", "dark"]) {
      const ctx = await browser.newContext({ ...v, colorScheme: scheme });
      const page = await ctx.newPage();
      const errors = [];
      page.on("pageerror", e => errors.push(e.message));
      page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
      await page.goto(page_url, { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      const file = path.join(out, `${v.name}-${scheme}.png`);
      await page.screenshot({ path: file, fullPage: true });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      console.log(file, errors.length ? "ERRORES: " + errors.join(" | ") : "sin errores", overflow ? "· DESBORDA" : "");
      await ctx.close();
    }
  }
  await browser.close();
})();
