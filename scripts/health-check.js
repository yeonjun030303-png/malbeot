// 헬스체크/장애감시 봇
// - Render 서비스(/) 핑 체크, 응답지연/5xx/타임아웃 감지시 즉시 이메일+이슈로 긴급 알림
// - 5~10분 간격 실행 전제(워크플로우 cron)이므로 상태 저장 없이 매 실행 독립 판정(장애 지속시 반복 알림됨 - 의도적)

const fs = require('fs');

const TARGET_URL = process.env.HEALTH_CHECK_URL || 'https://malbeot-1.onrender.com/';
const TIMEOUT_MS = 15000; // Render 무료플랜 콜드스타트 감안, 15초까지는 정상 허용
const SLOW_THRESHOLD_MS = 8000; // 8초 넘으면 "느림" 경고(장애까지는 아님)

async function checkHealth() {
  const start = Date.now();
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    const res = await fetch(TARGET_URL, { signal: controller.signal });
    clearTimeout(timer);
    const elapsed = Date.now() - start;

    if (res.status >= 500) {
      return { ok: false, reason: `서버 오류 (HTTP ${res.status})`, elapsed };
    }
    if (res.status >= 400) {
      return { ok: false, reason: `클라이언트 오류 (HTTP ${res.status})`, elapsed };
    }
    if (elapsed > SLOW_THRESHOLD_MS) {
      return { ok: false, reason: `응답 지연 (${(elapsed / 1000).toFixed(1)}초, 임계값 ${(SLOW_THRESHOLD_MS / 1000)}초)`, elapsed };
    }
    return { ok: true, elapsed };
  } catch (e) {
    const elapsed = Date.now() - start;
    if (e.name === 'AbortError') {
      return { ok: false, reason: `타임아웃 (${(TIMEOUT_MS / 1000)}초 초과 무응답)`, elapsed };
    }
    return { ok: false, reason: `연결 실패 (${e.message})`, elapsed };
  }
}

async function main() {
  const result = await checkHealth();

  if (result.ok) {
    console.log(`정상 - 응답시간 ${(result.elapsed / 1000).toFixed(1)}초`);
    process.exit(0);
  }

  const lines = [];
  lines.push('## 🚨 말벗 서비스 장애 감지');
  lines.push('');
  lines.push(`- 대상: ${TARGET_URL}`);
  lines.push(`- 사유: ${result.reason}`);
  lines.push(`- 소요시간: ${(result.elapsed / 1000).toFixed(1)}초`);
  lines.push(`- 감지시각(UTC): ${new Date().toISOString()}`);
  lines.push('');
  lines.push('Render 대시보드(Logs/Events)에서 재시작 여부, 메모리 사용량을 바로 확인해주세요.');

  fs.writeFileSync('review-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
  process.exit(0); // 워크플로우 후속 단계(이슈/이메일)가 계속 진행되도록 0으로 종료
}

main();
