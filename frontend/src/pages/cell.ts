/**
 * Tweak the Tumor's microscope illustration, ported from the PinkAI v2 design (app.js).
 *
 * The real benign FNAC slide with its nuclei painted out (public/pinkai/slide-bg.jpg) is the
 * background; every nucleus is redrawn from the five slider values, so each measurement changes
 * only its own feature: size, chromatin speckle, a ragged edge, dent depth and number of dents.
 * It is an illustration only — the model's prediction always comes from the API.
 */

// [x, y, radius, elongation, angle] of each nucleus, measured from the real slide by the design's tools/nuclei.py.
const NUCLEI = [[196.3,52.4,19.8,1.21,-0.04],[301.3,153.8,16.0,1.1,-0.47],[290.2,102.3,16.7,1.24,0.24],[246.2,185.5,19.7,1.3,0.06],[291.0,126.3,16.1,1.18,-0.43],[258.9,82.6,16.4,1.17,-2.1],[306.7,179.1,19.1,1.35,-0.28],[272.0,153.0,17.2,1.1,-2.01],[258.5,120.5,17.1,1.05,0.17],[236.3,90.0,16.6,1.21,-1.72],[240.2,145.4,18.1,1.16,-1.97],[178.0,132.6,17.7,1.23,0.36],[167.6,100.1,19.4,1.3,-0.78],[68.7,97.0,10.2,1.35,-2.19],[125.1,115.6,18.7,1.18,-0.92],[493.4,113.7,19.9,1.35,0.23],[537.4,139.3,14.4,1.28,-1.55],[348.8,157.3,18.5,1.11,-1.56],[377.0,158.2,17.7,1.14,-1.58],[402.6,149.0,15.7,1.14,0.4],[205.6,162.4,17.0,1.16,0.44],[451.9,167.8,19.7,1.1,0.74],[48.6,205.5,19.3,1.11,0.37],[65.9,176.3,18.9,1.05,-0.46],[108.0,180.8,16.3,1.14,-0.84],[122.4,198.8,17.2,1.24,-0.67],[400.7,186.9,19.0,1.23,-0.74],[180.2,191.2,18.8,1.04,-0.88],[295.7,209.1,17.1,1.19,0.29],[337.0,198.0,18.3,1.2,-0.6],[275.4,226.3,17.5,1.11,-2.27],[205.2,221.8,19.4,1.1,-1.53],[233.8,227.2,19.0,1.12,-1.38],[543.1,220.3,17.0,1.07,0.7],[390.9,242.9,19.3,1.27,-1.1],[367.9,232.6,17.5,1.16,-1.59],[329.7,295.0,17.8,1.18,-2.23],[349.5,276.3,18.1,1.19,0.55],[303.5,267.9,18.6,1.18,0.21],[321.7,237.8,18.5,1.25,-0.1],[148.1,245.2,18.6,1.21,-1.3],[529.4,254.6,17.6,1.11,-2.04],[189.9,257.3,18.0,1.29,-2.31],[231.8,267.5,17.6,1.26,-0.18],[94.3,272.4,19.6,1.21,-0.5],[170.9,318.5,15.8,1.24,-1.2],[166.5,279.4,18.2,1.04,-0.39],[151.2,310.2,15.3,1.2,-1.29],[249.6,386.5,17.8,1.22,0.5],[208.8,372.6,17.5,1.17,-0.36],[191.7,351.8,17.0,1.13,-1.27],[200.8,299.2,17.3,1.13,-1.22],[248.1,294.6,18.4,1.31,-0.65],[242.3,354.8,17.8,1.15,-0.18],[218.5,325.3,18.1,1.08,-0.91],[248.2,327.4,16.5,1.1,-2.07],[50.5,283.4,9.5,1.15,-2.26],[382.2,297.3,17.1,1.15,-0.56],[291.7,309.2,19.2,1.12,0.25],[404.7,347.0,16.2,1.35,0.15],[407.5,327.3,16.0,1.34,0.09],[131.6,351.6,18.0,1.17,-1.29],[350.0,362.4,10.2,1.35,-1.78],[303.7,384.3,18.2,1.26,-0.36],[294.3,362.2,17.8,1.21,-0.42],[161.5,380.5,21.2,1.19,-1.33],[190.7,416.6,17.3,1.32,0.68],[177.9,433.5,17.6,1.35,0.65],[371.9,418.9,15.3,1.34,-2.26],[357.2,430.9,15.5,1.33,-2.25]];

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
/** Small fixed-seed generator, so every nucleus keeps its own look between redraws. */
const seeded = (seed: number) => () => {
  seed = (seed + 0x6D2B79F5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

const background = new Image();
let pending: { canvas: HTMLCanvasElement; values: number[]; mini: HTMLCanvasElement | null } | null = null;
let queued = false;
background.onload = () => { if (pending) schedule(); };
background.src = "/pinkai/slide-bg.jpg";
let layer: HTMLCanvasElement | null = null;

function schedule() {
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => {
    queued = false;
    if (pending) paint(pending.canvas, pending.values, pending.mini);
  });
}

/** Redraw the cell for these slider values (radius, texture, smoothness, concavity, worst concave points). */
export function drawCell(canvas: HTMLCanvasElement, values: number[], mini: HTMLCanvasElement | null) {
  pending = { canvas, values, mini };
  schedule();
}

function paint(cell: HTMLCanvasElement, v: number[], mini: HTMLCanvasElement | null) {
  const g = cell.getContext("2d");
  if (!g) return;
  if (!layer) {
    layer = document.createElement("canvas");
    layer.width = cell.width;
    layer.height = cell.height;
  }
  const size = Math.pow(v[0] / 12.2, 0.6);              // nucleus size: the whole nucleus grows or shrinks
  const texture = clamp01((v[1] - 9) / 31);             // texture: even → coarse, speckled chromatin
  const rough = clamp01((v[2] - 0.08) / 0.08) * 0.17;   // smoothness: a smooth edge → a ragged one
  const depth = 0.04 + 0.85 * clamp01(v[3] / 0.43);     // concavity: how deep each dent goes
  const dents = 1 + 9 * clamp01((v[4] - 0.05) / 0.24); // concave points (worst): how many dents
  // nuclei go on their own layer first, so the whole layer can be softened once to match the photo's blur
  const l = layer.getContext("2d")!;
  l.setTransform(2, 0, 0, 2, 0, 0);
  l.clearRect(0, 0, 570, 490);
  NUCLEI.forEach(([x, y, r0, e, a], i) => {
    const rnd = seeded(i * 7919 + 13);
    const R = r0 * size * (0.92 + 0.16 * rnd());
    const f1 = 7 + Math.floor(rnd() * 5), f2 = 13 + Math.floor(rnd() * 7), p1 = rnd() * 6.283, p2 = rnd() * 6.283;
    const dd = depth * (0.75 + 0.5 * rnd());
    const n = Math.max(1, Math.round(dents + (rnd() - 0.5) * 2));
    const at = Array.from({ length: 11 }, (_, j) => p2 + j * 2.39996 + (rnd() - 0.5) * 0.4).slice(0, n); // golden-angle spread
    const path = new Path2D();
    for (let k = 0; k <= 96; k++) {
      const th = (k / 96) * 2 * Math.PI, c = Math.cos(th - a), s = Math.sin(th - a);
      let rr = 1 / Math.sqrt((c / e) ** 2 + (s * e) ** 2);
      rr *= 1 + rough * (0.6 * Math.sin(f1 * th + p1) + 0.4 * Math.sin(f2 * th + p2));
      let dent = 0;
      at.forEach((phi) => { const d = Math.atan2(Math.sin(th - phi), Math.cos(th - phi)); dent += Math.exp((-d * d) / 0.05); });
      rr *= 1 - Math.min(0.7, dd * dent);
      const px = x + Math.cos(th) * R * rr, py = y + Math.sin(th) * R * rr;
      if (k) path.lineTo(px, py); else path.moveTo(px, py);
    }
    path.closePath();
    // flat stain like the real slide: one even purple per nucleus and a soft bluish rim
    const tone = rnd(), warm = rnd() ** 2;
    l.lineWidth = 2.5;
    l.strokeStyle = "rgba(52,62,99,.5)";
    l.stroke(path);
    l.fillStyle = `rgb(${Math.round(38 + 12 * tone + 26 * warm)},${Math.round(29 + 15 * tone)},${Math.round(72 + 20 * tone - 8 * warm)})`;
    l.fill(path);
    // chromatin: faint mottling when even, coarse dark clumps when speckled
    const grain = seeded(i * 104729 + 7);
    l.save();
    l.clip(path);
    const count = Math.round(R * R * (0.04 + 0.22 * texture));
    for (let k = 0; k < count; k++) {
      const ang = grain() * 6.283, rad = Math.sqrt(grain()) * R, dark = grain() < 0.6, w = 0.8 + grain() * (1 + 1.8 * texture);
      l.fillStyle = dark ? `rgba(22,12,44,${0.15 + 0.5 * texture})` : `rgba(88,76,132,${0.12 + 0.35 * texture})`;
      l.fillRect(x + Math.cos(ang) * rad - w / 2, y + Math.sin(ang) * rad - w / 2, w, w);
    }
    l.restore();
  });
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, cell.width, cell.height);
  if (background.complete && background.naturalWidth) g.drawImage(background, 0, 0, cell.width, cell.height);
  g.filter = "blur(1.2px)"; // ignored by browsers without canvas filters; the nuclei are then a touch sharper
  g.globalAlpha = 0.95;
  g.drawImage(layer, 0, 0);
  g.globalAlpha = 1;
  g.filter = "none";
  mini?.getContext("2d")?.drawImage(cell, 0, 0, mini.width, mini.height);
}
