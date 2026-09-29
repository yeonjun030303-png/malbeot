// ㈜영정철강 콘텐츠 후보 생성봇 (반자동: 이메일 발송만, 자동 게시 없음)
// 흐름: 아이디어(Gemini 텍스트) -> 이미지 3장(Nano Banana Pro) -> 이메일 첨부 발송
const nodemailer = require('nodemailer');

const KEY = process.env.GEMINI_API_KEY;
const TEXT_MODEL = process.env.YJ_TEXT_MODEL || 'gemini-2.5-flash';
const IMG_MODELS = ['gemini-3-pro-image-preview', 'gemini-2.5-flash-image']; // 1순위 실패 시 폴백
const BASE = 'https://generativelanguage.googleapis.com/v1beta/models/';

const STYLE = '스마트폰으로 몰래 찍은 듯한 극사실적 저화질 사진, 형광등 아래 어둡고 채도 낮은 청회색 톤, 강한 비네트, 필름 그레인, 사선 구도. 사람 얼굴은 절대 보이지 않게(뒷모습/실루엣만). 주소, 사업자등록번호, 실존 기업 로고는 넣지 말 것. 회사명은 ㈜영정철강.';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function gem(model, body, tries = 3) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(`${BASE}${model}:generateContent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': KEY },
        body: JSON.stringify(body),
      });
      if (res.ok) return await res.json();
      last = new Error(`${model} HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
      if (![429, 500, 503].includes(res.status)) break;
    } catch (e) { last = e; }
    await sleep(4000 * (i + 1));
  }
  throw last;
}

async function makeIdea() {
  const prompt = `너는 가상 중소기업 ㈜영정철강(철강 유통·가공, 1987년 설립)의 사내 소식 아카이브 인스타 계정 기획자다.
오늘 올릴 "사내 실태점검" 콘텐츠 1건을 기획하라.
- 딱딱한 관공서식 표/문서 형태 + 반전 요소(사소한 걸 국가기밀처럼 다룸 / 신조어가 공식 문서에 등장 / 예상 밖 결말) 중 하나
- 구체적 숫자 포함 (예: "시간당 12회")
- 얼굴 노출 금지, 주소·사업자번호 항목 금지
- 5일 중 4일은 앱 언급 없이, 1일만 캡션 끝에 '말벗' 앱을 아주 약하게 연결. 오늘 요일 번호: ${new Date().getUTCDate() % 5} (0이면 약한 연결 포함)
JSON만 출력: {"topic":"소재","hook":"반전 설명","caption":"캡션(해시태그 제외)","hashtags":["..."],"scenes":["이미지1 장면 묘사","이미지2 장면 묘사","이미지3 장면 묘사"]}
scenes 3개는 서로 구도/소품이 확실히 다르게, 문서/표에 들어갈 한글 문구도 구체적으로 적어라.`;
  const j = await gem(TEXT_MODEL, {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { responseMimeType: 'application/json' },
  });
  const txt = j.candidates[0].content.parts.map((p) => p.text || '').join('');
  return JSON.parse(txt.replace(/```json|```/g, '').trim());
}

async function makeImage(scene) {
  const full = `${scene}\n\n${STYLE}\n비율 4:5 세로.`;
  let err;
  for (const m of IMG_MODELS) {
    try {
      const j = await gem(m, {
        contents: [{ parts: [{ text: full }] }],
        generationConfig: { responseModalities: ['IMAGE'], imageConfig: { aspectRatio: '4:5' } },
      }, 2);
      const part = j.candidates[0].content.parts.find((p) => p.inlineData);
      if (part) return { buf: Buffer.from(part.inlineData.data, 'base64'), model: m, prompt: full, mime: part.inlineData.mimeType || 'image/png' };
      err = new Error(`${m}: 이미지 없음`);
    } catch (e) { err = e; }
  }
  throw err;
}

async function send(subject, html, attachments) {
  const t = nodemailer.createTransport({ service: 'gmail', auth: { user: process.env.MAIL_USER, pass: process.env.MAIL_PASS } });
  await t.sendMail({ from: process.env.MAIL_USER, to: process.env.MAIL_TO, subject, html, attachments });
}

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

(async () => {
  try {
    if (!KEY) throw new Error('GEMINI_API_KEY 없음');
    const idea = await makeIdea();
    const atts = []; const notes = [];
    for (let i = 0; i < 3; i++) {
      try {
        const r = await makeImage(idea.scenes[i]);
        const ext = r.mime.includes('jpeg') ? 'jpg' : 'png';
        atts.push({ filename: `후보${i + 1}.${ext}`, content: r.buf });
        notes.push(`<li><b>후보${i + 1}</b> (${esc(r.model)})<br><small>${esc(r.prompt)}</small></li>`);
      } catch (e) {
        notes.push(`<li><b>후보${i + 1}</b> 생성 실패: ${esc(e.message)}</li>`);
      }
    }
    const tags = (idea.hashtags || []).map((h) => '#' + String(h).replace(/^#/, '')).join(' ');
    const html = `<h3>오늘의 소재: ${esc(idea.topic)}</h3><p>반전: ${esc(idea.hook)}</p>
<h4>캡션</h4><p style="white-space:pre-wrap">${esc(idea.caption)}\n\n${esc(tags)}</p>
<h4>이미지 후보 / 프롬프트</h4><ol>${notes.join('')}</ol>
<p>※ 자동 게시 없음. 마음에 드는 후보를 골라 직접 업로드하세요.</p>`;
    await send('[정기] 영정철강 콘텐츠 후보 보고의 건', html, atts);
    console.log(`완료: 첨부 ${atts.length}장`);
  } catch (e) {
    console.error('실패:', e.message);
    try { await send('[정기] 영정철강 콘텐츠 후보 보고의 건 (생성 실패)', `<p>오늘 생성 실패: ${esc(e.message)}</p>`, []); } catch (_) {}
    process.exit(0); // 실패 리포트 후 정상 종료
  }
})();
