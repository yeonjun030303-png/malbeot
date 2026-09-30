// 여러 무료 도구를 조합해 1장의 "몰래 찍은 사진" 이미지를 만든다.
// 1) 배경 사진: Cloudflare(FLUX) -> HuggingFace -> Pollinations -> 자체 생성 순으로 시도 (글자 없는 배경만 요청)
// 2) 한글 표/문서: puppeteer로 직접 렌더링 (AI는 한글이 깨지므로 코드로 정확하게)
// 3) 합성 + 스마트폰 저화질 효과: sharp
const sharp = require('sharp');
const W = 1080, H = 1350;
const esc = (s) => String(s == null ? '' : s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

async function bgCloudflare(prompt) {
  const r = await fetch(`https://api.cloudflare.com/client/v4/accounts/${process.env.CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.CF_API_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, steps: 6 }),
    signal: AbortSignal.timeout(90000),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const j = await r.json();
  return Buffer.from(j.result.image, 'base64');
}
async function bgHF(prompt) {
  const r = await fetch('https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell', {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.HF_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ inputs: prompt }),
    signal: AbortSignal.timeout(90000),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}
async function bgPollinations(prompt) {
  const u = `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=1080&height=1350&model=flux&nologo=true&seed=${Math.floor(Math.random() * 1e6)}`;
  const r = await fetch(u, { signal: AbortSignal.timeout(90000) });
  if (!r.ok || !String(r.headers.get('content-type')).startsWith('image/')) throw new Error(`HTTP ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}
async function proceduralBg() {
  const raw = Buffer.alloc(W * H * 3);
  for (let i = 0; i < raw.length; i += 3) { const v = 55 + Math.floor(Math.random() * 30); raw[i] = v; raw[i + 1] = v + 6; raw[i + 2] = v + 14; }
  return sharp(raw, { raw: { width: W, height: H, channels: 3 } }).blur(14).jpeg().toBuffer();
}
async function getBackground(prompt) {
  const tries = [];
  if (process.env.CF_ACCOUNT_ID && process.env.CF_API_TOKEN) tries.push(['cloudflare', bgCloudflare]);
  if (process.env.HF_TOKEN) tries.push(['huggingface', bgHF]);
  tries.push(['pollinations', bgPollinations]);
  for (const [name, fn] of tries) {
    try {
      const b = await fn(prompt);
      if (b && b.length > 5000) { console.log('배경 생성:', name); return b; }
    } catch (e) { console.error('배경 실패:', name, e.message); }
  }
  console.log('배경 생성: 자체 생성(모든 외부 AI 실패)');
  return proceduralBg();
}

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

const VARIANTS = [
  { angle: -3, scale: 0.84, left: 80, top: 300, dim: 0.5, glow: true },   // 프로젝터 화면
  { angle: 2.5, scale: 0.78, left: 110, top: 290, dim: 0.85, glow: false }, // 게시판 인쇄물
  { angle: -7, scale: 0.76, left: 110, top: 400, dim: 0.8, glow: false },  // 책상 위 서류
];

async function compose(idea, idx, opts = {}) {
  const v = VARIANTS[idx % 3];
  const bgPrompt = ((idea.bg && idea.bg[idx]) || '회사 사무실 내부') + ', no text, no letters, no people, dim fluorescent lighting, blurry smartphone snapshot, low quality, grainy';
  const bg = await sharp(await getBackground(bgPrompt)).resize(W, H, { fit: 'cover' }).modulate({ brightness: v.dim, saturation: 0.6 }).toBuffer();
  const docPng = opts.docPng || (await renderDoc(idea.doc || { title: idea.topic, columns: [], rows: [] }));
  let d = sharp(docPng).resize({ width: Math.round(W * v.scale), height: H - v.top - 120, fit: 'inside' });
  d = v.glow ? d.modulate({ brightness: 0.95 }).tint({ r: 205, g: 220, b: 255 }) : d.modulate({ brightness: 0.82 });
  const doc = await d.ensureAlpha().rotate(v.angle, { background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toBuffer();
  const m = await sharp(doc).metadata();
  const left = Math.max(0, Math.min(v.left, W - m.width - 20));
  const top = Math.max(0, Math.min(v.top, H - m.height - 20));
  const shadow = await sharp(doc).modulate({ brightness: 0 }).blur(14).png().toBuffer();
  let img = await sharp(bg).composite([
    { input: shadow, left: Math.min(left + 14, W - m.width), top: Math.min(top + 18, H - m.height) },
    { input: doc, left, top },
  ]).toBuffer();
  const vign = Buffer.from(`<svg width="${W}" height="${H}"><defs><radialGradient id="g" cx="50%" cy="50%" r="75%"><stop offset="45%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.75"/></radialGradient></defs><rect width="100%" height="100%" fill="url(#g)"/></svg>`);
  const g = Buffer.alloc(W * H);
  for (let i = 0; i < g.length; i++) g[i] = 92 + Math.floor(Math.random() * 74);
  const grain = await sharp(g, { raw: { width: W, height: H, channels: 1 } }).png().toBuffer();
  img = await sharp(img).composite([{ input: vign }, { input: grain, blend: 'overlay' }]).toBuffer();
  return sharp(img)
    .modulate({ saturation: 0.75 })
    .linear([0.95, 1, 1.06], [0, 0, 4])
    .resize(Math.round(W * 0.6))
    .resize(W, H, { kernel: 'cubic' })
    .blur(0.6)
    .jpeg({ quality: 62 })
    .toBuffer();
}

module.exports = { compose };
