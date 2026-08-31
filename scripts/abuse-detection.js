// 이상행동탐지 담당 봇 (감찰팀) - 매일 17:00
// Firebase 'messages' 노드에서 짧은 시간 내 동일 문구를 반복 전송하는 스팸성 패턴을 탐지
// 필드명 추정: senderId(또는 userId), text(또는 content), timestamp(또는 createdAt)

const { initializeApp, cert } = require('firebase-admin/app');
const { getDatabase } = require('firebase-admin/database');
const fs = require('fs');

const FIREBASE_TIMEOUT_MS = 60000;
const DAY_MS = 24 * 60 * 60 * 1000;
const REPEAT_THRESHOLD = 5; // 하루 동안 동일 문구를 이 횟수 이상 보내면 의심 처리

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} - ${ms / 1000}초 응답 없음(타임아웃)`)), ms))
  ]);
}

function pickSender(m) { return m.senderId || m.userId || m.from || 'unknown'; }
function pickText(m) { return (m.text || m.content || m.message || '').toString(); }
function pickTime(m) { return m.timestamp || m.createdAt || m.date || null; }

async function main() {
  const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  initializeApp({ credential: cert(serviceAccount), databaseURL: process.env.FIREBASE_DB_URL });
  const db = getDatabase();

  const snap = await withTimeout(db.ref('messages').once('value'), FIREBASE_TIMEOUT_MS, 'messages 읽기');
  const obj = snap.val() || {};

  // messages가 채팅방별로 중첩된 구조일 수도 있어 1단계만 우선 평탄화 시도
  let flat = [];
  Object.keys(obj).forEach(k1 => {
    const v1 = obj[k1];
    if (v1 && typeof v1 === 'object' && (v1.text || v1.content || v1.message)) {
      flat.push({ id: k1, ...v1 });
    } else if (v1 && typeof v1 === 'object') {
      Object.keys(v1).forEach(k2 => flat.push({ id: `${k1}/${k2}`, ...v1[k2] }));
    }
  });

  const now = Date.now();
  const recent = flat.filter(m => { const t = pickTime(m); return t && (now - Number(t)) <= DAY_MS; });

  const counter = {}; // key: sender||text
  recent.forEach(m => {
    const key = `${pickSender(m)}||${pickText(m)}`;
    counter[key] = (counter[key] || 0) + 1;
  });

  const suspicious = Object.keys(counter).filter(k => counter[k] >= REPEAT_THRESHOLD);

  if (suspicious.length === 0) {
    console.log('이상행동 없음 - 리포트 생략');
    return;
  }

  const lines = [];
  lines.push('## 🚨 이상행동탐지 (최근 24시간)');
  lines.push('');
  lines.push(`- 반복 전송 의심 패턴: ${suspicious.length}건 (동일 발신자+동일 문구가 ${REPEAT_THRESHOLD}회 이상)`);
  lines.push('');
  suspicious.forEach(key => {
    const [sender, text] = key.split('||');
    lines.push(`- 발신자 ${sender}: "${text.slice(0, 50)}" 를 ${counter[key]}회 반복 전송`);
  });
  lines.push('');
  lines.push('### 필드 감지 참고 (실제 필드명과 다르면 스크립트 수정 필요)');
  lines.push('- 메시지 노드: messages (채팅방별 중첩 구조 1단계까지 자동 평탄화 시도함)');
  lines.push('- 발신자 필드 추정: senderId / userId / from');
  lines.push('- 내용 필드 추정: text / content / message');
  lines.push('- 시각 필드 추정: timestamp / createdAt / date');

  fs.writeFileSync('abuse-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main().catch(err => {
  console.error('이상행동탐지 실패:', err);
  process.exit(1);
});
