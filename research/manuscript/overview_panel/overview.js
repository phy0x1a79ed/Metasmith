  // ov:js:start — the overview: a band of two reciprocal triangles over Contract / Specification / Plan / Execution columns
  const OV = JSON.parse(document.getElementById("ov-data").textContent);
  const OVPAL = {
    light: { you: "#E3E6EC", youText: "#1B1E24", ms: "#5F6878", msText: "#FFFFFF", bar: "#EEF0F3", barText: "#1B1E24" },
    dark:  { you: "#343944", youText: "#DFE3EA", ms: "#8D97A8", msText: "#14171C", bar: "#262A31", barText: "#DFE3EA" },
  };
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
  function userIcon(cx, cy, s, ink) {   // the person from the old figure 1A, with its upright head, scaled to height s
    const k = s / 74, X = (x) => f(cx + (x - 24.5) * k), Y = (y) => f(cy + (y - 37) * k);
    return `<g fill="none" stroke="${ink}" stroke-width="2" stroke-linejoin="round">`
      + `<ellipse cx="${X(24.5)}" cy="${Y(16.5)}" rx="${f(14 * k)}" ry="${f(16.5 * k)}"/>`
      + `<polygon points="${X(12)},${Y(40)} ${X(37)},${Y(40)} ${X(49)},${Y(74)} ${X(0)},${Y(74)}"/></g>`;
  }
  function serverIcon(cx, cy, s, ink) {   // three stacked units, each with one light and one vent
    const w = s * 0.95, gap = s * 0.07, h = (s - 2 * gap) / 3, x = cx - w / 2;
    let out = `<g fill="none" stroke="${ink}" stroke-width="2" stroke-linecap="round">`;
    for (let i = 0; i < 3; i++) {
      const y = cy - s / 2 + i * (h + gap), my = y + h / 2;
      out += `<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}" rx="${f(h * 0.3)}"/>`
        + `<circle cx="${f(x + w * 0.2)}" cy="${f(my)}" r="${f(h * 0.22)}"/>`
        + `<line x1="${f(x + w * 0.4)}" y1="${f(my)}" x2="${f(x + w * 0.84)}" y2="${f(my)}"/>`;
    }
    return out + "</g>";
  }
  function overview(pal) {
    const t = theme(), op = OVPAL[t], d = OV[t];
    const solver = DATA.scenes.solver.filter((e) => !(e.type === "line" && e.strokeStyle === "dashed") && !/^Solved/.test(e.text || ""));
    const specScene = solver.filter((e) => centreX(e) < 429);
    const planScene = solver.filter((e) => centreX(e) > 950);
    const COLS = [
      ["Contract", "A", excal(DATA.scenes.types, SCENE_OPTS.types, 0.95)],
      ["Specification", "B", excal(specScene, SCENE_OPTS.solver, 0.62)],
      ["Plan", "C", excal(planScene, SCENE_OPTS.solver, 0.62)],
      ["Execution", "D", piece(d.rows)],
    ];
    const PAD = 28, G = 56, LAB = 46, BAND = 54, BAR = 34, FS = 22;
    const cols = COLS.map(([name, letter, it]) => ({ name, body: { w: it.w, h: it.h + LAB, inner: (x, y) =>
      `<text x="${f(x)}" y="${f(y + 32)}" font-family="${FONT}" font-size="34" font-weight="bold" fill="${pal.text}">${letter}</text>` + it.inner(x, y + LAB) } }));
    const W = PAD * 2 + cols.reduce((s, c) => s + c.body.w, 0) + G * (cols.length - 1);
    // The band spans the full width; each triangle's thick end fades out under its icon.
    const ICON = 72, FADE = ICON + 70, bh = BAND, y0 = PAD + (ICON - bh) / 2, e = 3.5 / bh;
    const x0 = PAD, x1 = W - PAD, bw = x1 - x0, cy = y0 + bh / 2;
    const fade = (id, color, from, to) => `<linearGradient id="${id}" gradientUnits="userSpaceOnUse" x1="${f(from)}" y1="0" x2="${f(to)}" y2="0">`
      + `<stop offset="0" stop-color="${color}" stop-opacity="0"/><stop offset="1" stop-color="${color}" stop-opacity="1"/></linearGradient>`;
    const tri = (pts, fill) => `<polygon points="${pts.map(([x, y]) => `${f(x)},${f(y)}`).join(" ")}" fill="${fill}"/>`;
    let svg = `<defs>${fade("ov-fade-you", op.you, x0 + ICON * 0.35, x0 + FADE)}${fade("ov-fade-ms", op.ms, x1 - ICON * 0.35, x1 - FADE)}</defs>`
      + tri([[x0, y0], [x0 + bw * (1 - e), y0], [x0, y0 + bh * (1 - e)]], "url(#ov-fade-you)")
      + tri([[x1, y0 + bh * e], [x1, y0 + bh], [x0 + bw * e, y0 + bh]], "url(#ov-fade-ms)")
      + userIcon(x0 + ICON / 2, cy, ICON, pal.text)
      + serverIcon(x1 - ICON / 2, cy, ICON, pal.text)
      + `<text x="${f(x0 + FADE)}" y="${f(y0 + bh * 0.42)}" font-family="${FONT}" font-size="${FS}" fill="${op.youText}">Expressiveness</text>`
      + `<text x="${f(x1 - FADE)}" y="${f(y0 + bh * 0.86)}" font-family="${FONT}" font-size="${FS}" fill="${op.msText}" text-anchor="end">Automation</text>`;
    let cx = PAD, H = 0;
    const yBar = y0 + bh + ICON / 2 - bh / 2 + 18, yBody = yBar + BAR + 22;
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
  }
  (async () => {
    const downloads = window.claude?.use ? await window.claude.use("downloads") : null;
    if (!downloads) return;
    const btn = document.getElementById("ov-dl"), status = document.getElementById("ov-status");
    btn.hidden = false;
    btn.addEventListener("click", async () => {
      status.textContent = "";
      try {
        await downloads.save({ filename: `metasmith_overview_${theme()}.svg`, data: '<?xml version="1.0" encoding="UTF-8"?>\n' + built.ov });
        status.textContent = "Saved";
      } catch (err) {
        const code = err && err.code;
        if (code === "rate_limited") status.textContent = "A save prompt is already open";
        else if (code !== "declined") { status.textContent = "Download isn't available here"; btn.hidden = true; }
      }
    });
  })();
  // ov:js:end
