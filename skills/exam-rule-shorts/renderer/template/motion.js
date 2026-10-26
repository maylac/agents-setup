// Builds the paused GSAP timeline for one episode from window.__EPISODE_TIMING__.
// All motion is absolute-positioned on the timeline so HyperFrames can seek any frame.
// index.html calls buildEpisodeTimeline(tl, timing) and registers it on window.__timelines.
window.buildEpisodeTimeline = function (tl, T) {
  const $ = (sel) => document.querySelector(sel);

  // Persistent chrome
  tl.fromTo("#progress-fill", { scaleX: 0 }, { scaleX: 1, duration: T.total, ease: "none" }, 0);
  tl.from("#header", { y: -30, opacity: 0, duration: 0.5, ease: "power3.out" }, 0);

  const ACCENT = ["#6ea8ff", "#4cc38a", "#f29a52", "#c8ccd4"];

  T.scenes.forEach((s, idx) => {
    const S = s.start;
    const D = s.duration;
    const last = idx === T.scenes.length - 1;
    const k = Math.min(1, D / 8); // compress intro beats for short scenes
    const at = (t) => S + t * k;
    const end = S + D;
    const scene = `#scene-${s.sid}`;
    const p = s.sid;

    // Scene dots
    tl.to(`#dot-${idx + 1}`, { backgroundColor: ACCENT[idx % 4], scale: 1.25, duration: 0.3, ease: "back.out(3)" }, S);
    if (!last) tl.to(`#dot-${idx + 1}`, { scale: 1, duration: 0.2 }, end - 0.2);

    // Enter / exit
    if (idx === 0) tl.set(scene, { opacity: 1 }, 0);
    else tl.fromTo(scene, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power2.out" }, S);
    if (!last) tl.to(scene, { opacity: 0, duration: 0.25, ease: "power2.in" }, end - 0.25);

    tl.from(`#${p}-kicker`, { x: -40, opacity: 0, duration: 0.45, ease: "power3.out" }, at(0.05));
    tl.from(`${scene} .step`, { opacity: 0, duration: 0.4 }, at(0.1));
    if (idx !== 0) tl.from(`#${p}-title`, { y: 60, opacity: 0, duration: 0.6, ease: "power3.out" }, at(0.15));
    if ($(`#${p}-body`)) tl.from(`#${p}-body`, { y: 30, opacity: 0, duration: 0.5, ease: "power2.out" }, at(0.45));
    const captionChunks = s.captionChunks || [];
    if (captionChunks.length) {
      captionChunks.forEach((c) => {
        const sel = `#${p}-caption-chunk-${c.i}`;
        const begin = Math.max(S, Math.min(end, S + c.start));
        const finish = Math.max(begin, Math.min(end, S + c.end));
        tl.set(sel, { display: "block", opacity: 0 }, begin);
        tl.to(sel, { opacity: 1, duration: 0.06 }, begin);
        tl.to(sel, { opacity: 0, duration: 0.06 }, Math.max(begin + 0.06, finish - 0.06));
        tl.set(sel, { display: "none" }, finish);
      });
    } else {
      tl.from(`#${p}-caption`, { y: 24, opacity: 0, duration: 0.4, ease: "power2.out" }, at(0.3));
    }
    if ($(`#${p}-source`)) tl.from(`#${p}-source`, { opacity: 0, duration: 0.4 }, at(0.6));

    // Nodes pop in
    for (let n = 0; n < s.nodeCount; n++) {
      tl.from(`#${p}-node-${n}`, { scale: 0.6, opacity: 0, duration: 0.5, ease: "back.out(1.8)" }, at(0.7 + n * 0.15));
    }

    // Edges draw
    s.edges.forEach((e, i) => {
      const t0 = at(1.2 + i * 0.2);
      tl.from(`#${p}-edge-${e.i} .edge-line`, { scaleX: 0, duration: 0.45, ease: "power2.out" }, t0);
      tl.from(`#${p}-edge-${e.i} .edge-head`, { scale: 0, opacity: 0, duration: 0.25, ease: "back.out(3)" }, t0 + 0.35);
      if (e.hasLabel) tl.from(`#${p}-edge-${e.i}-label`, { scale: 0.7, opacity: 0, duration: 0.35, ease: "back.out(2)" }, t0 + 0.4);
    });
    const edgesReady = at(1.2 + Math.max(0, s.edges.length - 1) * 0.2 + 0.6);

    // Wrong path: orange packet gets blocked half-way, then the misconception is struck out.
    let flowStart = edgesReady;
    if (s.hasWrong) {
      const w = edgesReady;
      tl.from(`#${p}-wrong`, { x: -60, opacity: 0, duration: 0.45, ease: "power3.out" }, w - 0.2);
      if ($(`#${p}-wrong-pkt`) && s.edges.length) {
        const half = s.edges[0].len / 2;
        tl.fromTo(`#${p}-wrong-pkt`, { x: 0, opacity: 0 }, { x: half - 40, opacity: 1, duration: 0.7, ease: "power1.in" }, w);
        tl.to(`#${p}-wrong-pkt`, { x: half - 70, duration: 0.25, ease: "power2.out" }, w + 0.7);
        tl.fromTo(`#${p}-wrong-x`, { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, w + 0.7);
        tl.to(`#${p}-wrong-pkt`, { opacity: 0, duration: 0.3 }, w + 1.1);
        tl.to(`#${p}-wrong-x`, { opacity: 0, scale: 0.6, duration: 0.3 }, w + 1.6);
      }
      tl.fromTo(`#${p}-strike`, { backgroundSize: "0% 5px" }, { backgroundSize: "100% 5px", duration: 0.6, ease: "power2.inOut" }, w + 0.8);
      tl.to(`#${p}-wrong`, { opacity: 0.75, duration: 0.4 }, w + 1.3);
      flowStart = w + 1.7;
    }

    // Rule card lands once the correct flow begins.
    if (s.hasRule) {
      const r = Math.min(Math.max(flowStart + 0.3, S + D * 0.35), end - 1.2);
      tl.from(`#${p}-rule`, { y: 40, scale: 0.94, opacity: 0, duration: 0.5, ease: "back.out(1.6)" }, Math.max(r, S + 0.3));
    }

    // Correct flow: packets travel every edge in sequence, cycling until the scene ends.
    const travel = 0.8;
    const stepGap = 0.35;
    const cycle = Math.max(1.6, s.edges.length * stepGap + travel + 0.4);
    const flowEnd = end - (last ? 0.2 : 0.45);
    let c = 0;
    for (let t = flowStart; s.edges.length && t + travel < flowEnd; t += cycle, c++) {
      s.edges.forEach((e, i) => {
        const t0 = t + i * stepGap;
        if (t0 + travel > flowEnd) return;
        const pkt = `#${p}-edge-${e.i}-pkt-${c % 2 ? "b" : "a"}`;
        tl.fromTo(pkt, { x: 0, opacity: 0 }, { x: e.len - 34, duration: travel, ease: "power1.inOut", immediateRender: false }, t0);
        tl.fromTo(pkt, { opacity: 0 }, { opacity: 1, duration: 0.12, immediateRender: false }, t0);
        tl.to(pkt, { opacity: 0, duration: 0.12 }, t0 + travel - 0.12);
        tl.fromTo(`#${p}-node-${e.to}`, { scale: 1 }, { scale: 1.05, duration: 0.12, yoyo: true, repeat: 1, ease: "power1.out", immediateRender: false }, t0 + travel - 0.05);
      });
    }
  });

  tl.set({}, {}, T.total);
  return tl;
};
