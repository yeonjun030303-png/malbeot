path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = ".app-container{width:100%;max-width:480px;height:100vh;height:100dvh;max-height:900px;background:#fff;display:flex;flex-direction:column;position:relative;box-shadow:var(--shadow-lg);overflow:hidden;}"
new = ".app-container{width:100%;max-width:480px;height:100vh;height:100dvh;max-height:900px;background:#fff;display:flex;flex-direction:column;position:relative;box-shadow:var(--shadow-lg);overflow:hidden;align-self:flex-start;}"

count = content.count(old)
if count != 1:
    raise SystemExit(f"[실패] .app-container CSS 매치 {count}개 (1개여야 함)")
content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[완료] .app-container에 align-self:flex-start 추가함 - 키보드로 높이 줄어들 때 더 이상 세로 중앙정렬되지 않고 항상 화면 상단에 고정됨")
