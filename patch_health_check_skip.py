path = "scripts/health-check.js"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "async function main() {\n  let result = await checkHealth();"

new = """async function checkOnlineCount() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const base = TARGET_URL.replace(/\\/$/, '"'"''"'"');
    const res = await fetch(base + '"'"'/api/online-count'"'"', { signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data.count === '"'"'number'"'"' ? data.count : null;
  } catch (e) {
    return null;
  }
}

async function main() {
  const onlineCount = await checkOnlineCount();

  if (onlineCount !== null && onlineCount > 0) {
    console.log(`접속자 ${onlineCount}명 있음 - 가벼운 체크만 하고 종료`);
    process.exit(0);
  }

  console.log(onlineCount === 0 ? '"'"'접속자 0명 - 전체 점검 진행'"'"' : '"'"'접속자 수 확인 실패 - 안전하게 전체 점검 진행'"'"');

  let result = await checkHealth();"""

count = content.count(old)
if count == 0:
    print("[오류] 패턴을 찾을 수 없습니다.")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[완료] 접속자 있을 때 가벼운 체크로 전환되는 로직 추가됨 ({count}곳)")
