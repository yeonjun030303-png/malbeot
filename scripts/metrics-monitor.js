// 지표 모니터링 요원 봇
// - Firebase에서 DAU(최근 접속), 신규가입/탈퇴, 구독(골드/플래티넘) 현황을 집계
// - 매주 실행분을 metrics/weekly/<날짜> 에 스냅샷으로 저장해두고, 전주 스냅샷과 비교해 급변 항목 하이라이트
// - 필드명(예: createdAt, lastActiveAt, subscriptionTier)은 실제 스키마 확인 전 추정치이므로,
//   최초 실행 결과의 "감지된 필드" 항목을 꼭 확인하고 다르면 알려주세요 - 바로 수정해드립니다.

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
  return user.createdAt || user.joinedAt || user.signupAt || null;
}
function pickLastActive(user) {
  return user.lastActiveAt || user.lastSeenAt || user.lastLoginAt || null;
}
function pickTier(user) {
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
  lines.push('### ⚠️ 필드 감지 참고 (스키마 추정치 - 실제와 다르면 알려주세요)');
  lines.push('- 가입일 필드 후보: createdAt / joinedAt / signupAt');
  lines.push('- 최근접속 필드 후보: lastActiveAt / lastSeenAt / lastLoginAt');
  lines.push('- 구독등급 필드 후보: subscriptionTier / subscription.tier / plan');

  fs.writeFileSync('review-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().then(() => process.exit(0)).catch(err => {
  console.error('스크립트 오류:', err);
  process.exit(1);
});
