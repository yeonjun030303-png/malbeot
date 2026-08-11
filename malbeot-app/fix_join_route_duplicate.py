#!/usr/bin/env python3
# 초대링크 라우트 중복/충돌 버그 수정
# 문제: server.js에 app.get('/join/:code', ...)가 두 번 등록되어 있었음
#   - 1번째(먼저 등록됨, 실제 동작): '/?joinCode=코드' 로 redirect
#   - 2번째(죽은 코드, 실행 안 됨): index.html을 경로 그대로 sendFile
# 클라이언트(public/index.html)는 location.pathname에서 '/join/코드' 패턴을 직접 찾기 때문에,
# redirect로 경로가 '/'로 바뀌어버리면 클라이언트가 초대코드를 절대 못 읽음 -> 초대링크 자동입장이 항상 실패하는 상태였음.
# 해결: redirect 라우트를 제거하고, 경로를 그대로 유지하며 index.html을 내려주는 라우트 하나만 남김.
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_join_route_duplicate.py

import sys

def patch(path, replacements):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        count = content.count(old)
        if count != 1:
            print(f"[실패] {path}: 패턴이 {count}번 발견됨 (1번이어야 함) -> {old[:60]!r}")
            sys.exit(1)
        content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[성공] {path} 패치 완료")

server_replacements = [
(
"""// 단체채팅방 초대링크(실제 URL) 진입점: /join/코드 로 접속하면 프론트가 그 코드를 읽어 자동 입장 처리함
// (지금은 웹앱뿐이라 그냥 앱 페이지로 리다이렉트하지만, 나중에 네이티브 앱이 생기면
//  여기서 미설치 기기를 감지해 스토어로 보내는 분기를 추가할 것)
app.get('/join/:code', (req, res) => {
  res.redirect('/?joinCode=' + encodeURIComponent(req.params.code));
});

// 단체채팅방 초대링크 (카카오 오픈채팅처럼 실제 URL로 들어오면 앱 내 페이지로 바로 진입)
// 지금은 웹뷰만 있어서 index.html을 그대로 내려주고, 클라이언트가 경로의 코드를 읽어 로그인 후 자동 입장시킴.
// TODO: 나중에 네이티브 앱이 생기면 여기서 User-Agent를 보고 앱 미설치 기기는 스토어로 리다이렉트하도록 확장할 것.
app.get('/join/:code', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});""",
"""// 단체채팅방 초대링크 (카카오 오픈채팅처럼 실제 URL로 들어오면 앱 내 페이지로 바로 진입)
// 지금은 웹뷰만 있어서 index.html을 그대로 내려주고, 클라이언트가 경로(/join/코드)를 그대로 읽어 로그인 후 자동 입장시킴.
// 주의: 절대 여기서 redirect하지 말 것 - 클라이언트가 location.pathname에서 '/join/코드' 패턴을 직접 파싱하기 때문에,
//       경로가 바뀌면(redirect로 '/?joinCode=...' 등으로) 클라이언트가 코드를 못 읽어 자동입장이 깨짐.
// TODO: 나중에 네이티브 앱이 생기면 여기서 User-Agent를 보고 앱 미설치 기기는 스토어로 리다이렉트하도록 확장할 것.
app.get('/join/:code', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});"""
),
]

patch('server.js', server_replacements)
print("\n패치 완료. 다음 순서로 진행하세요:")
print("1) node -c server.js")
print("2) git add -A && git commit -m \"0-7: 초대링크 라우트 중복 버그 수정 - redirect로 인해 자동입장이 항상 실패하던 문제\"")
print("3) (모아뒀다가 원하실 때) git push")
