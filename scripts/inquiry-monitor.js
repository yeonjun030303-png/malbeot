// 고객문의모니터링 봇 (운영팀 신규)
// - Firebase 'inquiries' 노드에서 미답변 고객문의를 조회해 목록 리포트 생성
// - 필드명은 추정치이므로 첫 실행 리포트의 "필드 감지 참고" 항목으로 실제 필드명과 맞는지 확인 필요
// - 미답변 문의가 없으면 파일을 만들지 않고 조용히 종료(다른 봇들과 동일한 설계)

const { initializeApp, cert } = require('firebase-admin/app');
const { getDatabase } = require('firebase-admin/database');
const fs = require('fs');

const FIREBASE_TIMEOUT_MS = 60000; // Firebase 응답이 60초 이상 없으면 타임아웃 처리(6시간 강제종료 방지)

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} - ${ms / 1000}초 응답 없음(타임아웃)`)), ms))
  ]);
}

function isPending(inq) {
  if (typeof inq.answered === 'boolean') return inq.answered === false;
  if (inq.status) return inq.status === 'pending' || inq.status === '대기';
  return true; // 상태 필드를 못 찾으면 일단 미답변으로 간주(누락 방지 우선)
}

function pickCreatedAt(inq) {
  return inq.createdAt || inq.timestamp || inq.date || null;
}

async function main() {
  const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  initializeApp({
    credential: cert(serviceAccount),
    databaseURL: process.env.FIREBASE_DB_URL
  });
  const db = getDatabase();

  const snap = await withTimeout(db.ref('inquiries').once('value'), FIREBASE_TIMEOUT_MS, 'inquiries 읽기');
  const obj = snap.val() || {};
  const list = Object.keys(obj).map(id => ({ id, ...obj[id] }));
  const pending = list.filter(isPending);

  if (pending.length === 0) {
    console.log('미답변 문의 없음 - 리포트 생략');
    return;
  }

  const sorted = pending
    .sort((a, b) => (Number(pickCreatedAt(b)) || 0) - (Number(pickCreatedAt(a)) || 0))
    .slice(0, 30);

  const lines = [];
  lines.push('## 📮 고객문의 모니터링');
  lines.push('');
  lines.push(`- 전체 문의: ${list.length}건`);
  lines.push(`- 미답변 문의: ${pending.length}건 (최근 30건만 표시)`);
  lines.push('');
  lines.push('### 미답변 목록');
  sorted.forEach(inq => {
    const created = pickCreatedAt(inq);
    const date = created ? new Date(Number(created)).toLocaleString('ko-KR') : '날짜 미상';
    const content = (inq.content || inq.message || inq.text || '(내용 없음)').toString().slice(0, 100);
    lines.push(`- [${date}] ${content}`);
  });
  lines.push('');
  lines.push('### ⚠️ 필드 감지 참고 (실제 필드명과 다르면 스크립트 수정 필요)');
  lines.push('- 문의함 노드: inquiries');
  lines.push('- 답변여부 필드 추정: answered / status');
  lines.push('- 작성시각 필드 추정: createdAt / timestamp / date');
  lines.push('- 내용 필드 추정: content / message / text');

  fs.writeFileSync('inquiry-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().catch(err => {
  console.error('고객문의모니터링 실패:', err);
  process.exit(1);
});
