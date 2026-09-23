path = "ios/App/App/Info.plist"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

if "GADApplicationIdentifier" in content:
    raise SystemExit("[실패] GADApplicationIdentifier가 이미 있음 - 중복 추가 방지를 위해 중단")

old = "\t<key>ITSAppUsesNonExemptEncryption</key>\n\t<false/>\n</dict>\n</plist>"
new = (
    "\t<key>ITSAppUsesNonExemptEncryption</key>\n\t<false/>\n"
    "\t<key>GADApplicationIdentifier</key>\n\t<string>ca-app-pub-1897610037138449~2107611900</string>\n"
    "\t<key>NSUserTrackingUsageDescription</key>\n\t<string>맞춤형 광고를 제공하기 위해 사용됩니다.</string>\n"
    "</dict>\n</plist>"
)

count = content.count(old)
if count != 1:
    raise SystemExit(f"[실패] 파일 끝부분 매치 {count}개 (1개여야 함) - 인코딩(탭/스페이스) 차이일 수 있음")
content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[완료] Info.plist에 GADApplicationIdentifier + NSUserTrackingUsageDescription 추가함")
