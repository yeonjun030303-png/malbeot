// 2차 작업: 렌더링된 한글 문서를 "사원이 몰래 찍은 사진" 장면에 원근 합성한다.
// 장면 3종: 0=회의실 빔프로젝터 화면 / 1=사내 게시판(코르크) / 2=복도 벽 대자보
// 배경 질감은 Cloudflare/HuggingFace 무료 AI(키가 있을 때)로 얹고, 없으면 자체 생성 장면만 사용한다.
const sharp = require('sharp');
const W = 1080, H = 1350;
const esc = (s) => String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const rnd = (a, b) => a + Math.random() * (b - a);

// ---------- 1) 한글 문서 렌더 (puppeteer) ----------
async function renderDoc(doc) {
  const puppeteer = require('puppeteer');
  const cols = doc.columns || [], rows = doc.rows || [];
  const html = `<html><body style="margin:0;background:#fff;font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif">
<div id="d" style="display:inline-block;padding:28px 34px;background:#fff;min-width:900px">
<div style="font-size:44px;font-weight:800">${esc(doc.title)}</div>
${doc.subtitle ? `<div style="text-align:right;font-size:22px;color:#444;margin:6px 0 14px">${esc(doc.subtitle)}</div>` : ''}
<table style="border-collapse:collapse;width:100%;font-size:30px">
<tr>${cols.map((c) => `<th style="background:#c8d96b;border:2px solid #333;padding:12px 10px">${esc(c)}</th>`).join('')}</tr>
${rows.map((r) => `<tr>${r.map((c) => `<td style="border:2px solid #333;padding:14px 10px;text-align:center">${esc(c)}</td>`).join('')}</tr>`).join('')}
</table>
${doc.footer ? `<div style="margin-top:14px;font-size:22px;color:#333">${esc(doc.footer)}</div>` : ''}
</div></body></html>`;
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1200, height: 1400, deviceScaleFactor: 1 });
    await page.setContent(html);
    return await (await page.$('#d')).screenshot({ type: 'png' });
  } finally { await browser.close(); }
}

