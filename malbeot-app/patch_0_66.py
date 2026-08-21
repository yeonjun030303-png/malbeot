import re, sys

path = "server.js"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) 파일 상단에 크래시 방지/로깅 핸들러 + 메모리 로거 삽입
anchor1 = "const webpush = require('web-push');\n"
assert content.count(anchor1) == 1, "anchor1 매칭 실패"

crash_guard = anchor1 + """
// ===== 0-66: 502 크래시 루프 원인 파악용 안전망 =====
// Node 20은 처리되지 않은 Promise rejection(unhandledRejection)이 발생하면 기본적으로
// 프로세스 전체를 종료시킴 -> 이 서버는 지금까지 이걸 잡아주는 코드가 없어서, 어딘가 하나의
// 비동기 라우트에서 try/catch 없이 에러가 나면 그 요청 하나 때문에 서버 전체가 죽고
// Render가 재시작하는 동안 502가 뜨는 크래시 루프가 발생할 수 있었음.
// 아래 핸들러는 (1) 서버가 즉시 죽지 않게 막고 (2) 정확한 원인을 Render 로그에 남긴다.
process.on('unhandledRejection', (reason) => {
  console.error('🔴 [unhandledRejection] 처리되지 않은 Promise 에러(서버는 계속 실행됨):', reason);
});
process.on('uncaughtException', (err) => {
  console.error('🔴 [uncaughtException] 처리되지 않은 예외(서버는 계속 실행됨):', err);
});

// 0-66: 메모리 사용량을 30초마다 로그로 남겨서, 502/재시작 직전 RSS가 얼마였는지
// Render 로그에서 추적 가능하게 함(OOM으로 죽는 것인지 판단하는 용도)
setInterval(() => {
  const m = process.memoryUsage();
  console.log(`📊 메모리 RSS ${(m.rss/1024/1024).toFixed(0)}MB / heapUsed ${(m.heapUsed/1024/1024).toFixed(0)}MB`);
}, 30000);
"""
content = content.replace(anchor1, crash_guard, 1)

# 2) 서버 시작시 즉시 NSFW 모델 예열하던 부분을, 5초 지연 + 실패해도 안전하게 처리
old_warmup = """loadNsfwModel()
  .then(() => console.log('✅ NSFW 이미지 검사 모델 예열 완료'))
  .catch(err => console.error('⚠️ NSFW 모델 예열 실패(사용자 요청 시점에 재시도됨):', err.message));"""

new_warmup = """// 0-66: 부팅 직후(다른 초기화 작업과 메모리 스파이크가 겹치는 시점)를 피하기 위해
// 5초 지연 후 예열하고, 실패해도 서버 자체는 절대 죽지 않게 처리
setTimeout(() => {
  loadNsfwModel()
    .then(() => console.log('✅ NSFW 이미지 검사 모델 예열 완료'))
    .catch(err => console.error('⚠️ NSFW 모델 예열 실패(사용자 요청 시점에 재시도됨):', err.message));
}, 5000);"""

assert content.count(old_warmup) == 1, "old_warmup 매칭 실패"
content = content.replace(old_warmup, new_warmup, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("패치 완료")
