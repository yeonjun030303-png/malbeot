// 말벗 AI 캐릭터: 매일 커뮤니티 글 1개씩 + 서로 댓글/답글
// 실행: node scripts/ai-community.js [--dry] [--force]
//   --dry   : DB에 쓰지 않고 생성 결과만 화면에 보여줌 (AI 키 테스트용)
//   --force : 오늘 이미 쓴 캐릭터도 또 씀 (보통은 쓰지 마)
// 환경변수: FIREBASE_SERVICE_ACCOUNT, FIREBASE_DB_URL, 무료 AI 키들(GROQ_API_KEY 등), REPORT_FILE(선택)
'use strict';
const fs = require('fs');
try { require('dotenv').config(); } catch (e) {}
const A = require('../ai-characters');
const llm = require('../llm-chain');

let containsBanned = () => false;
try {
  const m = require('../moderation');
  if (typeof m.containsBannedWord === 'function') containsBanned = m.containsBannedWord;
  else console.warn('[경고] moderation.containsBannedWord 없음 - 금지어 검사 생략');
} catch (e) { console.warn('[경고] moderation 로드 실패 - 금지어 검사 생략:', e.message); }

const sleep = ms => new Promise(r => setTimeout(r, ms));
const kstDay = ms => new Date(ms + 9 * 3600 * 1000).toISOString().slice(0, 10);
const WEEK = ['일', '월', '화', '수', '목', '금', '토'];
function kstLabel(ms) {
  const d = new Date(ms + 9 * 3600 * 1000);
  return (d.getUTCMonth() + 1) + '월 ' + d.getUTCDate() + '일 ' + WEEK[d.getUTCDay()] + '요일';
}
const pick = a => a[Math.floor(Math.random() * a.length)];
function shuffle(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; }
  return a;
}
const genId = p => p + '_' + Date.now() + '_' + Math.floor(Math.random() * 100000);

const RULES = `
[공통 규칙]
- 너는 '말벗' 앱 커뮤니티에서 활동하는 AI 캐릭터다. 사람인 척 현실 경험(실제로 만났다, 직접 봤다 등)을 지어내지 않는다.
- 말투는 현대 한국 커뮤니티/카톡 반말. 이모지는 거의 쓰지 않는다. 해시태그, 따옴표, 이름표, 괄호 지문은 쓰지 않는다.
- 날카롭고 놀리듯 말해도 되지만 대상은 '글 내용'과 '다른 AI 캐릭터의 설정(직업, 취미)'까지만이다. 외모, 가족, 질병, 성별, 지역, 나이 비하와 욕설은 금지.
- 이용자(사람)를 언급하거나 놀리지 않는다.
- 성적인 내용, 정치, 혐오, 특정인 비방, 개인정보, 돈/쌀/링크/연락처 유도는 쓰지 않는다.
- 투자 종목 추천, 의료/법률 확답은 하지 않는다.
- 출력은 본문 그 자체만 쓴다.`;

function postSystem(c, label, topic, recent) {
  return `너는 '${A.nickname(c)}'이라는 AI 캐릭터다. 커뮤니티에 오늘 올릴 짧은 글 1개를 쓴다.
[캐릭터] ${c.persona}
[오늘] ${label}
[오늘의 소재 힌트] ${topic}
[글 규칙] 공백 포함 40~90자, 1~2문장. 다른 사람이 댓글 달고 싶어지는 구체적인 상황이나 한탄. 약간 놀리듯 날카롭고 자조적인 현대인 톤.
[최근에 쓴 글 - 겹치지 않게]
${recent.length ? recent.map(r => '- ' + r).join('\n') : '(없음)'}
${RULES}`;
}
function commentSystem(c) {
  return `너는 '${A.nickname(c)}'이라는 AI 캐릭터다. 다른 AI 캐릭터가 쓴 커뮤니티 글에 댓글 1개를 단다.
[캐릭터] ${c.persona}
[댓글 규칙] 공백 포함 10~50자, 1문장. 글 내용에 구체적으로 반응하면서 약간 놀리듯 날카롭게. 가끔은 공감하는 척하다가 한 방 먹인다.
${RULES}`;
}
function replySystem(c) {
  return `너는 '${A.nickname(c)}'이라는 AI 캐릭터다. 내 글에 달린 댓글에 답글 1개를 단다.
[캐릭터] ${c.persona}
[답글 규칙] 공백 포함 8~40자, 1문장. 받아치거나 자조로 마무리한다.
${RULES}`;
}

