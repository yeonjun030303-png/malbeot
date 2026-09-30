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

const BASE_SCENES = [
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

// ---------- 4-2) 면담 몰카 시점 / 단톡방 캡처 장면 ----------
const DEFAULT_CHAT = [
  ['이 부장', '자재창고 재고실사표 봤나'],
  ['이 부장', '[이미지]'],
  ['이 부장', '수량 안 맞는 이유 오늘 중으로 보고해'],
  ['박 대리', '네 확인하겠습니다'],
  ['최 사원', '죄송합니다 바로 확인하겠습니다'],
];
async function renderChat(chat, docPng) {
  const puppeteer = require('puppeteer');
  const room = (chat && chat.room) || '생산관리팀 (12)';
  const lines = chat && Array.isArray(chat.lines) && chat.lines.length ? chat.lines.slice(0, 8) : DEFAULT_CHAT;
  const uri = 'data:image/png;base64,' + docPng.toString('base64');
  const palette = ['#8fa4b8', '#b89f8f', '#9fb88f', '#a08fb8'];
  const colorOf = {}; let ci = 0, prev = null;
  const rows = lines.map(([who, text], i) => {
    const time = `오전 10:${String(12 + Math.floor(i / 2)).padStart(2, '0')}`;
    const isImg = text === '[이미지]';
    const inner = isImg
      ? `<img src="${uri}" style="width:450px;border-radius:14px;display:block"/>`
      : `<div style="padding:16px 22px;font-size:32px;line-height:1.4;word-break:keep-all">${esc(text)}</div>`;
    if (who === '나') {
      return `<div style="display:flex;justify-content:flex-end;align-items:flex-end;margin:10px 0"><div style="font-size:20px;color:#4d5a66;margin-right:10px">${time}</div><div style="background:#fee500;border-radius:20px 6px 20px 20px;max-width:470px;overflow:hidden">${inner}</div></div>`;
    }
    if (!colorOf[who]) colorOf[who] = palette[ci++ % palette.length];
    const first = prev !== who; prev = who;
    const avatar = first ? `<div style="width:66px;height:66px;border-radius:26px;background:${colorOf[who]};flex:none"></div>` : `<div style="width:66px;flex:none"></div>`;
    const name = first ? `<div style="font-size:23px;color:#33414d;margin:0 0 6px 4px">${esc(who)}</div>` : '';
    return `<div style="display:flex;gap:14px;margin:${first ? 22 : 8}px 0">${avatar}<div>${name}<div style="display:flex;align-items:flex-end;gap:10px"><div style="background:#fff;border-radius:${first ? '6px 20px 20px 20px' : '20px'};max-width:470px;overflow:hidden">${inner}</div><div style="font-size:20px;color:#4d5a66;line-height:1.25;text-align:left"><span style="color:#e0a000">${i % 3 === 0 ? '2' : '1'}</span><br>${time}</div></div></div></div>`;
  }).join('');
  const html = `<html><body style="margin:0;width:750px;height:1400px;background:#abc1d1;font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif;position:relative;overflow:hidden">
<div style="height:62px;padding:0 34px;display:flex;justify-content:space-between;align-items:center;font-size:26px;font-weight:700;color:#111"><span>10:15</span><span style="font-size:22px">LTE ▂▄▆</span></div>
<div style="height:92px;padding:0 30px;display:flex;justify-content:space-between;align-items:center;color:#111"><span style="font-size:34px;font-weight:700">‹ &nbsp;${esc(room)}</span><span style="font-size:30px">⌕ &nbsp;☰</span></div>
<div style="text-align:center;margin:14px 0 6px"><span style="background:rgba(0,0,0,0.22);color:#fff;font-size:22px;border-radius:24px;padding:8px 22px">2026년 9월 30일 수요일</span></div>
<div style="padding:0 26px">${rows}</div>
<div style="position:absolute;left:0;right:0;bottom:0;height:118px;background:#fff;display:flex;align-items:center;gap:18px;padding:0 24px"><span style="font-size:44px;color:#555">＋</span><div style="flex:1;height:70px;border-radius:35px;background:#f1f1f1;line-height:70px;padding-left:26px;font-size:26px;color:#999">메시지 입력</div><span style="font-size:36px;color:#555">☺</span></div>
</body></html>`;
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 750, height: 1400, deviceScaleFactor: 1 });
    await page.setContent(html);
    return await page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 750, height: 1400 } });
  } finally { await browser.close(); }
}

