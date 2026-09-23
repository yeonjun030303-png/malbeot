# -*- coding: utf-8 -*-
# 0-87: Info.plist(카메라/사진첩 권한) 반영을 위한 다음 빌드 준비
# - 빌드번호 10 -> 11
# - 마케팅 버전 1.0 -> 1.1 (App Store Connect에 이미 만들어둔 1.1 버전과 맞춤)

path = "ios/App/App.xcodeproj/project.pbxproj"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

build_before = content.count("CURRENT_PROJECT_VERSION = 10;")
content = content.replace("CURRENT_PROJECT_VERSION = 10;", "CURRENT_PROJECT_VERSION = 11;")

version_before = content.count("MARKETING_VERSION = 1.0;")
content = content.replace("MARKETING_VERSION = 1.0;", "MARKETING_VERSION = 1.1;")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"빌드번호 10 -> 11 ({build_before}곳 교체)")
print(f"마케팅버전 1.0 -> 1.1 ({version_before}곳 교체)")