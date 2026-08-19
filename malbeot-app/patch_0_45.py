# -*- coding: utf-8 -*-
import re, subprocess, sys

path = "malbeot-app/public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) 프로필 화면의 "메시지 보내기" 버튼 onclick 교체
old_btn = '${isMe?\'\':\'<button class="btn btn-primary btn-block" onclick="openMessageComposeScreen()"><i class="fa-solid fa-comments"></i> 메시지 보내기</button>\'}'
new_btn = '${isMe?\'\':\'<button class="btn btn-primary btn-block" onclick="handleSendMessageClick()"><i class="fa-solid fa-comments"></i> 메시지 보내기</button>\'}'
if old_btn not in content:
    print("❌ 메시지 보내기 버튼 코드를 찾을 수 없습니다. 수동 확인이 필요합니다.")
    sys.exit(1)
content = content.replace(old_btn, new_btn, 1)

# 2) openMessageComposeScreen 함수 바로 위에 handleSendMessageClick 함수 삽입
anchor = "/* ===================== 메시지 작성 화면 ===================== */\nfunction openMessageComposeScreen(){"
if anchor not in content:
    print("❌ openMessageComposeScreen 함수 위치를 찾을 수 없습니다. 수동 확인이 필요합니다.")
    sys.exit(1)

new_func = """/* ===================== 메시지 작성 화면 ===================== */
// 이미 채팅방이 있는 상대면 작성화면을 건너뛰고 바로 채팅창으로 이동, 없으면 기존처럼 작성화면(쌀 50개 안내) 표시
function handleSendMessageClick(){
  const targetId = currentProfileUserId; if (!targetId) return;
  socket.emit('chat:get_list', (res)=>{
    if (res && res.success){
      currentChatRooms = res.rooms;
      const existing = currentChatRooms.find(r=>r.targetUser && r.targetUser.id===targetId);
      if (existing){
        closeProfileDetailScreen();
        switchTab('tab-chat');
        openChatRoomById(existing.roomId);
        return;
      }
    }
    openMessageComposeScreen();
  });
}
function openMessageComposeScreen(){"""

content = content.replace(anchor, new_func, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 0-45 패치 적용 완료: handleSendMessageClick 함수 추가 + 메시지 보내기 버튼 연결")

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "0-45: 이미 채팅중인 사람에게 메시지 보내면 즉시 채팅창으로 이동"], check=True)
print("✅ 커밋 완료")