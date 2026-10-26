// usage: node shorts-frames.cjs <batchDir> <epId...> : screenshot each scene at start+offset
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const [dir, ...ids] = process.argv.slice(2); const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const out = path.join(dir, 'evidence', 'frames'); fs.mkdirSync(out, { recursive: true }); const issues = [];
  for (const id of ids) {
    await p.goto('file://' + path.join(dir, 'production/build', id, 'index.html')); await p.evaluate(() => document.fonts.ready);
    const scenes = await p.$$eval('section.scene', s => s.map(e => [Number(e.dataset.start), Number(e.dataset.duration)]));
    for (const [i, [st, du]] of scenes.entries()) {
      const t = st + Math.min(du - 0.5, 7.5);
      await p.evaluate(t => { const tl = Object.values(window.__timelines)[0]; tl.seek(t, false); }, t);
      await p.waitForTimeout(100);
      issues.push(...await p.evaluate(sid => { const r = []; const sc = document.querySelector('#scene-' + sid);
        sc.querySelectorAll('.node-label,.node-sub,.title,.body,.verdict p,.edge-label').forEach(e => { if (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1) r.push(sid + ' overflow ' + e.className + ': ' + e.textContent); });
        const st = sc.querySelector('.stage').getBoundingClientRect(), v = sc.querySelector('.verdicts').getBoundingClientRect();
        sc.querySelectorAll('.node').forEach(n => { const b = n.getBoundingClientRect(); if (b.bottom > v.top && v.height > 0) r.push(sid + ' node overlaps verdict'); });
        sc.querySelectorAll('.node-label').forEach(e => { if (e.getBoundingClientRect().height > parseFloat(getComputedStyle(e).fontSize) * 1.5) r.push(sid + ' label wraps: ' + e.textContent); });
        const body = sc.querySelector('.text-block').getBoundingClientRect(); if (body.bottom > st.top - 16) r.push(sid + ' text block touches diagram');
        const cap = sc.querySelector('.caption').getBoundingClientRect(); if (v.height > 0 && v.bottom > cap.top - 12) r.push(sid + ' verdict touches caption');
        return r; }, `s${i + 1}`).then(r => r.map(x => id + ' ' + x)));
      await p.screenshot({ path: path.join(out, `${id}-s${i + 1}.png`) });
    }
  }
  console.log(issues.length ? issues.join('\n') : 'no layout issues'); await b.close();
})();