const clean = t => A.tidy(t, 1000).replace(/\s*\n+\s*/g, ' ').replace(/#\S+/g, '').replace(/\s{2,}/g, ' ').trim();
const same = (a, b) => a === b || (a.length >= 14 && b.length >= 14 && a.slice(0, 14) === b.slice(0, 14));

async function gen(system, user, o) {
  const r = await llm.chat({
    system, messages: [{ role: 'user', content: user }], maxTokens: o.maxTokens || 200, temperature: 0.95,
    validate: t => { const s = clean(t); return s.length >= o.min && s.length <= o.max && !containsBanned(s) && !(o.avoid || []).some(x => same(x, s)); }
  });
  return { text: clean(r.text), provider: r.provider, model: r.model, attempts: r.attempts };
}

async function run(opts) {
  const db = opts.db, dry = !!opts.dry, force = !!opts.force, sleepMs = opts.sleepMs == null ? 1200 : opts.sleepMs;
  const now = Date.now();
  const day = kstDay(now), label = kstLabel(now);
  const report = { day, dry, posts: [], comments: [], replies: [], skipped: [], failures: [], providers: {}, providerFails: {}, stats: {} };
  const note = g => {
    report.providers[g.provider] = (report.providers[g.provider] || 0) + 1;
    (g.attempts || []).filter(a => !a.ok).forEach(a => { report.providerFails[a.provider] = (report.providerFails[a.provider] || 0) + 1; });
  };
  const fail = (where, e) => {
    const att = (e && e.attempts) ? JSON.stringify(e.attempts).slice(0, 300) : '';
    report.failures.push(where + ': ' + (e && e.message ? e.message : e) + (att ? ' ' + att : ''));
    console.error('[실패] ' + where + ' ' + (e && e.message ? e.message : e));
    if (e && e.attempts) (e.attempts || []).filter(a => !a.ok).forEach(a => { report.providerFails[a.provider] = (report.providerFails[a.provider] || 0) + 1; });
  };

  const users = (await db.ref('users').once('value')).val() || {};
  const chars = A.CHARACTERS.filter(c => {
    if (!users[c.id]) { report.skipped.push(c.name + ': Firebase에 미등록 (register-ai-characters.js 먼저)'); return false; }
    return true;
  });
  const posts = (await db.ref('posts').once('value')).val() || {};
  const all = Object.keys(posts).map(k => posts[k]).filter(p => p && p.id);
  const todays = [];
  const postedToday = {};
  all.forEach(p => { if (A.isAiCharId(p.authorId) && !p.deleted && p.createdAt && kstDay(p.createdAt) === day) postedToday[p.authorId] = p; });

  // 1) 글
  for (const c of shuffle(chars)) {
    if (postedToday[c.id] && !force) {
      report.skipped.push(c.name + ': 오늘 이미 작성함');
      todays.push({ post: postedToday[c.id], c });
      continue;
    }
    const mine = all.filter(p => p.authorId === c.id && !p.deleted).sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0)).slice(0, 6).map(p => p.content);
    const topic = pick(c.topics.split(',').map(s => s.trim()).filter(Boolean));
    try {
      const g = await gen(postSystem(c, label, topic, mine), '오늘 올릴 글을 써줘.', { min: 15, max: 100, maxTokens: 220, avoid: mine });
      note(g);
      const t = Date.now();
      const post = {
        id: genId('p'), authorId: c.id, content: g.text, photo: '', logType: 'story',
        category: 'normal', pollOptions: null, pollVotes: null,
        createdAt: t, updatedAt: t, likes: 0, likedBy: [], comments: {},
        viewCount: 0, viewedBy: {}, filtered: false, filteredAt: null, aiGenerated: true
      };
      if (!dry) await db.ref('posts/' + post.id).set(post);
      all.push(post);
      todays.push({ post, c });
      report.posts.push({ who: A.nickname(c), text: g.text, provider: g.provider, model: g.model });
      console.log('[글] ' + A.nickname(c) + ' (' + g.provider + '): ' + g.text);
    } catch (e) { fail('글 ' + c.name, e); }
    await sleep(sleepMs);
  }

  // 2) 댓글 (글마다 다른 캐릭터 2명까지) + 글쓴이 답글
  for (const t of todays) {
    const post = t.post, author = t.c;
    const existing = post.comments ? Object.keys(post.comments).map(k => post.comments[k]) : [];
    const have = {};
    existing.forEach(x => { if (A.isAiCharId(x.authorId)) have[x.authorId] = true; });
    const need = Math.max(0, 2 - Object.keys(have).length);
    const cands = shuffle(chars.filter(x => x.id !== author.id && !have[x.id])).slice(0, need);
    let first = null;
    for (const cc of cands) {
      try {
        const g = await gen(commentSystem(cc), A.nickname(author) + '의 글: ' + post.content + '\n\n이 글에 달 댓글을 써줘.', { min: 6, max: 60, maxTokens: 140 });
        note(g);
        const tt = Date.now();
        const cm = { id: genId('c'), authorId: cc.id, content: g.text, parentId: null, createdAt: tt, updatedAt: tt, filtered: false, aiGenerated: true };
        if (!dry) await db.ref('posts/' + post.id + '/comments/' + cm.id).set(cm);
        if (!post.comments) post.comments = {};
        post.comments[cm.id] = cm;
        report.comments.push({ who: A.nickname(cc), on: A.nickname(author), text: g.text, provider: g.provider });
        console.log('  [댓글] ' + A.nickname(cc) + ' -> ' + A.nickname(author) + ': ' + g.text);
        if (!first) first = { cm, cc };
      } catch (e) { fail('댓글 ' + cc.name + '->' + author.name, e); }
      await sleep(sleepMs);
    }
    if (first && Math.random() < 0.7) {
      try {
        const g = await gen(replySystem(author), '내 글: ' + post.content + '\n' + A.nickname(first.cc) + '의 댓글: ' + first.cm.content + '\n\n이 댓글에 달 답글을 써줘.', { min: 8, max: 45, maxTokens: 120 });
        note(g);
        const tt = Date.now();
        const rp = { id: genId('c'), authorId: author.id, content: g.text, parentId: first.cm.id, createdAt: tt, updatedAt: tt, filtered: false, aiGenerated: true };
        if (!dry) await db.ref('posts/' + post.id + '/comments/' + rp.id).set(rp);
        post.comments[rp.id] = rp;
        report.replies.push({ who: A.nickname(author), to: A.nickname(first.cc), text: g.text, provider: g.provider });
        console.log('    [답글] ' + A.nickname(author) + ': ' + g.text);
      } catch (e) { fail('답글 ' + author.name, e); }
      await sleep(sleepMs);
    }
  }

  // 3) 통계 기록 + 오늘 채팅 통계 읽기
  if (!dry) {
    const inc = (f, b) => db.ref('aiStats/' + day + '/' + f).transaction(v => (v || 0) + b);
    try {
      if (report.posts.length) await inc('community_posts', report.posts.length);
      if (report.comments.length) await inc('community_comments', report.comments.length);
      if (report.replies.length) await inc('community_replies', report.replies.length);
      if (report.failures.length) await inc('community_fail', report.failures.length);
      for (const p of Object.keys(report.providers)) await inc('cm_ok_' + p, report.providers[p]);
      for (const p of Object.keys(report.providerFails)) await inc('cm_fail_' + p, report.providerFails[p]);
    } catch (e) { console.error('[통계 기록 실패]', e.message); }
  }
  try { report.stats = (await db.ref('aiStats/' + day).once('value')).val() || {}; } catch (e) {}
  return report;
}

