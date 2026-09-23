# -*- coding: utf-8 -*-
# 0-86 긴급수정: patch_0-85.py가 실수로 두 번 실행되면서 생긴 중복 코드 제거
# (특히 index.html의 "let currentChatRoomIndex" 중복 선언은 SyntaxError를 일으켜
#  화면 전체 스크립트가 아예 안 돌아가는 심각한 문제라 최우선으로 고쳐야 함)

def patch(path, replacements, encoding="utf-8"):
    with open(path, "r", encoding=encoding) as f:
        content = f.read()
    for label, old, new in replacements:
        cnt = content.count(old)
        if cnt != 1:
            print(f"[건너뜀/확인필요] {path} :: {label} (매칭 {cnt}개, 1개여야 정상)")
            continue
        content = content.replace(old, new)
        print(f"[적용됨] {path} :: {label}")
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


# 1. index.html: let 중복선언(SyntaxError 원인, 최우선) 제거
patch("public/index.html", [
    ("currentChatRoomIndex 중복 선언 제거 (SyntaxError 원인)",
     "let currentChatRoomIndex = []; // 0-85: 프로필 등에서 메시지유무만 가볍게 확인할 때 쓰는 인덱스(전체 메시지 미포함)\nlet currentChatRoomIndex = []; // 0-85: 프로필 등에서 메시지유무만 가볍게 확인할 때 쓰는 인덱스(전체 메시지 미포함)",
     "let currentChatRoomIndex = []; // 0-85: 프로필 등에서 메시지유무만 가볍게 확인할 때 쓰는 인덱스(전체 메시지 미포함)"),
])

# 2. server.js: getRoomUserIds 함수 중복 제거
patch("server.js", [
    ("getRoomUserIds 함수 중복 제거",
     """// 0-85: 프로필 화면 등에서 "이 사람과 채팅방이 있는지"만 확인할 때 메시지 전체를
// 불러오지 않도록 userIds 필드만 가볍게 조회하는 함수 (프로필/채팅방 렉 원인 수정)
async function getRoomUserIds(roomId) {
  const snap = await db.ref(`chats/${roomId}/userIds`).once('value');
  return snap.val();
}
// 0-85: 프로필 화면 등에서 "이 사람과 채팅방이 있는지"만 확인할 때 메시지 전체를
// 불러오지 않도록 userIds 필드만 가볍게 조회하는 함수 (프로필/채팅방 렉 원인 수정)
async function getRoomUserIds(roomId) {
  const snap = await db.ref(`chats/${roomId}/userIds`).once('value');
  return snap.val();
}""",
     """// 0-85: 프로필 화면 등에서 "이 사람과 채팅방이 있는지"만 확인할 때 메시지 전체를
// 불러오지 않도록 userIds 필드만 가볍게 조회하는 함수 (프로필/채팅방 렉 원인 수정)
async function getRoomUserIds(roomId) {
  const snap = await db.ref(`chats/${roomId}/userIds`).once('value');
  return snap.val();
}"""),

    ("chat:get_room_index 핸들러 중복 제거 (이중 등록시 콜백 2번 호출되는 문제)",
     """  // 0-85: chat:get_list의 가벼운 버전. 메시지 전체를 불러오지 않고 "상대 id + roomId"만 반환.
  // 프로필 화면에서 메시지버튼 분기("메시지 보내기" / "채팅창으로 이동하기")에만 사용.
  socket.on('chat:get_room_index', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const idxSnap = await db.ref(`userChats/${userId}`).once('value');
      const myRoomIds = Object.keys(idxSnap.val() || {});
      const rooms = [];
      for (const roomId of myRoomIds) {
        const userIds = await getRoomUserIds(roomId);
        if (!userIds || !userIds.includes(userId)) continue;
        const otherId = userIds.find(id => id !== userId);
        rooms.push({ roomId, targetUser: { id: otherId } });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });

  // 0-85: chat:get_list의 가벼운 버전. 메시지 전체를 불러오지 않고 "상대 id + roomId"만 반환.
  // 프로필 화면에서 메시지버튼 분기("메시지 보내기" / "채팅창으로 이동하기")에만 사용.
  socket.on('chat:get_room_index', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const idxSnap = await db.ref(`userChats/${userId}`).once('value');
      const myRoomIds = Object.keys(idxSnap.val() || {});
      const rooms = [];
      for (const roomId of myRoomIds) {
        const userIds = await getRoomUserIds(roomId);
        if (!userIds || !userIds.includes(userId)) continue;
        const otherId = userIds.find(id => id !== userId);
        rooms.push({ roomId, targetUser: { id: otherId } });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });""",
     """  // 0-85: chat:get_list의 가벼운 버전. 메시지 전체를 불러오지 않고 "상대 id + roomId"만 반환.
  // 프로필 화면에서 메시지버튼 분기("메시지 보내기" / "채팅창으로 이동하기")에만 사용.
  socket.on('chat:get_room_index', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const idxSnap = await db.ref(`userChats/${userId}`).once('value');
      const myRoomIds = Object.keys(idxSnap.val() || {});
      const rooms = [];
      for (const roomId of myRoomIds) {
        const userIds = await getRoomUserIds(roomId);
        if (!userIds || !userIds.includes(userId)) continue;
        const otherId = userIds.find(id => id !== userId);
        rooms.push({ roomId, targetUser: { id: otherId } });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });"""),
])

print("\n0-86 중복제거 완료.")