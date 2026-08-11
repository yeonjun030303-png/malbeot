#!/usr/bin/env python3
# 채팅창 상단 이름/프로필사진 클릭 시 프로필이 안 열리던 버그 수정
# 원인: openProfileDetailScreen()이 users:get_list(나이19~99 등 필터 걸린 전체목록)에서 대상을 찾는 방식이라
#      상대방이 그 필터 조건 밖에 있으면(나이 미설정 등) 조용히 실패해서 채팅만 닫히고 아무 일도 안 일어남(뒤로가기처럼 보임)
# 해결: 필터 없이 ID 하나로 정확히 조회하는 전용 이벤트(users:get_one)를 서버에 추가하고 클라이언트가 이걸 쓰도록 변경
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_chat_header_profile.py

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
"""  socket.on('users:get_list', async (filters, cb) => {""",
"""  // 단일 유저 프로필 조회 (채팅 상단 헤더 등에서 목록 필터에 상관없이 특정 유저 1명을 정확히 조회할 때 사용)
  socket.on('users:get_one', async (data, cb) => {
    try {
      const user = await getUser(data.userId);
      if (!user) return cb({ success: false });
      const result = user.nicknameFiltered ? { ...user, nickname: "삭제된 닉네임입니다" } : user;
      cb({ success: true, user: result });
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('users:get_list', async (filters, cb) => {"""
),
]

html_replacements = [
(
"""function openProfileDetailScreen(userId){
  currentProfileUserId = userId; profilePhotoIndex = 0;
  socket.emit('users:get_list', {region:'전체', gender:'전체', ageMin:19, ageMax:99}, (res)=>{
    const user = (res.users||[]).find(u=>u.id===userId);
    if (!user) return;
    currentProfileUserCache = user;
    renderProfileDetail(user);
    openFullScreen('profileDetailScreen');
  });
}
function refreshOpenProfileIfNeeded(){
  if (!document.getElementById('profileDetailScreen').classList.contains('active') || !currentProfileUserId) return;
  socket.emit('users:get_list', {region:'전체', gender:'전체', ageMin:19, ageMax:99}, (res)=>{
    const user = (res.users||[]).find(u=>u.id===currentProfileUserId);
    if (user){ currentProfileUserCache = user; renderProfileDetail(user); }
  });
}""",
"""function openProfileDetailScreen(userId){
  currentProfileUserId = userId; profilePhotoIndex = 0;
  socket.emit('users:get_one', {userId}, (res)=>{
    const user = res && res.user;
    if (!user) return;
    currentProfileUserCache = user;
    renderProfileDetail(user);
    openFullScreen('profileDetailScreen');
  });
}
function refreshOpenProfileIfNeeded(){
  if (!document.getElementById('profileDetailScreen').classList.contains('active') || !currentProfileUserId) return;
  socket.emit('users:get_one', {userId:currentProfileUserId}, (res)=>{
    const user = res && res.user;
    if (user){ currentProfileUserCache = user; renderProfileDetail(user); }
  });
}"""
),
]

patch('server.js', server_replacements)
patch('public/index.html', html_replacements)
print("\n패치 완료. 다음 순서로 진행하세요:")
print("1) node -c server.js")
print("2) git add -A && git commit -m \"채팅창 상단 프로필 클릭 버그 수정: 유저 목록 필터 대신 전용 단일조회 이벤트 사용\"")
print("3) git push")
