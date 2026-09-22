path = "ios/App/App.xcodeproj/project.pbxproj"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "CURRENT_PROJECT_VERSION = 8;"
new = "CURRENT_PROJECT_VERSION = 9;"

count = content.count(old)
if count != 2:
    raise SystemExit(f"[실패] CURRENT_PROJECT_VERSION = 8; 매치 {count}개 (2개여야 함)")

content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"[완료] CURRENT_PROJECT_VERSION 8 -> 9 로 변경함 ({count}곳)")