// 역광을 받은 뒷모습 실루엣 (고개 숙인 직원)
function seated(x, y, s, bow) {
  const d = bow * 26;
  return `<g transform="translate(${x} ${y}) scale(${s})"><path d="M-150,330 Q-150,120 -70,98 Q-30,88 -22,70 L22,70 Q30,88 70,98 Q150,120 150,330 Z" fill="#07090d"/><ellipse cx="0" cy="${-8 + d}" rx="50" ry="62" fill="#050608"/><path d="M-150,330 Q-150,120 -70,98 Q-30,88 -22,70" fill="none" stroke="#6f93c4" stroke-opacity="0.28" stroke-width="4"/><path d="M-48,${-40 + d} Q0,${-78 + d} 48,${-40 + d}" fill="none" stroke="#6f93c4" stroke-opacity="0.32" stroke-width="4"/></g>`;
}
// 화면 옆에 서서 자료를 가리키는 부장 실루엣
function boss(x, y, s) {
  return `<g transform="translate(${x} ${y}) scale(${s})" fill="#06080c"><circle cx="0" cy="0" r="40"/><rect x="-16" y="30" width="32" height="30"/><path d="M-95,80 Q-95,52 -50,50 L50,50 Q95,52 95,80 L105,300 L-105,300 Z"/><path d="M-100,300 L-70,720 L-15,720 L0,420 L15,720 L70,720 L100,300 Z"/><path d="M-78,72 L-190,-20 L-206,-2 L-96,110 Z"/><line x1="-200" y1="-10" x2="-340" y2="-125" stroke="#0a0c10" stroke-width="7"/></g>`;
}
function sceneInterview(aspect) {
  const quad = fit([[80, 240], [790, 212], [805, 690], [70, 725]], aspect);
  const bg = svg(`<defs><linearGradient id="wa" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b222b"/><stop offset="1" stop-color="#0a0d12"/></linearGradient>
<radialGradient id="beam" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#9cc2ff" stop-opacity="0.55"/><stop offset="1" stop-color="#9cc2ff" stop-opacity="0"/></radialGradient>
<linearGradient id="tb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a241d"/><stop offset="1" stop-color="#0c0a08"/></linearGradient></defs>
<rect width="${W}" height="${H}" fill="url(#wa)"/><polygon points="0,0 ${W},0 ${W - 90},170 90,170" fill="#262d36"/>
<rect x="160" y="50" width="250" height="34" fill="#dfe8f2" opacity="0.75" filter="url(#b6)"/><rect x="640" y="56" width="250" height="34" fill="#dfe8f2" opacity="0.75" filter="url(#b6)"/>
<ellipse cx="440" cy="480" rx="650" ry="470" fill="url(#beam)" filter="url(#b60)"/>
<polygon points="${poly(grow(quad, 20))}" fill="#0b0b0c"/><polygon points="${poly(quad)}" fill="#e2e9f3"/>
${boss(930, 430, 0.62)}
<polygon points="0,800 ${W},775 ${W},1010 0,1010" fill="url(#tb)"/><polygon points="0,800 ${W},775 ${W},790 0,815" fill="#6d86a8" opacity="0.35"/>
<polygon points="140,850 330,842 340,880 130,890" fill="#cfd6df" opacity="0.8"/><polygon points="560,840 760,834 768,872 552,880" fill="#c3cbd6" opacity="0.8"/>`);
  const fg = svg(`<defs><linearGradient id="gl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.2"/><stop offset="0.5" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<polygon points="${poly(quad)}" fill="url(#gl)"/>
<g filter="url(#b3)">${seated(20, 1010, 1.7, 1)}${seated(390, 1040, 1.45, 1.5)}${seated(800, 1000, 1.6, 0.6)}</g>
<ellipse cx="90" cy="1340" rx="300" ry="130" fill="#000" opacity="0.85" filter="url(#b14)"/>`);
  return { bg, fg, quad, tint: [0.92, 0.97, 1.04], cast: [0.94, 1, 1.08], tex: 'dark conference room wall' };
}
function sceneChat(aspect) {
  const quad = fit([[290, 190], [815, 235], [795, 1180], [255, 1140]], aspect);
  const bg = svg(`<defs><linearGradient id="dk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4a3826"/><stop offset="1" stop-color="#17110c"/></linearGradient>
<filter id="wd"><feTurbulence type="fractalNoise" baseFrequency="0.012 0.35" numOctaves="3" seed="${Math.floor(rnd(1, 99))}"/><feColorMatrix type="matrix" values="0 0 0 0 0.1  0 0 0 0 0.06  0 0 0 0 0.03  0 0 0 1.3 -0.3"/></filter>
<radialGradient id="lamp" cx="20%" cy="10%" r="70%"><stop offset="0" stop-color="#ffd9a0" stop-opacity="0.35"/><stop offset="1" stop-color="#ffd9a0" stop-opacity="0"/></radialGradient></defs>
<rect width="${W}" height="${H}" fill="url(#dk)"/><rect width="${W}" height="${H}" filter="url(#wd)"/><rect width="${W}" height="${H}" fill="url(#lamp)"/>
<g><circle cx="935" cy="1190" r="92" fill="#000" opacity="0.4" filter="url(#b14)"/><circle cx="935" cy="1190" r="82" fill="#e9e5dc"/><circle cx="935" cy="1190" r="62" fill="#3a2316"/><path d="M1015 1170 q45 5 40 40 q-5 30 -42 25" fill="none" stroke="#e9e5dc" stroke-width="16"/></g>
<g transform="rotate(-24 150 1230)"><rect x="40" y="1224" width="300" height="14" rx="7" fill="#1c3a6e"/><rect x="300" y="1224" width="50" height="14" rx="7" fill="#d9d9d9"/></g>
<polygon points="${poly(off(quad, 14, 20))}" fill="#000" opacity="0.5" filter="url(#b14)"/>
<polygon points="${poly(grow(quad, 40))}" fill="#dbe7f5" opacity="0.5" filter="url(#b60)"/>
<polygon points="${poly(grow(quad, 22))}" fill="#0a0a0b" stroke="#0a0a0b" stroke-width="30" stroke-linejoin="round"/>`);
  const fg = svg(`<defs><linearGradient id="gl2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.16"/><stop offset="0.45" stop-color="#fff" stop-opacity="0"/></linearGradient></defs><polygon points="${poly(quad)}" fill="url(#gl2)"/>`);
  return { bg, fg, quad, tint: [0.97, 0.97, 1], cast: [1.03, 1, 0.94], tex: 'dark wooden desk surface top view' };
}
const SCENE_DEFS = [
  { kind: 'doc', make: sceneInterview },
  { kind: 'chat', make: sceneChat },
  { kind: 'doc', make: (a) => (new Date().getUTCDate() % 2 ? BASE_SCENES[1](a) : BASE_SCENES[2](a)) },
];
const docCache = new Map();
function getDoc(idea, opts) {
  if (opts.docPng) return Promise.resolve(opts.docPng);
  const k = JSON.stringify(idea.doc || idea.topic || '');
  if (!docCache.has(k)) docCache.set(k, renderDoc(idea.doc || { title: idea.topic, columns: [], rows: [] }));
  return docCache.get(k);
}

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
  const docPng = await getDoc(idea, opts);
  let def = SCENE_DEFS[idx % 3], srcPng = docPng;
  if (def.kind === 'chat') {
    try { srcPng = opts.chatPng || (await renderChat(idea.chat, docPng)); }
    catch (e) { console.error('단톡방 렌더 실패, 게시판 장면으로 대체:', e.message); def = { kind: 'doc', make: BASE_SCENES[1] }; }
  }
  const isChat = def.kind === 'chat';
  const { data, info } = await sharp(srcPng).resize({ width: isChat ? 750 : 900 }).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const sc = def.make(info.width / info.height);
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