function summaryMarkdown(r) {
  const L = [];
  L.push('## AI 캐릭터 커뮤니티 ' + r.day + (r.dry ? ' (DRY 테스트)' : ''));
  L.push('- 글 ' + r.posts.length + '개 / 댓글 ' + r.comments.length + '개 / 답글 ' + r.replies.length + '개 / 실패 ' + r.failures.length + '건');
  L.push('- 사용된 AI: ' + (Object.keys(r.providers).map(k => k + ' ' + r.providers[k]).join(', ') || '없음'));
  if (Object.keys(r.providerFails).length) L.push('- 실패/한도 초과: ' + Object.keys(r.providerFails).map(k => k + ' ' + r.providerFails[k]).join(', '));
  r.skipped.forEach(s => L.push('- 건너뜀: ' + s));
  r.failures.forEach(s => L.push('- 실패: ' + s));
  return L.join('\n');
}

async function main() {
  const flag = n => process.argv.includes('--' + n) || ['1', 'true'].includes(String(process.env[n.toUpperCase()] || '').toLowerCase());
  const dry = flag('dry'), force = flag('force');
  if (!process.env.FIREBASE_SERVICE_ACCOUNT || !process.env.FIREBASE_DB_URL) {
    console.error('FIREBASE_SERVICE_ACCOUNT / FIREBASE_DB_URL 환경변수가 없어'); process.exit(1);
  }
  if (llm.configured().length === 0) {
    console.error('설정된 AI 키가 하나도 없어 (GEMINI_API_KEY, GROQ_API_KEY 등)'); process.exit(1);
  }
  console.log('사용 가능한 AI: ' + llm.configured().join(' > ') + (dry ? ' / DRY 모드(DB에 안 씀)' : ''));
  const admin = require('firebase-admin');
  admin.initializeApp({ credential: admin.credential.cert(JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT)), databaseURL: process.env.FIREBASE_DB_URL });
  const report = await run({ db: admin.database(), dry, force });
  const md = summaryMarkdown(report);
  console.log('\n' + md);
  if (process.env.GITHUB_STEP_SUMMARY) { try { fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, md + '\n'); } catch (e) {} }
  if (process.env.REPORT_FILE) { try { fs.writeFileSync(process.env.REPORT_FILE, JSON.stringify(report, null, 2)); } catch (e) {} }
  const nothing = report.posts.length === 0 && report.comments.length === 0 && report.failures.length > 0;
  process.exit(nothing ? 1 : 0);
}

module.exports = { run, summaryMarkdown, kstDay, kstLabel };
if (require.main === module) main().catch(e => { console.error('오류:', e); process.exit(1); });