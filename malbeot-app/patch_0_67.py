with open("package.json", "r", encoding="utf-8") as f:
    pkg = f.read()
old_start = '"start": "node server.js"'
assert pkg.count(old_start) == 1, "package.json old_start 매칭 실패"
pkg = pkg.replace(old_start, '"start": "node --max-old-space-size=400 --expose-gc server.js"')
with open("package.json", "w", encoding="utf-8") as f:
    f.write(pkg)

with open("moderation.js", "r", encoding="utf-8") as f:
    mod = f.read()
old_threshold = "let nsfwQueue = Promise.resolve();\nconst MEMORY_GUARD_RSS_MB = 430; // Render 무료 플랜 512MB 중 이 이상이면 위험 수준으로 판단"
assert mod.count(old_threshold) == 1, "moderation.js old_threshold 매칭 실패"
new_threshold = "let nsfwQueue = Promise.resolve();\nconst MEMORY_GUARD_RSS_MB = 350; // 0-67: 512MB 컨테이너 기준 여유를 더 두기 위해 430->350으로 하향(급격한 스파이크 대비)"
mod = mod.replace(old_threshold, new_threshold)

old_guard = """  const task = nsfwQueue.then(async () => {
    const rss = currentRssMb();
    if (rss >= MEMORY_GUARD_RSS_MB) {
      console.warn(`NSFW 검사 스킵(메모리 보호): 현재 RSS ${rss.toFixed(0)}MB`);
      return { isNsfw: false, score: 0, error: `메모리 보호로 검사 스킵(RSS ${rss.toFixed(0)}MB, 통과 처리)` };
    }"""
assert mod.count(old_guard) == 1, "moderation.js old_guard 매칭 실패"
new_guard = """  const task = nsfwQueue.then(async () => {
    let rss = currentRssMb();
    if (rss >= MEMORY_GUARD_RSS_MB && global.gc) {
      global.gc();
      rss = currentRssMb();
    }
    if (rss >= MEMORY_GUARD_RSS_MB) {
      console.warn(`NSFW 검사 스킵(메모리 보호): 현재 RSS ${rss.toFixed(0)}MB`);
      return { isNsfw: false, score: 0, error: `메모리 보호로 검사 스킵(RSS ${rss.toFixed(0)}MB, 통과 처리)` };
    }"""
mod = mod.replace(old_guard, new_guard)
with open("moderation.js", "w", encoding="utf-8") as f:
    f.write(mod)

with open("server.js", "r", encoding="utf-8") as f:
    srv = f.read()
old_logger = """setInterval(() => {
  const m = process.memoryUsage();
  console.log(`📊 메모리 RSS ${(m.rss/1024/1024).toFixed(0)}MB / heapUsed ${(m.heapUsed/1024/1024).toFixed(0)}MB`);
}, 30000);"""
assert srv.count(old_logger) == 1, "server.js old_logger 매칭 실패"
new_logger = """setInterval(() => {
  const m = process.memoryUsage();
  const rssMb = m.rss / 1024 / 1024;
  console.log(`📊 메모리 RSS ${rssMb.toFixed(0)}MB / heapUsed ${(m.heapUsed/1024/1024).toFixed(0)}MB`);
  if (rssMb >= 380 && global.gc) {
    global.gc();
    console.log('🧹 0-67: RSS 임계치 근접, 강제 GC 실행');
  }
}, 30000);"""
srv = srv.replace(old_logger, new_logger)
with open("server.js", "w", encoding="utf-8") as f:
    f.write(srv)

print("0-67 패치 완료")
