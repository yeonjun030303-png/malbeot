// ㈜영정철강 콘텐츠 후보 생성봇 (반자동: 이메일 발송만, 자동 게시 없음)
// 흐름: 아이디어(Gemini 텍스트) -> 이미지 3장(Nano Banana Pro) -> 이메일 첨부 발송
const nodemailer = require('nodemailer');

const KEY = process.env.GEMINI_API_KEY;
let TEXT_MODEL = process.env.YJ_TEXT_MODEL || 'gemini-3.8-flash';
let IMG_MODELS = ['gemini-3-pro-image-preview', 'gemini-2.5-flash-image']; // 1순위 실패 시 폴백
const BASE = 'https://generativelanguage.googleapis.com/v1beta/models/';

const STYLE = '스마트폰으로 몰래 찍은 듯한 극사실적 저화질 컬러 사진(흑백 아님), 형광등 아래 다소 어둡고 채도 낮은 청회색 톤이지만 사물과 옷의 실제 색은 알아볼 수 있게, 약한 비네트, 필름 그레인, 사선 구도. 사람이 있으면 반드시 실제 사람처럼 그릴 것: 뒤통수·어깨선·옆모습 뒤쪽·손이 보이고 머리카락 결, 옷 주름, 셔츠·조끼의 색과 질감이 드러나야 함. 얼굴 정면은 보이지 않게 하되, 검은 실루엣·역광으로 까맣게 뭉개진 인물·마네킹·그림자 인물은 금지. 주소, 사업자등록번호, 실존 기업 로고는 넣지 말 것. 회사명은 ㈜영정철강. 광고 사진 같은 깨끗함, 완벽한 대칭, 플라스틱 피부, 깨진 한글, 영어로 바뀐 글자, 손가락 개수 오류, 로고 왜곡은 피할 것.';

// 차별화 원칙: 다른 계정 콘텐츠를 변형/재가공하지 않고 100% 자체 기획만 사용
const FORMATS = [
  '자재창고 재고 실사표에 적힌 이상한 품목/수량(사소한 것을 국가기밀처럼 관리)',
  '사내 안전수칙 게시문 개정안에 신조어가 공식 문구로 들어간 버전',
  '구내식당 주간 배식 공문(철분 강화 메뉴 등 철강회사다운 문구)',
  '지문 인식기 출퇴근 기록 통계와 지각 사유 분류표',
  '결재 문서 반려 사유 코드표(코드마다 엉뚱한 사유)',
  '사내 방송 멘트 대본(점심시간 안내 방송을 엄숙하게)',
];
const YT_QUERIES = ['중소기업 사내규정 불만', '중소기업 명절 선물 현실', '중소기업 직장인 썰', '꼰대 상사 회사 현실', 'MZ 신입 퇴사 이유'];
const THEMES = ['보수적인 사내 분위기', 'MZ 세대의 조용한 반란', '말도 안 되는 중소기업식 마인드'];

async function yt(path, params) {
  const u = new URL('https://www.googleapis.com/youtube/v3/' + path);
  Object.entries({ ...params, key: process.env.YOUTUBE_API_KEY }).forEach(([k, v]) => u.searchParams.set(k, v));
  const r = await fetch(u);
  if (!r.ok) throw new Error(`YouTube ${path} HTTP ${r.status}`);
  return r.json();
}

// 매일 최근 7일 인기 영상 제목 + 상위 댓글(시청자 불만)을 수집
async function getTrends() {
  if (!process.env.YOUTUBE_API_KEY) return '';
  const after = new Date(Date.now() - 7 * 864e5).toISOString();
  const lines = [];
  for (const q of YT_QUERIES) {
    try {
      const s = await yt('search', { part: 'snippet', q, type: 'video', order: 'viewCount', publishedAfter: after, regionCode: 'KR', relevanceLanguage: 'ko', maxResults: 3 });
      for (const it of s.items) lines.push(`[영상] ${it.snippet.title}`);
      const vid = s.items[0] && s.items[0].id.videoId;
      if (vid) {
        try {
          const c = await yt('commentThreads', { part: 'snippet', videoId: vid, order: 'relevance', maxResults: 5, textFormat: 'plainText' });
          for (const t of c.items) lines.push(`[댓글] ${t.snippet.topLevelComment.snippet.textDisplay.slice(0, 120)}`);
        } catch (_) { /* 댓글 막힌 영상은 건너뜀 */ }
      }
    } catch (e) { console.error('트렌드 수집 실패:', q, e.message); }
  }
  return lines.join('\n').slice(0, 3500);
}

