# -*- coding: utf-8 -*-
import subprocess, sys

path = "malbeot-app/public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) openProfileDetailScreen: 유저 정보 + 최신 채팅목록을 함께 불러온 뒤에 프로필을 렌더링(버튼 라벨 결정을 위해)
old_open = """function openProfileDetailScreen(userId){
  currentProfileUserId = userId; profilePhotoIndex = 0;
  socket.emit('profile:record_visit', {targetUserId: userId});
  socket.emit('users:get_one', {userId}, (res)=>{
    const user = res && res.user;
    if (!user) return;
    currentProfileUserCache = user;
    renderProfileDetail(user);
    openFullScreen('profileDetailScreen');
  });
}"""
new_open = """function openProfileDetailScreen(userId){
  currentProfileUserId = userId; profilePhotoIndex = 0;
  socket.emit('profile:record_visit', {targetUserId: userId});
  let fetchedUser = null, userLoaded = false, roomsLoaded = false;
  function tryOpenProfile(){
    if (!userLoaded || !roomsLoaded || !fetchedUser) return;
    currentProfileUserCache = fetchedUser;
    renderProfileDetail(fetchedUser);
    openFullScreen('profileDetailScreen');
  }
  socket.emit('users:get_one', {userId}, (res)=>{
    fetchedUser = res && res.user; userLoaded = true; tryOpenProfile();
  });
  // 메시지 버튼을 "메시지 보내기"(신규)/"채팅창으로 이동하기"(기존 채팅방 있음)로 정확히 나누기 위해 최신 채팅목록을 함께 불러옴
  socket.emit('chat:get_list', (res)=>{
    if (res && res.success) currentChatRooms = res.rooms;
    roomsLoaded = true; tryOpenProfile();
  });
}"""
if old_open not in content:
    print("❌ openProfileDetailScreen 함수를 찾을 수 없습니다."); sys.exit(1)
content = content.replace(old_open, new_open, 1)

# 2) 메시지 버튼: 이미 채팅방이 있으면 "채팅창으로 이동하기"로 라벨/아이콘 자체를 바꿔서 카톡처럼 명확히 구분
old_btn = '${isMe?\'\':\'<button class="btn btn-primary btn-block" onclick="handleSendMessageClick()"><i class="fa-solid fa-comments"></i> 메시지 보내기</button>\'}'
new_btn = """${isMe?'':(function(){
        const existingRoom = (currentChatRooms||[]).find(r=>r.targetUser && r.targetUser.id===user.id);
        return existingRoom
          ? '<button class="btn btn-primary btn-block" onclick="handleSendMessageClick()"><i class="fa-solid fa-comment-dots"></i> 채팅창으로 이동하기</button>'
          : '<button class="btn btn-primary btn-block" onclick="handleSendMessageClick()"><i class="fa-solid fa-comments"></i> 메시지 보내기</button>';
      })()}"""
if old_btn not in content:
    print("❌ 메시지 보내기 버튼 코드를 찾을 수 없습니다."); sys.exit(1)
content = content.replace(old_btn, new_btn, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 0-50 패치 적용 완료: 이미 채팅중인 상대는 버튼이 '채팅창으로 이동하기'로 바뀌어 즉시 이동, 신규 상대는 '메시지 보내기'(쌀 50개 안내) 그대로 유지")

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "0-50: 프로필 메시지 버튼 - 채팅방 존재 여부로 라벨 자체를 분리(메시지 보내기 / 채팅창으로 이동하기)"], check=True)
print("✅ 커밋 완료")