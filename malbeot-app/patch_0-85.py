# -*- coding: utf-8 -*-
# 0-85: 인수인계서 v20 조사분 6개 버그 수정
# 1) 채팅 전송 버튼 안눌림 (touchstart preventDefault가 click을 씹음)
# 2) 상단 버튼 상태바 겹침 (safe-area 누락)
# 3) 프로필/채팅방 렉 (전체 메시지 통째 로딩)
# 4) 카메라 촬영시 크래시 (Info.plist 권한 문구 누락)
# 5) 채팅방 진입시 스크롤이 맨 위에 걸림 (display:none 상태에서 스크롤 계산)
# 6) 사진편집 블러 효과 약함

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


# ============================================================
# 1. server.js - 프로필 렉 원인(전체 메시지 로딩) 수정용 서버 함수/엔드포인트 추가
# ============================================================
patch("server.js", [
    ("getRoomUserIds 함수 추가",
     """async function getRoom(roomId) {
  const snap = await db.ref(`chats/${roomId}`).once('value');
  return snap.val();
}""",
     """async function getRoom(roomId) {
  const snap = await db.ref(`chats/${roomId}`).once('value');
  return snap.val();
}
// 0-85: 프로필 화면 등에서 "이 사람과 채팅방이 있는지"만 확인할 때 메시지 전체를
// 불러오지 않도록 userIds 필드만 가볍게 조회하는 함수 (프로필/채팅방 렉 원인 수정)
async function getRoomUserIds(roomId) {
  const snap = await db.ref(`chats/${roomId}/userIds`).once('value');
  return snap.val();
}"""),

    ("chat:get_room_index 엔드포인트 추가",
     """  socket.on('chat:get_list', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const idxSnap = await db.ref(`userChats/${userId}`).once('value');
      const myRoomIds = Object.keys(idxSnap.val() || {});
      const rooms = [];
      for (const roomId of myRoomIds) {
        const room = await getRoom(roomId);
        if (!room || !room.userIds || !room.userIds.includes(userId)) continue;
        const otherId = room.userIds.find(id => id !== userId);
        const targetUser = await getUser(otherId);
        const messages = (room.messages ? Object.values(room.messages) : []).filter(m => !(m.deletedFor || []).includes(userId));
        const unreadCount = messages.filter(m => m.senderId !== userId && m.senderId !== 'system' && !m.read).length;
        const muted = !!(room.muted && room.muted[userId]);
        rooms.push({ roomId, targetUser, messages, unreadCount, lastReadAt: room.lastReadAt || {}, muted });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });""",
     """  socket.on('chat:get_list', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const idxSnap = await db.ref(`userChats/${userId}`).once('value');
      const myRoomIds = Object.keys(idxSnap.val() || {});
      const rooms = [];
      for (const roomId of myRoomIds) {
        const room = await getRoom(roomId);
        if (!room || !room.userIds || !room.userIds.includes(userId)) continue;
        const otherId = room.userIds.find(id => id !== userId);
        const targetUser = await getUser(otherId);
        const messages = (room.messages ? Object.values(room.messages) : []).filter(m => !(m.deletedFor || []).includes(userId));
        const unreadCount = messages.filter(m => m.senderId !== userId && m.senderId !== 'system' && !m.read).length;
        const muted = !!(room.muted && room.muted[userId]);
        rooms.push({ roomId, targetUser, messages, unreadCount, lastReadAt: room.lastReadAt || {}, muted });
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
  });"""),
])


