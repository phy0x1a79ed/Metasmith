  // ov:js:start — the overview: a band of two reciprocal triangles over Contract / Specification / Plan / Execution columns
  const OV = JSON.parse(document.getElementById("ov-data").textContent);
  const OVPAL = {
    light: { you: "#E3E6EC", youText: "#1B1E24", ms: "#636EFA", msText: "#FFFFFF", bar: "#EEF0F3", barText: "#1B1E24" },
    dark:  { you: "#343944", youText: "#DFE3EA", ms: "#636EFA", msText: "#FFFFFF", bar: "#262A31", barText: "#DFE3EA" },
  };
  const DS = 22 / 13;   // composite px per DAG-renderer px: its 13px labels land at the figure's 22px
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
    const FS = 22, PAD = 28, G = 56, BAR = 34, LAB_GAP = 22, BAND = 60, ICON = BAND, FADE = ICON + 70;
    const text = (x, y, s, anchor = "start", fill = pal.text, weight = "normal") =>
      `<text x="${f(x)}" y="${f(y + FS * 0.35)}" font-family="${FONT}" font-size="${FS}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${esc(s)}</text>`;
    // A: the types canvas at the figure's one label size; it is drawn large enough that its circle labels fit at that size.
    const saved = { fs: ST.fs, small: ST.small };
    ST.fs = FS; ST.small = FS;
    let contract;
    try { contract = excal(DATA.scenes.types, { ...SCENE_OPTS.types, typesLabel: "Type:" }, 1.22); contract = { ...contract, svg: contract.inner(0, 0) }; }
    finally { Object.assign(ST, saved); }
    const A = { w: contract.w, h: contract.h, inner: (x, y) => `<g transform="translate(${f(x)} ${f(y)})">${contract.svg}</g>` };
    // B: the specification in pieces, each row named on the left.
    const S = d.spec, lib = S.library.map((p) => piece(p)), dots = 34, LG = 28;
    const libW = lib.reduce((s, p) => s + p.w, 0) + LG * lib.length + dots;
    const rowsB = [["Given", [piece(S.given)]], ["Transform library", lib], ["Targets", [piece(S.targets)]]];
    const labW = Math.max(...rowsB.map(([n]) => textWidth(n, FS))) + 18, RG = 10;
    const B = { w: labW + Math.max(libW, ...rowsB.map(([, ps]) => ps[0].w)),
      h: rowsB.reduce((s, [, ps]) => s + Math.max(...ps.map((p) => p.h)), 0) + RG * (rowsB.length - 1),
      inner: (x, y) => {
        let out = "", cy = y;
        for (const [name, ps] of rowsB) {
          const h = Math.max(...ps.map((p) => p.h)), src = ps === lib ? null : (name === "Given" ? S.given : S.targets);
          out += text(x + labW - 18, cy + (src ? (h - ps[0].h) / 2 + src.anchor * DS : h / 2), name, "end");
          let cx = x + labW;
          for (const p of ps) { out += p.inner(cx, cy + (h - p.h) / 2); cx += p.w + LG; }
          if (ps === lib) for (let i = 0; i < 3; i++) out += `<circle cx="${f(cx + 4 + i * 12)}" cy="${f(cy + h / 2)}" r="3.2" fill="${pal.text}"/>`;
          cy += h + RG;
        }
        return out;
      } };
    const C = piece(d.plan), D = piece(d.grid);
    // A column is at least wide enough for its header: the letter at the left, the name centred clear of it.
    const fit = (letter, name, it) => {
      const w = Math.max(it.w, textWidth(name, FS) + 2 * (12 + textWidth(letter, FS) + 14)), dx = (w - it.w) / 2;
      return [letter, name, { w, h: it.h, inner: (x, y) => it.inner(x + dx, y) }];
    };
    const COLS = [["A", "Contract", A], ["B", "Specification", B], ["C", "Plan", C], ["D", "Execution", D]].map((c) => fit(...c));
    const W = PAD * 2 + COLS.reduce((s, c) => s + c[2].w, 0) + G * (COLS.length - 1);
    // The band spans the full width; each triangle's thick end is the icons' height (2 for their strokes) and fades out under its icon.
    const y0 = PAD, bh = BAND + 2, x0 = PAD, x1 = W - PAD, bw = x1 - x0, cy = y0 + bh / 2, gx = 3.5 * bw / bh;
    const fade = (id, color, from, to) => `<linearGradient id="${id}" gradientUnits="userSpaceOnUse" x1="${f(from)}" y1="0" x2="${f(to)}" y2="0">`
      + `<stop offset="0" stop-color="${color}" stop-opacity="0"/><stop offset="1" stop-color="${color}" stop-opacity="1"/></linearGradient>`;
    const tri = (pts, fill) => `<polygon points="${pts.map(([x, y]) => `${f(x)},${f(y)}`).join(" ")}" fill="${fill}"/>`;
    let svg = `<defs>${fade("ov-fade-you", op.you, x0 + ICON * 0.35, x0 + FADE)}${fade("ov-fade-ms", op.ms, x1 - ICON * 0.35, x1 - FADE)}</defs>`
      + tri([[x0, y0], [x1 - gx, y0], [x0, y0 + bh]], "url(#ov-fade-you)")
      + tri([[x1, y0], [x1, y0 + bh], [x0 + gx, y0 + bh]], "url(#ov-fade-ms)")
      + userIcon(x0 + ICON / 2, cy, ICON, pal.text)
      + serverIcon(x1 - ICON / 2, cy, ICON, pal.text)
      + text(x0 + FADE, y0 + bh * 0.3, "Expressiveness", "start", op.youText)
      + text(x1 - FADE, y0 + bh * 0.72, "Automation", "end", op.msText);
    let cx = PAD, H = 0;
    const yBar = y0 + bh + 18, yBody = yBar + BAR + LAB_GAP;
    for (const [letter, name, it] of COLS) {
      svg += `<rect x="${f(cx)}" y="${f(yBar)}" width="${f(it.w)}" height="${BAR}" rx="5" fill="${op.bar}"/>`
        + text(cx + 12, yBar + BAR / 2, letter, "start", op.barText, "bold")
        + text(cx + it.w / 2, yBar + BAR / 2, name, "middle", op.barText, "bold")
        + it.inner(cx, yBody);
      H = Math.max(H, yBody + it.h);
      cx += it.w + G;
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