const NAVER_QUERIES = ['중소기업 사내규정', '회사 명절 선물 불만', '중소기업 꼰대 문화'];
const NEWS_QUERIES = ['중소기업 직장인 불만', '회사 명절 선물 논란'];
const stripTags = (s) => String(s || '').replace(/<[^>]+>/g, '').replace(/&quot;|&amp;|&#39;|&lt;|&gt;/g, ' ').trim();

// 네이버 검색 API(카페/지식iN/블로그) + 구글 뉴스 RSS에서 최신 화제·불만 수집 (공식 API/RSS만 사용)
async function getCommunityTrends() {
  const lines = [];
  const id = process.env.NAVER_CLIENT_ID, sec = process.env.NAVER_CLIENT_SECRET;
  if (id && sec) {
    for (const q of NAVER_QUERIES) {
      for (const [ep, label] of [['cafearticle', '카페'], ['kin', '지식iN'], ['blog', '블로그']]) {
        try {
          const r = await fetch(`https://openapi.naver.com/v1/search/${ep}.json?query=${encodeURIComponent(q)}&display=3&sort=date`, { headers: { 'X-Naver-Client-Id': id, 'X-Naver-Client-Secret': sec } });
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const j = await r.json();
          for (const it of j.items || []) lines.push(`[${label}] ${stripTags(it.title)} - ${stripTags(it.description).slice(0, 80)}`);
        } catch (e) { console.error('네이버 수집 실패:', ep, q, e.message); }
      }
    }
  }
  for (const q of NEWS_QUERIES) {
    try {
      const r = await fetch(`https://news.google.com/rss/search?q=${encodeURIComponent(q)}&hl=ko&gl=KR&ceid=KR:ko`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const xml = await r.text();
      const titles = [...xml.matchAll(/<item>[\s\S]*?<title>([\s\S]*?)<\/title>/g)].slice(0, 3).map((m) => stripTags(m[1].replace(/<!\[CDATA\[|\]\]>/g, '')));
      titles.forEach((t) => lines.push(`[뉴스] ${t}`));
    } catch (e) { console.error('뉴스 수집 실패:', q, e.message); }
  }
  return lines.join('\n').slice(0, 2500);
}

async function discoverModels() {
  try {
    const res = await fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200', { headers: { 'x-goog-api-key': KEY } });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const j = await res.json();
    const names = (j.models || [])
      .filter((m) => (m.supportedGenerationMethods || []).includes('generateContent'))
      .map((m) => m.name.replace('models/', ''));
    const ver = (n) => { const m = n.match(/(\d+(?:\.\d+)?)/); return m ? parseFloat(m[1]) : 0; };
    const stab = (n) => (/preview|exp/i.test(n) ? 0 : 1);
    const texts = names
      .filter((n) => /flash/i.test(n) && !/image|tts|live|audio|lite|8b|native|robotics|computer/i.test(n))
      .sort((a, b) => ver(b) - ver(a) || stab(b) - stab(a));
    const imgs = names
      .filter((n) => /image/i.test(n) && !/tts|live|audio/i.test(n))
      .sort((a, b) => (/pro/i.test(b) - /pro/i.test(a)) || ver(b) - ver(a) || stab(b) - stab(a));
    if (texts.length && !process.env.YJ_TEXT_MODEL) TEXT_MODEL = texts[0];
    TEXT_LIST = texts.slice(0, 4);
    if (imgs.length) IMG_MODELS = imgs.slice(0, 3);
    console.log('사용 모델 - 텍스트:', TEXT_MODEL, '/ 이미지:', IMG_MODELS.join(', '));
  } catch (e) { console.error('모델 목록 조회 실패(기본값 사용):', e.message); }
}

let TEXT_LIST = [];
// 텍스트 모델이 과부하(503) 등으로 실패하면 다음 모델로 넘어가며 시도
async function gemText(body) {
  const order = [...new Set([TEXT_MODEL, ...TEXT_LIST])];
  let last;
  for (const m of order) {
    try {
      return await gem(m, body, 3);
    } catch (e) {
      last = e;
      console.error('텍스트 모델 실패:', m, String(e.message).slice(0, 80));
      await sleep(5000);
    }
  }
  throw last;
}

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
  const trends = [await getTrends(), await getCommunityTrends()].filter(Boolean).join('\n').slice(0, 6000);
  const prompt = `너는 가상 중소기업 ㈜영정철강(철강 유통·가공, 1987년 설립)의 사내 소식 아카이브 인스타 계정 기획자다.
오늘 올릴 콘텐츠 1건을 기획하라.
[컨셉] 사원이 회사 몰래 사진 찍어 올린 내부고발/제보 톤. 캡션은 사원 1인칭 시점의 건조하고 억울한 말투.
[오늘 날짜] ${new Date().toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })} (extras·doc·chat의 날짜와 요일은 이 날짜 기준으로 맞출 것)
[오늘의 테마] ${THEMES[new Date().getUTCDate() % 3]} (보수적 분위기 / MZ의 반란 / 중소기업식 마인드: 명절 선물, 사내 규정, 직원 불만 등)
[트렌드 자료: 유튜브 화제 영상·댓글, 커뮤니티·뉴스 글] 흐름과 불만 포인트만 요약해 반영하고, 제목·댓글 문장을 그대로 베끼지 말 것. 실존 기업·인물 실명 금지.
${trends || '(수집된 자료 없음. 일반적인 중소기업 직장인 불만 소재로 기획)'}
- 딱딱한 관공서식 표/문서 형태 + 반전 요소(사소한 걸 국가기밀처럼 다룸 / 신조어가 공식 문서에 등장 / 예상 밖 결말) 중 하나
- 구체적 숫자 포함 (예: "시간당 12회")
- 얼굴 노출 금지, 주소·사업자번호 항목 금지
- 오늘의 포맷 씨앗(이 방향으로만 기획): ${FORMATS[new Date().getUTCDate() % FORMATS.length]}
- 다른 기업 계정(특히 태산금형)의 게시물을 따라 하거나 변형하지 말 것. 다음 소재는 이미 다른 계정이 쓴 것이므로 금지: MZ 어투 사용 현황표, 고사/제사 사진, 그림 시험지 만화, 명절 선물 증정식, 부서장 취임 인사문, 금속 조각 작품. 문구·구도·표 구성도 새로 만들 것
- 5일 중 4일은 앱 언급 없이, 1일만 캡션 끝에 '말벗' 앱을 아주 약하게 연결. 오늘 요일 번호: ${new Date().getUTCDate() % 5} (0이면 약한 연결 포함)
JSON만 출력: {"topic":"소재","trend_summary":"오늘 반영한 트렌드 3줄 요약","hook":"반전 설명","caption":"캡션(해시태그 제외)","hashtags":["..."],"scenes":["이미지1 장면 묘사","이미지2 장면 묘사","이미지3 장면 묘사"],"bg":["글자 없는 배경 사진 묘사1","배경2","배경3"],"doc":{"title":"문서 제목","subtitle":"점검 기간 등 한 줄","columns":["열1","열2","열3"],"rows":[["행1열1","행1열2","행1열3"]],"footer":"각주 한 줄"},"chat":{"room":"단톡방 이름(인원수)","lines":[["직급","메시지"]]}}
scenes 3개는 서로 구도/소품이 확실히 다르게, 문서/표에 들어갈 한글 문구도 구체적으로 적어라.
${require('fs').readFileSync(require('path').join(__dirname, 'yj_detail_rules.txt'), 'utf8')}
doc은 실제 관공서식 표(열 3~4개, 행 4~6개, 구체적 숫자 포함, 얼굴·실명 없음)로 작성하고, bg는 글자가 전혀 없는 배경 사진(창고, 회의실, 게시판 벽 등)을 3개 서로 다르게 묘사하라.
chat은 부장이 위 doc 자료를 단톡방에 올리고 직원을 추궁하는 상황이다. lines는 5~7개, 형식은 [보낸사람, 메시지]. 보낸사람은 "이 부장"처럼 성+직급(실명 금지). 부장의 두 번째 줄은 정확히 "[이미지]"(자료 사진 첨부)로 하고, 나머지는 실제 회사 단톡방 말투(추궁, 눈치 보는 직원의 답장, 어색한 정적 뒤 "넵 확인하겠습니다" 등)로 써라.`;
  const j = await gemText({
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { responseMimeType: 'application/json' },
  });
  const txt = j.candidates[0].content.parts.map((p) => p.text || '').join('');
  return JSON.parse(txt.replace(/```json|```/g, '').trim());
}

let CUR_IDEA = null;
// 1순위: Gemini 이미지 / 실패 시: 배경AI + 한글 문서 렌더 + 합성으로 1장 완성
async function makeImage(scene) {
  try {
    return await makeImageGemini(scene);
  } catch (ge) {
    try {
      const idx = Math.max(0, CUR_IDEA.scenes.indexOf(scene));
      const buf = await require('./yj_composite.js').compose(CUR_IDEA, idx);
      return { buf, model: '자체합성(배경AI+문서렌더)', prompt: scene, mime: 'image/jpeg' };
    } catch (ce) {
      throw new Error(`Gemini: ${String(ge.message).slice(0, 60)} / 합성: ${ce.message}`);
    }
  }
}

async function makeImageGemini(scene) {
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
    await discoverModels();
    const idea = await makeIdea();
    CUR_IDEA = idea;
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
<p>트렌드 반영: ${esc(idea.trend_summary || '없음(YOUTUBE_API_KEY 미설정 또는 수집 실패)')}</p>
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