# ============================================================
# 2. public/index.html
# ============================================================
patch("public/index.html", [

    # --- 버그1: 채팅 전송버튼 안눌림 (touchstart preventDefault가 click을 씹음) ---
    ("1:1 채팅 전송버튼 touchstart preventDefault 제거",
     "['mousedown','touchstart'].forEach(evt=>{\n  btnSendMsgEl.addEventListener(evt, (e)=>{ e.preventDefault(); }, {passive:false});\n});",
     "['mousedown'].forEach(evt=>{\n  btnSendMsgEl.addEventListener(evt, (e)=>{ e.preventDefault(); }, {passive:false});\n});"),

    ("단체채팅 전송버튼 touchstart preventDefault 제거",
     "['mousedown','touchstart'].forEach(evt=>{\n  btnSendGroupMsgEl.addEventListener(evt, (e)=>{ e.preventDefault(); }, {passive:false});\n});",
     "['mousedown'].forEach(evt=>{\n  btnSendGroupMsgEl.addEventListener(evt, (e)=>{ e.preventDefault(); }, {passive:false});\n});"),

    # --- 버그2: 상단 버튼 상태바 겹침 (safe-area 누락) ---
    (".fs-header safe-area 여백 추가",
     ".fs-header{height:52px;flex-shrink:0;display:flex;align-items:center;padding:0 12px;border-bottom:1px solid var(--border-color);position:relative;}",
     ".fs-header{min-height:52px;flex-shrink:0;display:flex;align-items:center;padding:env(safe-area-inset-top, 0px) 12px 0 12px;border-bottom:1px solid var(--border-color);position:relative;}"),

    ("사진뷰어 닫기버튼 safe-area 보정",
     '<div onclick="closePhotoViewer()" style="position:absolute;top:16px;left:16px;z-index:2;color:#fff;font-size:22px;width:38px;height:38px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.35);border-radius:50%;cursor:pointer;"><i class="fa-solid fa-xmark"></i></div>',
     '<div onclick="closePhotoViewer()" style="position:absolute;top:calc(16px + env(safe-area-inset-top, 0px));left:16px;z-index:2;color:#fff;font-size:22px;width:38px;height:38px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.35);border-radius:50%;cursor:pointer;"><i class="fa-solid fa-xmark"></i></div>'),

    ("스토리/릴스 뒤로가기버튼 safe-area 보정",
     '<button class="back-btn" style="position:absolute;top:12px;left:12px;color:#fff;z-index:6;background:rgba(0,0,0,.35);border-radius:50%;width:34px;height:34px;" onclick="event.stopPropagation();closeStoryViewer()"><i class="fa-solid fa-arrow-left"></i></button>',
     '<button class="back-btn" style="position:absolute;top:calc(12px + env(safe-area-inset-top, 0px));left:12px;color:#fff;z-index:6;background:rgba(0,0,0,.35);border-radius:50%;width:34px;height:34px;" onclick="event.stopPropagation();closeStoryViewer()"><i class="fa-solid fa-arrow-left"></i></button>'),

    ("스토리 음소거버튼 safe-area 보정",
     '<button id="storyMuteBtn" class="hidden" style="position:absolute;top:12px;right:52px;z-index:6;background:rgba(0,0,0,.35);border:none;color:#fff;width:34px;height:34px;border-radius:50%;" onclick="event.stopPropagation();toggleStoryMute()"><i id="storyMuteIcon" class="fa-solid fa-volume-xmark"></i></button>',
     '<button id="storyMuteBtn" class="hidden" style="position:absolute;top:calc(12px + env(safe-area-inset-top, 0px));right:52px;z-index:6;background:rgba(0,0,0,.35);border:none;color:#fff;width:34px;height:34px;border-radius:50%;" onclick="event.stopPropagation();toggleStoryMute()"><i id="storyMuteIcon" class="fa-solid fa-volume-xmark"></i></button>'),

    ("스토리 작성버튼 safe-area 보정",
     '<button style="position:absolute;top:12px;right:12px;z-index:6;background:rgba(0,0,0,.35);border:none;color:#fff;width:34px;height:34px;border-radius:50%;" onclick="event.stopPropagation();openStoryComposeScreen()"><i class="fa-solid fa-plus"></i></button>',
     '<button style="position:absolute;top:calc(12px + env(safe-area-inset-top, 0px));right:12px;z-index:6;background:rgba(0,0,0,.35);border:none;color:#fff;width:34px;height:34px;border-radius:50%;" onclick="event.stopPropagation();openStoryComposeScreen()"><i class="fa-solid fa-plus"></i></button>'),

    # --- 버그3: 프로필/채팅방 렉 (전체 메시지 통째 로딩) ---
    ("전역변수 currentChatRoomIndex 추가",
     "let currentChatRooms = [];",
     "let currentChatRooms = [];\nlet currentChatRoomIndex = []; // 0-85: 프로필 등에서 메시지유무만 가볍게 확인할 때 쓰는 인덱스(전체 메시지 미포함)"),

    ("프로필화면 진입시 가벼운 인덱스로 교체",
     "  socket.emit('chat:get_list', (res)=>{\n    if (res && res.success) currentChatRooms = res.rooms;\n    roomsLoaded = true; tryOpenProfile();\n  });",
     "  socket.emit('chat:get_room_index', (res)=>{\n    if (res && res.success) currentChatRoomIndex = res.rooms;\n    roomsLoaded = true; tryOpenProfile();\n  });"),

    ("프로필 메시지버튼 분기 체크 대상 변경",
     "const existingRoom = (currentChatRooms||[]).find(r=>r.targetUser && r.targetUser.id===user.id);",
     "const existingRoom = (currentChatRoomIndex||[]).find(r=>r.targetUser && r.targetUser.id===user.id);"),

    ("handleSendMessageClick 가벼운 인덱스로 교체",
     "function handleSendMessageClick(){\n  const targetId = currentProfileUserId; if (!targetId) return;\n  socket.emit('chat:get_list', (res)=>{\n    if (res && res.success){\n      currentChatRooms = res.rooms;\n      const existing = currentChatRooms.find(r=>r.targetUser && r.targetUser.id===targetId);",
     "function handleSendMessageClick(){\n  const targetId = currentProfileUserId; if (!targetId) return;\n  socket.emit('chat:get_room_index', (res)=>{\n    if (res && res.success){\n      currentChatRoomIndex = res.rooms;\n      const existing = currentChatRoomIndex.find(r=>r.targetUser && r.targetUser.id===targetId);"),

    # --- 버그5: 채팅방 진입시 스크롤이 맨 위에 걸림 (display:none 상태에서 계산됨) ---
    ("1:1 채팅방 진입 스크롤 순서 수정",
     "  area.scrollTop = area.scrollHeight;\n  openModal('chatModal');",
     "  openModal('chatModal');\n  requestAnimationFrame(()=>{ area.scrollTop = area.scrollHeight; });"),

    ("단체채팅방 진입 스크롤 순서 수정",
     "  area.scrollTop = area.scrollHeight;\n  openFullScreen('groupChatModal');",
     "  openFullScreen('groupChatModal');\n  requestAnimationFrame(()=>{ area.scrollTop = area.scrollHeight; });"),

    # --- 버그6: 사진편집 블러효과 강도 상향 ---
    ("사진편집 블러 강도 10px -> 28px",
     "bctx.filter = 'blur(10px)';",
     "bctx.filter = 'blur(28px)';"),
])


# ============================================================
# 3. iOS Info.plist - 카메라 크래시 원인(권한 문구 누락) 수정
# ============================================================
patch("ios/App/App/Info.plist", [
    ("카메라/사진첩 권한 문구 추가",
     "\t<key>NSUserTrackingUsageDescription</key>\n\t<string>맞춤형 광고를 제공하기 위해 사용됩니다.</string>\n</dict>\n</plist>",
     "\t<key>NSUserTrackingUsageDescription</key>\n\t<string>맞춤형 광고를 제공하기 위해 사용됩니다.</string>\n\t<key>NSCameraUsageDescription</key>\n\t<string>프로필 사진 촬영 및 채팅 사진 전송을 위해 카메라 접근이 필요합니다.</string>\n\t<key>NSPhotoLibraryUsageDescription</key>\n\t<string>프로필 사진 등록 및 채팅 사진 전송을 위해 사진 라이브러리 접근이 필요합니다.</string>\n\t<key>NSPhotoLibraryAddUsageDescription</key>\n\t<string>촬영하거나 편집한 사진을 저장하기 위해 사진 라이브러리 접근이 필요합니다.</string>\n</dict>\n</plist>"),
])

print("\n0-85 패치 완료.")