// 예산집행 리포트 담당 봇 (기획예산팀) - 매월 1일 17:00
// Firebase 'budgetEntries' 노드에 관리자가 수기로 기록해둔 지출/매출 항목을 월간 집계
// 해당 노드가 비어있거나 없으면 "아직 기록된 예산 데이터 없음" 안내와 함께 입력 가이드만 남김
// 필드명 추정: amount, category, type(income/expense), date

const { initializeApp, cert } = require('firebase-admin/app');
const { getDatabase } = require('firebase-admin/database');
const fs = require('fs');

const FIREBASE_TIMEOUT_MS = 60000;

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} - ${ms / 1000}초 응답 없음(타임아웃)`)), ms))
  ]);
}

function monthKeyOf(ts) {
  return new Date(Number(ts)).toISOString().slice(0, 7); // YYYY-MM
}

async function main() {
  const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  initializeApp({ credential: cert(serviceAccount), databaseURL: process.env.FIREBASE_DB_URL });
  const db = getDatabase();

  const snap = await withTimeout(db.ref('budgetEntries').once('value'), FIREBASE_TIMEOUT_MS, 'budgetEntries 읽기');
  const obj = snap.val() || {};
  const list = Object.keys(obj).map(id => ({ id, ...obj[id] }));

  const lines = [];
  lines.push('## 🧾 예산집행 리포트 (지난달)');
  lines.push('');

  if (list.length === 0) {
    lines.push('아직 budgetEntries 노드에 기록된 예산 데이터가 없습니다.');
    lines.push('');
    lines.push('### 입력 가이드 (관리자용)');
    lines.push('Firebase Realtime Database의 budgetEntries 노드 밑에 아래 형식으로 항목을 추가하면 다음 달부터 자동 집계됩니다.');
    lines.push('- amount: 금액(숫자)');
    lines.push('- type: "income" 또는 "expense"');
    lines.push('- category: 항목명(예: "서버비", "구독매출")');
    lines.push('- date: 타임스탬프(ms)');
    fs.writeFileSync('budget-result.md', lines.join('\n'));
    console.log(lines.join('\n'));
    return;
  }

  const now = new Date();
  const lastMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const targetKey = lastMonthDate.toISOString().slice(0, 7);

  const monthly = list.filter(e => e.date && monthKeyOf(e.date) === targetKey);

  if (monthly.length === 0) {
    lines.push(`${targetKey}에 기록된 항목이 없습니다.`);
    fs.writeFileSync('budget-result.md', lines.join('\n'));
    console.log(lines.join('\n'));
    return;
  }

  const income = monthly.filter(e => e.type === 'income').reduce((s, e) => s + Number(e.amount || 0), 0);
  const expense = monthly.filter(e => e.type === 'expense').reduce((s, e) => s + Number(e.amount || 0), 0);

  lines.push(`- 집계 대상 월: ${targetKey}`);
  lines.push(`- 총 수입: ${income.toLocaleString()}원`);
  lines.push(`- 총 지출: ${expense.toLocaleString()}원`);
  lines.push(`- 순이익: ${(income - expense).toLocaleString()}원`);
  lines.push('');
  lines.push('### 지출 항목별 내역');
  const byCategory = {};
  monthly.filter(e => e.type === 'expense').forEach(e => {
    const cat = e.category || '미분류';
    byCategory[cat] = (byCategory[cat] || 0) + Number(e.amount || 0);
  });
  Object.keys(byCategory).forEach(cat => {
    lines.push(`- ${cat}: ${byCategory[cat].toLocaleString()}원`);
  });

  fs.writeFileSync('budget-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().then(() => process.exit(0)).catch(err => {
  console.error('예산집행리포트 실패:', err);
  process.exit(1);
});