// ---------- 2) 무료 AI 배경 질감 (선택) ----------
async function texCloudflare(prompt) {
  const r = await fetch(`https://api.cloudflare.com/client/v4/accounts/${process.env.CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.CF_API_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, steps: 6 }),
    signal: AbortSignal.timeout(60000),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return Buffer.from((await r.json()).result.image, 'base64');
}
async function texHF(prompt) {
  const r = await fetch('https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell', {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.HF_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ inputs: prompt }),
    signal: AbortSignal.timeout(60000),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}
async function tryTexture(prompt) {
  const tries = [];
  if (process.env.CF_ACCOUNT_ID && process.env.CF_API_TOKEN) tries.push(['cloudflare', texCloudflare]);
  if (process.env.HF_TOKEN) tries.push(['huggingface', texHF]);
  for (const [name, fn] of tries) {
    try {
      const b = await fn(prompt + ', no text, no people, photo texture, dim lighting');
      if (b && b.length > 5000) { console.log('질감 생성:', name); return b; }
    } catch (e) { console.error('질감 실패:', name, e.message); }
  }
  return null;
}

// ---------- 3) 원근 변환 ----------
function solveHomography(from, to) { // from(x,y) -> to(u,v)
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const [x, y] = from[i], [u, v] = to[i];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
  }
  const n = 8;
  for (let i = 0; i < n; i++) {
    let p = i;
    for (let r = i + 1; r < n; r++) if (Math.abs(A[r][i]) > Math.abs(A[p][i])) p = r;
    [A[i], A[p]] = [A[p], A[i]]; [b[i], b[p]] = [b[p], b[i]];
    for (let r = i + 1; r < n; r++) {
      const f = A[r][i] / A[i][i];
      for (let c = i; c < n; c++) A[r][c] -= f * A[i][c];
      b[r] -= f * b[i];
    }
  }
  const h = new Array(n);
  for (let i = n - 1; i >= 0; i--) {
    let s = b[i];
    for (let c = i + 1; c < n; c++) s -= A[i][c] * h[c];
    h[i] = s / A[i][i];
  }
  return [[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1]];
}
function warp(src, sw, sh, quad, mul) {
  const out = Buffer.alloc(W * H * 4);
  const M = solveHomography(quad, [[0, 0], [sw - 1, 0], [sw - 1, sh - 1], [0, sh - 1]]);
  const xs = quad.map((p) => p[0]), ys = quad.map((p) => p[1]);
  const x0 = Math.max(0, Math.floor(Math.min(...xs))), x1 = Math.min(W - 1, Math.ceil(Math.max(...xs)));
  const y0 = Math.max(0, Math.floor(Math.min(...ys))), y1 = Math.min(H - 1, Math.ceil(Math.max(...ys)));
  for (let y = y0; y <= y1; y++) {
    for (let x = x0; x <= x1; x++) {
      const d = M[2][0] * x + M[2][1] * y + 1;
      const u = (M[0][0] * x + M[0][1] * y + M[0][2]) / d;
      const v = (M[1][0] * x + M[1][1] * y + M[1][2]) / d;
      if (u < 0 || v < 0 || u > sw - 1 || v > sh - 1) continue;
      const iu = Math.floor(u), iv = Math.floor(v), fu = u - iu, fv = v - iv;
      const iu2 = Math.min(iu + 1, sw - 1), iv2 = Math.min(iv + 1, sh - 1);
      const o = (y * W + x) * 4;
      for (let c = 0; c < 3; c++) {
        const p00 = src[(iv * sw + iu) * 4 + c], p10 = src[(iv * sw + iu2) * 4 + c];
        const p01 = src[(iv2 * sw + iu) * 4 + c], p11 = src[(iv2 * sw + iu2) * 4 + c];
        const val = (p00 * (1 - fu) + p10 * fu) * (1 - fv) + (p01 * (1 - fu) + p11 * fu) * fv;
        out[o + c] = Math.min(255, val * mul[c]);
      }
      out[o + 3] = 255;
    }
  }
  return out;
}

// ---------- 4) 장면 (SVG) ----------
const poly = (pts) => pts.map((p) => p.map((n) => n.toFixed(1)).join(',')).join(' ');
const off = (pts, dx, dy) => pts.map(([x, y]) => [x + dx, y + dy]);
function grow(q, d) {
  const cx = q.reduce((s, p) => s + p[0], 0) / 4, cy = q.reduce((s, p) => s + p[1], 0) / 4;
  return q.map(([x, y]) => { const l = Math.hypot(x - cx, y - cy); return [x + ((x - cx) / l) * d, y + ((y - cy) / l) * d]; });
}
// 문서 가로세로 비율에 맞춰 사각형의 세로 길이를 조정 (글자가 늘어나 보이지 않게)
function fit(q, aspect) {
  const len = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  const w = (len(q[0], q[1]) + len(q[3], q[2])) / 2, h = (len(q[0], q[3]) + len(q[1], q[2])) / 2;
  const k = Math.min(1.35, Math.max(0.7, w / aspect / h));
  return [q[0], q[1], [q[1][0] + (q[2][0] - q[1][0]) * k, q[1][1] + (q[2][1] - q[1][1]) * k], [q[0][0] + (q[3][0] - q[0][0]) * k, q[0][1] + (q[3][1] - q[0][1]) * k]];
}
const DEFS = `<defs><filter id="b3"><feGaussianBlur stdDeviation="3"/></filter><filter id="b6"><feGaussianBlur stdDeviation="6"/></filter><filter id="b14"><feGaussianBlur stdDeviation="14"/></filter><filter id="b60"><feGaussianBlur stdDeviation="60"/></filter></defs>`;
const svg = (inner) => `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">${DEFS}${inner}</svg>`;
function fakeLines(x, y, w, n, color = '#7d7d78') {
  let s = '';
  for (let i = 0; i < n; i++) s += `<rect x="${x}" y="${y + i * 24}" width="${(w * rnd(0.55, 1)).toFixed(0)}" height="9" fill="${color}" opacity="0.7"/>`;
  return s;
}
function paper(x, y, w, h, rot, fill) {
  return `<g transform="rotate(${rot} ${x + w / 2} ${y + h / 2})"><rect x="${x + 7}" y="${y + 9}" width="${w}" height="${h}" fill="#000" opacity="0.4" filter="url(#b6)"/><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/><rect x="${x + 24}" y="${y + 26}" width="${(w * 0.55).toFixed(0)}" height="16" fill="#4a4a48" opacity="0.85"/>${fakeLines(x + 24, y + 64, w - 48, Math.max(2, Math.floor((h - 90) / 24)))}</g>`;
}
const pin = (x, y, c = '#c8302a') => `<circle cx="${x + 6}" cy="${y + 8}" r="14" fill="#000" opacity="0.45" filter="url(#b3)"/><circle cx="${x}" cy="${y}" r="14" fill="${c}"/><circle cx="${x - 4}" cy="${y - 5}" r="5" fill="#fff" opacity="0.6"/>`;
const tape = (x, y, rot) => `<g transform="rotate(${rot} ${x} ${y})"><rect x="${x - 55}" y="${y - 20}" width="110" height="40" fill="#e8dcae" opacity="0.72"/><rect x="${x - 55}" y="${y - 20}" width="110" height="40" fill="#fff" opacity="0.12"/></g>`;

const SCENES = [
  // 0) 회의실 빔프로젝터 화면
  (aspect) => {
    const quad = fit([[170, 340], [915, 305], [930, 850], [150, 880]], aspect);
    const heads = [[150, 1210, 150, 200], [560, 1260, 185, 210], [935, 1215, 140, 185]]
      .map(([cx, cy, rx, ry]) => `<ellipse cx="${cx}" cy="${cy + ry * 0.95}" rx="${rx * 1.9}" ry="${ry * 0.75}"/><ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" stroke="#6f93c4" stroke-opacity="0.3" stroke-width="4"/>`).join('');
    const bg = svg(`<defs><linearGradient id="ce" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#262d36"/><stop offset="1" stop-color="#090c11"/></linearGradient>
<radialGradient id="beam" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#9cc2ff" stop-opacity="0.6"/><stop offset="1" stop-color="#9cc2ff" stop-opacity="0"/></radialGradient></defs>
<rect width="${W}" height="${H}" fill="url(#ce)"/>
<polygon points="0,0 ${W},0 ${W - 110},240 110,240" fill="#2d343d"/>
<rect x="190" y="70" width="250" height="44" fill="#dfe8f2" opacity="0.8" filter="url(#b6)"/><rect x="650" y="80" width="250" height="44" fill="#dfe8f2" opacity="0.8" filter="url(#b6)"/>
<rect x="470" y="150" width="140" height="56" rx="8" fill="#1a1d22"/><circle cx="540" cy="198" r="15" fill="#5a6c86"/>
<ellipse cx="540" cy="610" rx="640" ry="540" fill="url(#beam)" filter="url(#b60)"/>
<polygon points="${poly(grow(quad, 22))}" fill="#0b0b0c"/><polygon points="${poly(quad)}" fill="#e2e9f3"/>`);
    const fg = svg(`<defs><linearGradient id="gl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.22"/><stop offset="0.5" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<polygon points="${poly(quad)}" fill="url(#gl)"/><g fill="#04060a" filter="url(#b3)">${heads}</g>`);
    return { bg, fg, quad, tint: [0.92, 0.97, 1.04], cast: [0.94, 1, 1.08], tex: 'dark conference room wall and ceiling' };
  },
  // 1) 사내 게시판
  (aspect) => {
    const quad = fit([[150, 410], [915, 380], [930, 905], [140, 935]], aspect);
    const bg = svg(`<defs><filter id="ck"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="${Math.floor(rnd(1, 99))}"/><feColorMatrix type="matrix" values="0 0 0 0 0.25  0 0 0 0 0.16  0 0 0 0 0.08  0 0 0 1.4 -0.35"/></filter>
<linearGradient id="lt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.18"/><stop offset="1" stop-color="#000" stop-opacity="0.3"/></linearGradient></defs>
<rect width="${W}" height="${H}" fill="#a97d51"/><rect width="${W}" height="${H}" filter="url(#ck)"/>
${paper(60, 90, 300, 380, -4, '#ece8dc')}${paper(700, 60, 310, 290, 3, '#f3e9a8')}${paper(380, 40, 250, 260, -2, '#cfe0ee')}
${paper(40, 960, 300, 330, 5, '#efece2')}${paper(720, 975, 300, 320, -3, '#e9d9d0')}${paper(400, 1000, 240, 300, 2, '#f1efe6')}
<polygon points="${poly(off(quad, 12, 16))}" fill="#000" opacity="0.5" filter="url(#b14)"/>
<rect x="0" y="0" width="40" height="${H}" fill="#5b3d24"/><rect x="${W - 40}" y="0" width="40" height="${H}" fill="#5b3d24"/><rect x="0" y="0" width="${W}" height="34" fill="#5b3d24"/>
<rect width="${W}" height="${H}" fill="url(#lt)"/>${pin(110, 130)}${pin(330, 70, '#2a5fb0')}${pin(760, 100, '#c8302a')}${pin(120, 1000)}${pin(950, 1020, '#2a5fb0')}`);
    const fg = svg(`${pin(quad[0][0] + 14, quad[0][1] - 2)}${pin(quad[1][0] - 14, quad[1][1] - 2, '#2a5fb0')}${tape(quad[2][0] - 40, quad[2][1] - 10, -20)}${tape(quad[3][0] + 40, quad[3][1] - 8, 18)}`);
    return { bg, fg, quad, tint: [0.95, 0.95, 0.92], cast: [1.06, 1, 0.9], tex: 'cork board texture close up' };
  },
  // 2) 복도 벽 대자보
  (aspect) => {
    const quad = fit([[95, 320], [900, 410], [890, 895], [105, 1010]], aspect);
    const bg = svg(`<defs><linearGradient id="wl" x1="0" y1="0" x2="1" y2="0.6"><stop offset="0" stop-color="#d7dad2"/><stop offset="1" stop-color="#8f938a"/></linearGradient></defs>
<rect width="${W}" height="${H}" fill="url(#wl)"/><rect y="1120" width="${W}" height="230" fill="#7c8078"/><rect y="1110" width="${W}" height="14" fill="#5f635c"/>
<rect x="930" y="0" width="150" height="${H}" fill="#5e4c39"/><rect x="930" y="0" width="14" height="${H}" fill="#2f261c"/><circle cx="975" cy="760" r="18" fill="#b7b2a4"/>
<rect x="150" y="30" width="300" height="34" fill="#f4f7ff" opacity="0.7" filter="url(#b14)"/>
${paper(650, 60, 230, 210, 2, '#e8e6db')}
<polygon points="${poly(off(quad, 10, 14))}" fill="#000" opacity="0.45" filter="url(#b14)"/>`);
    const fg = svg(`${tape(quad[0][0] + 30, quad[0][1] + 18, -24)}${tape(quad[1][0] - 30, quad[1][1] + 18, 26)}${tape(quad[2][0] - 30, quad[2][1] - 16, -22)}${tape(quad[3][0] + 30, quad[3][1] - 16, 24)}`);
    return { bg, fg, quad, tint: [0.97, 0.97, 0.95], cast: [0.97, 1, 1.05], tex: 'painted office corridor wall' };
  },
];

// ---------- 5) 스마트폰 카메라 효과 ----------
async function camera(img, cast) {
  const mask = Buffer.alloc(W * H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const dx = (x - W / 2) / (W / 2), dy = (y - H / 2) / (H / 2);
      const d = Math.sqrt(dx * dx + dy * dy) / 1.41;
      mask[y * W + x] = Math.max(0, Math.min(255, ((d - 0.42) / 0.45) * 255));
    }
  }
  const flat = await sharp(img).removeAlpha().png().toBuffer();
  const blurred = await sharp(flat).blur(5).joinChannel(mask, { raw: { width: W, height: H, channels: 1 } }).png().toBuffer();
  const vign = Buffer.from(`<svg width="${W}" height="${H}"><defs><radialGradient id="g" cx="50%" cy="50%" r="75%"><stop offset="50%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.65"/></radialGradient></defs><rect width="100%" height="100%" fill="url(#g)"/></svg>`);
  const g = Buffer.alloc(W * H);
  for (let i = 0; i < g.length; i++) g[i] = 92 + Math.floor(Math.random() * 74);
  const grain = await sharp(g, { raw: { width: W, height: H, channels: 1 } }).png().toBuffer();
  return sharp(flat)
    .composite([{ input: blurred }, { input: vign }, { input: grain, blend: 'overlay' }])
    .modulate({ saturation: 0.72 })
    .linear(cast, [0, 0, 3])
    .resize(Math.round(W * 0.75))
    .resize(W, H, { kernel: 'cubic' })
    .blur(0.5)
    .jpeg({ quality: 62 })
    .toBuffer();
}

async function compose(idea, idx, opts = {}) {
  const docPng = opts.docPng || (await renderDoc(idea.doc || { title: idea.topic, columns: [], rows: [] }));
  const { data, info } = await sharp(docPng).resize({ width: 900 }).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const sc = SCENES[idx % 3](info.width / info.height);
  let base = await sharp(Buffer.from(sc.bg)).png().toBuffer();
  const tex = await tryTexture(sc.tex);
  if (tex) {
    const t = await sharp(tex).resize(W, H, { fit: 'cover' }).png().toBuffer();
    base = await sharp(base).composite([{ input: t, blend: 'soft-light' }]).png().toBuffer();
  }
  const layer = await sharp(warp(data, info.width, info.height, sc.quad, sc.tint), { raw: { width: W, height: H, channels: 4 } }).png().toBuffer();
  const img = await sharp(base).composite([{ input: layer }, { input: Buffer.from(sc.fg) }]).png().toBuffer();
  return camera(img, sc.cast);
}

module.exports = { compose };
