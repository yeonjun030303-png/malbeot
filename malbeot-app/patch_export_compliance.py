path = "ios\App\App\Info.plist"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "</dict>\n</plist>"
new = "\t<key>ITSAppUsesNonExemptEncryption</key>\n\t<false/>\n</dict>\n</plist>"

count = content.count(old)
if count == 0:
    print("[오류] 패턴을 찾을 수 없습니다.")
elif count > 1:
    print(f"[경고] {count}번 발견됨(1번이어야 함), 건너뜀")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[완료] ITSAppUsesNonExemptEncryption = false 추가됨")
