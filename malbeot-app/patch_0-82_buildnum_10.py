import re

path = r"ios/App/App.xcodeproj/project.pbxproj"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

before = content.count("CURRENT_PROJECT_VERSION = 9;")
if before == 0:
    print("[스킵] CURRENT_PROJECT_VERSION = 9; 를 찾지 못했습니다. 이미 변경됐거나 값이 다를 수 있습니다.")
else:
    content = content.replace("CURRENT_PROJECT_VERSION = 9;", "CURRENT_PROJECT_VERSION = 10;")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[완료] CURRENT_PROJECT_VERSION 9 -> 10 으로 변경 ({before}곳 교체)")