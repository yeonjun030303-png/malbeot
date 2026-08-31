// 지표 모니터링 요원 봇
// - Firebase에서 DAU(최근 접속), 신규가입/탈퇴, 구독(골드/플래티넘) 현황을 집계
// - 매주 실행분을 metrics/weekly/<날짜> 에 스냅샷으로 저장해두고, 전주 스냅샷과 비교해 급변 항목 하이라이트
// - 필드 스키마는 2026-08-31 Firebase 콘솔에서 실제 확인 완료 (가입일: uid 파싱 / 최근접속: lastSeen / 구독등급: 필드 없음, 전원 free)

const { initializeApp, cert } = require('firebase-admin/app');
const { getDatabase } = require('firebase-admin/database');
const fs = require('fs');

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
const FIREBASE_TIMEOUT_MS = 60000; // Firebase 요청이 60초 안에 응답 없으면 포기 (무한대기로 6시간 강제종료되는 문제 방지)

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} - ${ms / 1000}초 동안 응답 없음(타임아웃)`)), ms))
  ]);
}

function pickCreatedAt(user) {
  // 2026-08-31 실제 스키마 확인: 가입일 별도 필드 없음. uid가 'u_<가입시각ms>_<랜덤>' 형태라 여기서 파싱함
  if (user.id) {
    const m = String(user.id).match(/^u_(\d+)_/);
    if (m) return Number(m[1]);
  }
  return user.createdAt || user.joinedAt || user.signupAt || null;
}
function pickLastActive(user) {
  // 2026-08-31 실제 스키마 확인: lastSeen(ms 타임스탬프) 하나만 존재
  return user.lastSeen || null;
}
function pickTier(user) {
  // 2026-08-31 실제 스키마 확인: 구독등급 필드 자체가 아직 없음(전원 무료). 추후 필드 추가되면 자동 감지되도록 후보는 남겨둠
  return (user.subscriptionTier || (user.subscription && user.subscription.tier) || user.plan || 'free');
}

async function main() {
  const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  initializeApp({
    credential: cert(serviceAccount),
    databaseURL: process.env.FIREBASE_DB_URL
  });
  const db = getDatabase();

  const snap = await withTimeout(db.ref('users').once('value'), FIREBASE_TIMEOUT_MS, 'users 읽기');
  const usersObj = snap.val() || {};
  const users = Object.keys(usersObj).map(id => ({ id, ...usersObj[id] }));

  const now = Date.now();
  const totalUsers = users.length;

  const newThisWeek = users.filter(u => {
    const c = pickCreatedAt(u);
    return c && (now - Number(c)) <= WEEK_MS;
  }).length;

  const activeThisWeek = users.filter(u => {
    const a = pickLastActive(u);
    return a && (now - Number(a)) <= WEEK_MS;
  }).length;

  const tierCounts = {};
  users.forEach(u => {
    const t = pickTier(u);
    tierCounts[t] = (tierCounts[t] || 0) + 1;
  });

  const snapshot = {
    timestamp: now,
    totalUsers,
    newThisWeek,
    activeThisWeek,
    tierCounts
  };

  // 이번 주 스냅샷 저장
  const weekKey = new Date(now).toISOString().slice(0, 10);
  await withTimeout(db.ref(`metrics/weekly/${weekKey}`).set(snapshot), FIREBASE_TIMEOUT_MS, '스냅샷 저장');

  // 지난 스냅샷들 중 이번 주 이전 것 중 가장 최근 것을 "전주"로 사용
  const historySnap = await withTimeout(db.ref('metrics/weekly').once('value'), FIREBASE_TIMEOUT_MS, '히스토리 읽기');
  const history = historySnap.val() || {};
  const prevKeys = Object.keys(history).filter(k => k !== weekKey).sort();
  const prevKey = prevKeys[prevKeys.length - 1];
  const prev = prevKey ? history[prevKey] : null;

  function diffLine(label, curr, prevVal) {
    if (prevVal === undefined || prevVal === null) return `${label}: ${curr} (전주 데이터 없음)`;
    const delta = curr - prevVal;
    const sign = delta > 0 ? '+' : '';
    return `${label}: ${curr} (전주 ${prevVal} 대비 ${sign}${delta})`;
  }

  const lines = [];
  lines.push('## 📈 주간 지표 리포트');
  lines.push('');
  lines.push(`- ${diffLine('전체 가입자', totalUsers, prev && prev.totalUsers)}`);
  lines.push(`- ${diffLine('이번 주 신규가입', newThisWeek, prev && prev.newThisWeek)}`);
  lines.push(`- ${diffLine('이번 주 활성유저(최근 접속)', activeThisWeek, prev && prev.activeThisWeek)}`);
  lines.push('');
  lines.push('### 구독 등급별 인원');
  Object.keys(tierCounts).forEach(tier => {
    const prevTierCount = prev && prev.tierCounts ? prev.tierCounts[tier] : null;
    lines.push(`- ${diffLine(tier, tierCounts[tier], prevTierCount)}`);
  });
  lines.push('');
  lines.push('### ✅ 필드 스키마 (2026-08-31 실제 확인 완료)');
  lines.push('- 가입일: uid(id) 파싱 (u_<가입시각ms>_<랜덤>)');
  lines.push('- 최근접속: lastSeen');
  lines.push('- 구독등급: 전용 필드 없음 (전원 free)');

  fs.writeFileSync('review-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().then(() => process.exit(0)).catch(err => {
  console.error('스크립트 오류:', err);
  process.exit(1);
});
