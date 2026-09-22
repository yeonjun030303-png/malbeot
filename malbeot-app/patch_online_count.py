path = "server.js"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "app.get('/health', (req, res) => res.status(200).send('ok'));"
new = old + "\n\napp.get('/api/online-count', (req, res) => {\n  res.status(200).json({ count: Object.keys(userToSocket).length });\n});"

count = content.count(old)
if count == 0:
    print("[오류] 패턴을 찾을 수 없습니다.")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[완료] /api/online-count 엔드포인트 추가됨 ({count}곳)")
