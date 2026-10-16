  // ov:js:start — the overview: a band of two reciprocal triangles over Intent / Plan / Execution columns
  const OV = JSON.parse(document.getElementById("ov-data").textContent);
  const OVPAL = {
    light: { you: "#E3E6EC", youText: "#1B1E24", ms: "#5F6878", msText: "#FFFFFF", bar: "#EEF0F3", barText: "#1B1E24" },
    dark:  { you: "#343944", youText: "#DFE3EA", ms: "#8D97A8", msText: "#14171C", bar: "#262A31", barText: "#DFE3EA" },
  };
  let ovSplit = "stack";
  const DS = 1.7;   // composite px per DAG-renderer px: its 13px labels land near the canvases' label size
  const centreX = (e) => (e.points ? e.x + e.points.reduce((s, p) => s + p[0], 0) / e.points.length : e.x + (e.width || 0) / 2);
  function excal(elements, opts, s) {   // s: composite px per scene unit, fixed so steps match across pieces
    const r = renderScene(elements, PAL[theme()], opts);
    r.refit(1 / s);
    return { w: r.w * s, h: r.h * s, inner: (x, y) => r.inner(x, y, r.w * s, r.h * s) };
  }
  function piece(p, k = DS) {
    return { w: p.w * k, h: p.h * k,
      inner: (x, y) => `<svg x="${f(x)}" y="${f(y)}" width="${f(p.w * k)}" height="${f(p.h * k)}" viewBox="0 0 ${f(p.w)} ${f(p.h)}" overflow="visible">${p.body}</svg>` };
  }
  function row(items, gap, align = "top") {
    const w = items.reduce((s, it) => s + it.w, 0) + gap * (items.length - 1), h = Math.max(...items.map((it) => it.h));
    return { w, h, inner: (x, y) => { let cx = x; return items.map((it) => { const dy = align === "bottom" ? h - it.h : 0; const s = it.inner(cx, y + dy); cx += it.w + gap; return s; }).join(""); } };
  }
  function col(items, gap) {
    const w = Math.max(...items.map((it) => it.w)), h = items.reduce((s, it) => s + it.h, 0) + gap * (items.length - 1);
    return { w, h, inner: (x, y) => { let cy = y; return items.map((it) => { const s = it.inner(x, cy); cy += it.h + gap; return s; }).join(""); } };
  }
  function caption(text, item, pal) {
    const fs = 20, h = fs * 1.6;
    return { w: Math.max(item.w, textWidth(text, fs)), h: h + item.h,
      inner: (x, y) => `<text x="${f(x)}" y="${f(y + fs)}" font-family="${FONT}" font-size="${fs}" fill="${pal.text}">${esc(text)}</text>` + item.inner(x, y + h) };
  }
  function lineagePair(L, pal) {
    return row([caption("Target: ORFs", piece(L.plain), pal), caption("Target: ORFs from a MAG", piece(L.mag), pal)], 44);
  }
  function overview(pal) {
    const t = theme(), op = OVPAL[t], d = OV[t];
    const solver = DATA.scenes.solver.filter((e) => !(e.type === "line" && e.strokeStyle === "dashed") && !/^Solved/.test(e.text || ""));
    const intentScene = solver.filter((e) => centreX(e) < 429);
    const planScene = solver.filter((e) => centreX(e) > 950);
    const COLS = [
      ["Intent", [["A", excal(intentScene, SCENE_OPTS.solver, 0.62)], ["B", excal(DATA.scenes.types, SCENE_OPTS.types, 0.95)]]],
      ["Plan", [["C", excal(planScene, SCENE_OPTS.solver, 0.62)], ["D", lineagePair(d.lineage, pal)]]],
      ["Execution", [["E", piece(d.rows)]]],
    ];
    const PAD = 28, G = 56, IG = 40, LAB = 46, BAND = 54, BAR = 34, FS = 22;
    const lettered = (letter, it) => ({ w: it.w, h: it.h + LAB, letter, inner: (x, y) =>
      `<text x="${f(x)}" y="${f(y + 32)}" font-family="${FONT}" font-size="34" font-weight="bold" fill="${pal.text}">${letter}</text>` + it.inner(x, y + LAB) });
    const cols = COLS.map(([name, items]) => {
      const parts = items.map(([l, it]) => lettered(l, it));
      return { name, body: ovSplit === "side" ? row(parts, IG) : col(parts, IG) };
    });
    const W = PAD * 2 + cols.reduce((s, c) => s + c.body.w, 0) + G * (cols.length - 1);
    const x0 = PAD, x1 = W - PAD, y0 = PAD, bh = BAND, e = 3.5 / bh;
    const tri = (pts, fill) => `<polygon points="${pts.map(([x, y]) => `${f(x)},${f(y)}`).join(" ")}" fill="${fill}"/>`;
    const bw = x1 - x0;
    let svg = tri([[x0, y0], [x0 + bw * (1 - e), y0], [x0, y0 + bh * (1 - e)]], op.you)
      + tri([[x1, y0 + bh * e], [x1, y0 + bh], [x0 + bw * e, y0 + bh]], op.ms)
      + `<text x="${f(x0 + 14)}" y="${f(y0 + bh * 0.42)}" font-family="${FONT}" font-size="${FS}" fill="${op.youText}">What you specify</text>`
      + `<text x="${f(x1 - 14)}" y="${f(y0 + bh * 0.86)}" font-family="${FONT}" font-size="${FS}" fill="${op.msText}" text-anchor="end">What Metasmith decides</text>`;
    let cx = PAD, H = 0;
    const yBar = y0 + bh + 18, yBody = yBar + BAR + 22;
    for (const c of cols) {
      svg += `<rect x="${f(cx)}" y="${f(yBar)}" width="${f(c.body.w)}" height="${BAR}" rx="5" fill="${op.bar}"/>`
        + `<text x="${f(cx + c.body.w / 2)}" y="${f(yBar + BAR / 2 + FS * 0.35)}" font-family="${FONT}" font-size="${FS}" font-weight="bold" fill="${op.barText}" text-anchor="middle">${c.name}</text>`
        + c.body.inner(cx, yBody);
      H = Math.max(H, yBody + c.body.h);
      cx += c.body.w + G;
    }
    H += PAD;
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${f(W * SCALE)}" height="${f(H * SCALE)}" viewBox="0 0 ${f(W)} ${f(H)}">`
      + `<rect width="100%" height="100%" fill="${pal.bg}"/>${svg}</svg>`;
  }
  function drawOverview(pal) {
    built.ov = overview(pal);
    document.getElementById("ov-fig").innerHTML = built.ov;
    for (const b of document.querySelectorAll("[data-ov-split]")) b.setAttribute("aria-pressed", String(b.dataset.ovSplit === ovSplit));
  }
  for (const b of document.querySelectorAll("[data-ov-split]")) b.addEventListener("click", () => { ovSplit = b.dataset.ovSplit; drawOverview(PAL[theme()]); });
  (async () => {
    const downloads = window.claude?.use ? await window.claude.use("downloads") : null;
    if (!downloads) return;
    const btn = document.getElementById("ov-dl"), status = document.getElementById("ov-status");
    btn.hidden = false;
    btn.addEventListener("click", async () => {
      status.textContent = "";
      try {
        await downloads.save({ filename: `metasmith_overview_${ovSplit}_${theme()}.svg`, data: '<?xml version="1.0" encoding="UTF-8"?>\n' + built.ov });
        status.textContent = "Saved";
      } catch (err) {
        const code = err && err.code;
        if (code === "rate_limited") status.textContent = "A save prompt is already open";
        else if (code !== "declined") { status.textContent = "Download isn't available here"; btn.hidden = true; }
      }
    });
  })();
  // ov:js:end
