path = "public\index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = ".app-header{height:56px;background:#fff;border-bottom:1px solid var(--border-color);display:flex;align-items:center;justify-content:space-between;padding:0 16px;z-index:10;flex-shrink:0;}"
new = ".app-header{min-height:56px;background:#fff;border-bottom:1px solid var(--border-color);display:flex;align-items:center;justify-content:space-between;padding:env(safe-area-inset-top) 16px 0 16px;z-index:10;flex-shrink:0;}"

count = content.count(old)
if count == 0:
    print("[오류] 패턴을 찾을 수 없습니다.")
elif count > 1:
    print(f"[경고] {count}번 발견됨(1번이어야 함), 건너뜀")
else:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[완료] .app-header 안전영역 패딩 추가됨")
