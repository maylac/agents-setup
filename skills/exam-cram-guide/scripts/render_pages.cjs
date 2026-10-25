#!/usr/bin/env node
// Render every <section class="page"> of a cram-guide HTML file to PNG, write a PDF, and report overflow.
// usage: node render_pages.cjs <file.html> [--out DIR] [--pdf NAME.pdf] [--scale 2] [--selector .page]
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const args = process.argv.slice(2);
if (!args.length || args.includes('-h') || args.includes('--help')) {
  console.log('usage: node render_pages.cjs <file.html> [--out DIR] [--pdf NAME.pdf] [--scale 2] [--selector .page]');
  process.exit(args.length ? 0 : 2);
}
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : def; };
const html = path.resolve(args[0]);
const outDir = path.resolve(opt('--out', path.dirname(html)));
const pdfName = opt('--pdf', path.basename(html, path.extname(html)) + '.pdf');
const scale = Number(opt('--scale', '2'));
const selector = opt('--selector', '.page');

(async () => {
  fs.mkdirSync(path.join(outDir, 'png'), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1527 }, deviceScaleFactor: scale });
  await page.goto('file://' + html, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);

  const size = await page.$eval(selector, el => { const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) }; });
  await page.setViewportSize({ width: size.w, height: size.h });

  const report = await page.$$eval(selector, pages => pages.map((pg, i) => {
    const pb = pg.getBoundingClientRect();
    const foot = pg.querySelector('.foot');
    const kids = [...pg.children].filter(c => c !== foot);
    const last = kids.length ? Math.max(...kids.map(c => c.getBoundingClientRect().bottom)) : pb.top;
    const limit = foot ? foot.getBoundingClientRect().top : pb.bottom;
    const overflowEls = [...pg.querySelectorAll('*')].filter(el => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && (r.right > pb.right + 1 || r.bottom > pb.bottom + 1 || el.scrollWidth > el.clientWidth + 2);
    }).length;
    return { page: i + 1, slack: Math.round(limit - last), overflow: overflowEls > 0 || last > limit + 1, overflowing_elements: overflowEls };
  }));

  const pages = await page.$$(selector);
  for (let i = 0; i < pages.length; i++) {
    await pages[i].screenshot({ path: path.join(outDir, 'png', `p${String(i + 1).padStart(2, '0')}.png`) });
  }
  await page.pdf({ path: path.join(outDir, pdfName), width: `${size.w}px`, height: `${size.h}px`, printBackground: true });
  await browser.close();

  console.log(JSON.stringify({ pages: pages.length, size, pdf: path.join(outDir, pdfName), report }, null, 1));
  const bad = report.filter(r => r.overflow || r.slack < 0);
  if (bad.length) { console.error(`overflow on pages: ${bad.map(b => b.page).join(', ')}`); process.exit(1); }
})().catch(err => { console.error(err); process.exit(1); });
