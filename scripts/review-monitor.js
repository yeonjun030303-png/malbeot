// 후기모니터링 봇 (운영팀) - 매주 화 17:00
// Firebase 'reviews' 노드에서 이번 주 신규 후기 조회, 저평점 후기 강조
// 필드명 추정: rating/score, createdAt/timestamp/date, content/text/comment

const { initializeApp, cert } = require('firebase-admin/app');
const { getDatabase } = require('firebase-admin/database');
const fs = require('fs');

const FIREBASE_TIMEOUT_MS = 60000;
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} - ${ms / 1000}초 응답 없음(타임아웃)`)), ms))
  ]);
}

function pickCreatedAt(r) { return r.createdAt || r.timestamp || r.date || null; }
function pickRating(r) { return Number(r.rating || r.score || 0); }

async function main() {
  const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  initializeApp({ credential: cert(serviceAccount), databaseURL: process.env.FIREBASE_DB_URL });
  const db = getDatabase();

  const snap = await withTimeout(db.ref('reviews').once('value'), FIREBASE_TIMEOUT_MS, 'reviews 읽기');
  const obj = snap.val() || {};
  const list = Object.keys(obj).map(id => ({ id, ...obj[id] }));

  const now = Date.now();
  const thisWeek = list.filter(r => { const c = pickCreatedAt(r); return c && (now - Number(c)) <= WEEK_MS; });

  if (thisWeek.length === 0) {
    console.log('이번 주 신규 후기 없음 - 리포트 생략');
    return;
  }

  const ratings = thisWeek.map(pickRating).filter(n => n > 0);
  const avg = ratings.length ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(2) : '평점 필드 미확인';
  const lowRated = thisWeek.filter(r => pickRating(r) > 0 && pickRating(r) <= 2);

  const lines = [];
  lines.push('## ⭐ 후기 모니터링 (이번 주)');
  lines.push('');
  lines.push(`- 신규 후기: ${thisWeek.length}건`);
  lines.push(`- 평균 평점: ${avg}`);
  lines.push(`- 저평점(2점 이하) 후기: ${lowRated.length}건`);
  lines.push('');
  if (lowRated.length > 0) {
    lines.push('### ⚠️ 저평점 후기 목록');
    lowRated.forEach(r => {
      const content = (r.content || r.text || r.comment || '(내용 없음)').toString().slice(0, 150);
      lines.push(`- [${pickRating(r)}점] ${content}`);
    });
    lines.push('');
  }
  lines.push('### 필드 감지 참고 (실제 필드명과 다르면 스크립트 수정 필요)');
  lines.push('- 후기함 노드: reviews');
  lines.push('- 평점 필드 추정: rating / score');
  lines.push('- 작성시각 필드 추정: createdAt / timestamp / date');
  lines.push('- 내용 필드 추정: content / text / comment');

  fs.writeFileSync('review-monitor-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().catch(err => {
  console.error('후기모니터링 실패:', err);
  process.exit(1);
});
