import re

path = "malbeot-app/server.js"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

anchor = """app.get('/api/push/vapid-public-key', (req, res) => {
  res.json({ publicKey: VAPID_PUBLIC_KEY });
});"""

test_route = """app.get('/api/push/vapid-public-key', (req, res) => {
  res.json({ publicKey: VAPID_PUBLIC_KEY });
});

// [임시 테스트용] 웹푸시 동작 확인 후 삭제할 것
app.get('/api/push/test/:userId', (req, res) => {
  sendWebPush(req.params.userId, { title: '테스트 알림', body: '푸시 정상 작동 확인용', type: 'test' });
  res.json({ ok: true });
});"""

if anchor not in content:
    print("앵커 텍스트를 못 찾았습니다. 파일이 변경됐을 수 있습니다.")
else:
    content = content.replace(anchor, test_route, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("테스트 라우트 삽입 완료.")