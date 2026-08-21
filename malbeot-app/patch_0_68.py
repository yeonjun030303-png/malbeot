with open("server.js", "r", encoding="utf-8") as f:
    srv = f.read()

old_delete = """async function deleteRoom(roomId) {
  await db.ref(`chats/${roomId}`).remove();
}"""
assert srv.count(old_delete) == 1, "old_delete 매칭 실패"
new_delete = """async function deleteRoom(roomId) {
  const room = await getRoom(roomId);
  if (room && room.userIds) {
    await Promise.all(room.userIds.map(uid => db.ref(`userChats/${uid}/${roomId}`).remove()));
  }
  await db.ref(`chats/${roomId}`).remove();
}

async function addUserChatIndex(roomId, userIds) {
  await Promise.all(userIds.map(uid => db.ref(`userChats/${uid}/${roomId}`).set(true)));
}"""
srv = srv.replace(old_delete, new_delete)

old_create = """        await saveRoomMeta(roomId, { roomId, userIds: [user.id, target.id] });
        await addMessage(roomId, { senderId: 'system', text: '대화가 시작되었습니다. (쌀 50개 차감)', timestamp: Date.now() });"""
count_create = srv.count(old_create)
assert count_create == 2, f"old_create 매칭 개수 이상함(기대 2, 실제 {count_create})"
new_create = """        await saveRoomMeta(roomId, { roomId, userIds: [user.id, target.id] });
        await addUserChatIndex(roomId, [user.id, target.id]);
        await addMessage(roomId, { senderId: 'system', text: '대화가 시작되었습니다. (쌀 50개 차감)', timestamp: Date.now() });"""
srv = srv.replace(old_create, new_create)

old_get_list = """  socket.on('chat:get_list', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const snap = await db.ref('chats').once('value');
      const allChats = snap.val() || {};
      const rooms = [];
      for (const roomId of Object.keys(allChats)) {
        const room = allChats[roomId];
        if (!room.userIds || !room.userIds.includes(userId)) continue;
        const otherId = room.userIds.find(id => id !== userId);
        const targetUser = await getUser(otherId);
        const messages = (room.messages ? Object.values(room.messages) : []).filter(m => !(m.deletedFor || []).includes(userId));
        const unreadCount = messages.filter(m => m.senderId !== userId && m.senderId !== 'system' && !m.read).length;
        const muted = !!(room.muted && room.muted[userId]);
        rooms.push({ roomId, targetUser, messages, unreadCount, lastReadAt: room.lastReadAt || {}, muted });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });"""
assert srv.count(old_get_list) == 1, "old_get_list 매칭 실패"
new_get_list = """  socket.on('chat:get_list', async (cb) => {
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
  });"""
srv = srv.replace(old_get_list, new_get_list)

old_boot = """setTimeout(() => {
  loadNsfwModel()
    .then(() => console.log('✅ NSFW 이미지 검사 모델 예열 완료'))
    .catch(err => console.error('⚠️ NSFW 모델 예열 실패(사용자 요청 시점에 재시도됨):', err.message));
}, 5000);"""
assert srv.count(old_boot) == 1, "old_boot 매칭 실패"
new_boot = old_boot + """

setTimeout(async () => {
  try {
    const marker = await db.ref('meta/userChatsIndexBackfillDone').once('value');
    if (marker.val()) return;
    console.log('🔄 0-68: userChats 인덱스 백필 시작...');
    const snap = await db.ref('chats').once('value');
    const allChats = snap.val() || {};
    let count = 0;
    for (const roomId of Object.keys(allChats)) {
      const room = allChats[roomId];
      if (room && Array.isArray(room.userIds)) {
        await addUserChatIndex(roomId, room.userIds);
        count++;
      }
    }
    await db.ref('meta/userChatsIndexBackfillDone').set(true);
    console.log(`✅ 0-68: userChats 인덱스 백필 완료 (방 ${count}개)`);
  } catch (e) {
    console.error('0-68 userChats 인덱스 백필 실패(다음 재시작 때 재시도됨):', e);
  }
}, 20000);"""
srv = srv.replace(old_boot, new_boot)

with open("server.js", "w", encoding="utf-8") as f:
    f.write(srv)

print("0-68 패치 완료")
