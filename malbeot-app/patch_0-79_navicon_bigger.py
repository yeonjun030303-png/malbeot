path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = ".nav-icon-svg{width:22px;height:22px;display:block;}"
new = ".nav-icon-svg{width:27px;height:27px;display:block;}"

count = content.count(old)
if count != 1:
    raise SystemExit(f"[실패] .nav-icon-svg CSS 매치 {count}개 (1개여야 함)")
content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[완료] 네비 아이콘 크기 22px -> 27px로 키움")
