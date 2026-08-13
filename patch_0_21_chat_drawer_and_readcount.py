#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0-21: 
1) 단체채팅방 정보 드로어(우측) 폭 82% -> 50%로 축소 + 내부 요소(아바타/닉네임/제목/패딩) 크기 축소로 잘림 방지
2) 1:1 채팅 "전송됨"/"읽음" 텍스트를 카카오톡처럼 "1"(안읽음)/표시없음(읽음)으로 변경
3) 읽음 처리를 "방을 열면 무조건 전체 읽음"이 아니라, 실제로 화면에 스크롤되어 보인 메시지까지만
   읽음 처리하도록 변경(IntersectionObserver 기반 뷰포트 감지). 연속으로 여러 메시지를 보내고
   상대가 일부만 보고 나간 경우, 본 메시지만 안읽음 숫자가 줄고 안 본 메시지는 그대로 유지됨.
   (단체채팅방은 기존 lastReadAt 기반 "안읽은 인원 수" 로직이 이미 정확했으므로, 그 lastReadAt이
   "방 진입 시각"이 아니라 "실제로 화면에 보인 마지막 메시지 시각"이 되도록 소스만 교체함)
"""

SERVER_PATH = "server.js"
INDEX_PATH = "public/index.html"

def patch_server():
    with open(SERVER_PATH, "r", encoding="utf-8") as f:
        s = f.read()

    old_chat_mark_read = """  socket.on('chat:mark_read', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds || !room.userIds.includes(userId)) return;
      const messages = room.messages || {};
      const updates = {};
      Object.keys(messages).forEach(mid => {
        const m = messages[mid];
        if (m && m.senderId !== userId && m.senderId !== 'system' && !m.read) {
          updates[`chats/${data.roomId}/messages/${mid}/read`] = true;
        }
      });
      // 메시지별 read 플래그 대신, 카톡처럼 "안읽은 인원 수"를 계산하기 위한 lastReadAt(마지막으로 읽은 시각)도 함께 기록
      const now = Date.now();
      updates[`chats/${data.roomId}/lastReadAt/${userId}`] = now;
      await db.ref().update(updates);
      const otherId = room.userIds.find(id => id !== userId);
      const sId = userToSocket[otherId];
      if (sId) io.to(sId).emit('chat:read_receipt', { roomId: data.roomId, userId, lastReadAt: now });
    } catch (e) { console.error(e); }
  });"""
    assert s.count(old_chat_mark_read) == 1, "chat:mark_read 핸들러를 찾지 못함"
    new_chat_mark_read = """  // 0-21: upToTimestamp가 오면(=실제로 화면에 보인 마지막 메시지 시각) 그 시점까지 온 메시지만 읽음 처리.
  // 값이 없으면 기존 방식대로 현재 시점 기준 전체 읽음 처리(하위호환용 폴백).
  socket.on('chat:mark_read', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds || !room.userIds.includes(userId)) return;
      const upToTimestamp = data && data.upToTimestamp;
      const messages = room.messages || {};
      const updates = {};
      Object.keys(messages).forEach(mid => {
        const m = messages[mid];
        if (!m || m.senderId === userId || m.senderId === 'system' || m.read) return;
        if (upToTimestamp && m.timestamp > upToTimestamp) return;
        updates[`chats/${data.roomId}/messages/${mid}/read`] = true;
      });
      const prevLastReadAt = (room.lastReadAt && room.lastReadAt[userId]) || 0;
      const now = Date.now();
      const newLastReadAt = upToTimestamp ? Math.max(prevLastReadAt, upToTimestamp) : now;
      updates[`chats/${data.roomId}/lastReadAt/${userId}`] = newLastReadAt;
      await db.ref().update(updates);
      const otherId = room.userIds.find(id => id !== userId);
      const sId = userToSocket[otherId];
      if (sId) io.to(sId).emit('chat:read_receipt', { roomId: data.roomId, userId, lastReadAt: newLastReadAt });
    } catch (e) { console.error(e); }
  });"""
    s = s.replace(old_chat_mark_read, new_chat_mark_read, 1)

    old_group_mark_read = """  socket.on('group:mark_read', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return;
      const now = Date.now();
      await db.ref(`groupChats/${data.roomId}/lastReadAt/${userId}`).set(now);
      emitToGroupMembers((room.meta.memberIds || []).filter(id => id !== userId), 'group:read_receipt', { roomId: data.roomId, userId, lastReadAt: now });
    } catch (e) { console.error(e); }
  });"""
    assert s.count(old_group_mark_read) == 1, "group:mark_read 핸들러를 찾지 못함"
    new_group_mark_read = """  // 0-21: upToTimestamp가 오면(=실제로 화면에 보인 마지막 메시지 시각) 그 시점까지만 읽은 것으로 기록.
  // 값이 없으면 기존 방식대로 현재 시점 기준 전체 읽음 처리(하위호환용 폴백).
  socket.on('group:mark_read', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return;
      const upToTimestamp = data && data.upToTimestamp;
      const prevLastReadAt = (room.lastReadAt && room.lastReadAt[userId]) || 0;
      const now = Date.now();
      const newLastReadAt = upToTimestamp ? Math.max(prevLastReadAt, upToTimestamp) : now;
      await db.ref(`groupChats/${data.roomId}/lastReadAt/${userId}`).set(newLastReadAt);
      emitToGroupMembers((room.meta.memberIds || []).filter(id => id !== userId), 'group:read_receipt', { roomId: data.roomId, userId, lastReadAt: newLastReadAt });
    } catch (e) { console.error(e); }
  });"""
    s = s.replace(old_group_mark_read, new_group_mark_read, 1)

    with open(SERVER_PATH, "w", encoding="utf-8") as f:
        f.write(s)
    print("server.js 패치 완료")


def patch_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        s = f.read()

    old_drawer_css = ".full-screen-overlay.drawer-right{left:auto;width:82%;box-shadow:-6px 0 20px rgba(0,0,0,.18);}"
    assert s.count(old_drawer_css) == 1, "drawer-right CSS를 찾지 못함"
    new_drawer_css = """.full-screen-overlay.drawer-right{left:auto;width:50%;box-shadow:-6px 0 20px rgba(0,0,0,.18);}
#groupInfoScreen .chat-row-nick{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
#groupInfoScreen .chat-row-fg{padding:9px 2px;gap:8px;}
#groupInfoScreen .avatar-sm{width:28px;height:28px;}
#groupInfoScreen #groupInfoTitle{font-size:14px;}
#groupInfoScreen #groupInfoIntro{font-size:11px;margin-bottom:12px;}
#groupInfoScreen [style*="font-size:13px;font-weight:700"]{font-size:12px;}
#groupInfoScreen #groupInfoMemberCount{font-size:11px;}"""
    s = s.replace(old_drawer_css, new_drawer_css, 1)

    old_padding = '<div style="padding:16px;overflow-y:auto;flex:1;">\n      <h3 id="groupInfoTitle" style="margin:0 0 4px;"></h3>'
    assert s.count(old_padding) == 1, "groupInfoScreen 본문 padding 영역을 찾지 못함"
    new_padding = '<div style="padding:10px;overflow-y:auto;flex:1;">\n      <h3 id="groupInfoTitle" style="margin:0 0 4px;"></h3>'
    s = s.replace(old_padding, new_padding, 1)

    old_status = "if (isMine){ const st=document.createElement('span'); st.className='msg-status'; st.textContent = m.read?'읽음':'전송됨'; timeRow.appendChild(st); }"
    assert s.count(old_status) == 1, "1:1 msg-status 렌더링 코드를 찾지 못함"
    new_status = "if (isMine && !m.read){ const st=document.createElement('span'); st.className='msg-status'; st.textContent = '1'; timeRow.appendChild(st); }"
    s = s.replace(old_status, new_status, 1)

    old_receipt = """socket.on('chat:read_receipt', ({roomId})=>{
  if (activeRoomId !== roomId) return;
  document.querySelectorAll('#chatMessageArea .msg-row.mine .msg-status').forEach(el=>{ el.textContent = '읽음'; });
});"""
    assert s.count(old_receipt) == 1, "chat:read_receipt 리스너를 찾지 못함"
    new_receipt = """socket.on('chat:read_receipt', ({roomId, lastReadAt})=>{
  if (activeRoomId !== roomId) return;
  // 0-21: 실제로 상대가 본 시점(lastReadAt)까지의 내 메시지만 "1" 표시를 지움(카톡처럼 부분 읽음 반영)
  (currentChatMessages||[]).forEach(m=>{ if (m.senderId===currentUser.id && !m.read && m.timestamp<=lastReadAt) m.read = true; });
  document.querySelectorAll('#chatMessageArea .msg-row.mine').forEach(row=>{
    const msg = (currentChatMessages||[]).find(x=>x.id===row.dataset.msgid);
    if (msg && msg.read){ const st = row.querySelector('.msg-status'); if (st) st.remove(); }
  });
});"""
    s = s.replace(old_receipt, new_receipt, 1)

    old_append_tail = """  row.appendChild(timeRow);
  area.appendChild(row);
  // 스크롤을 올려 옛 메시지를 보고 있을 때는 화면을 강제로 내리지 않음(대신 새 메시지 pill로 알림). 하단 근처거나 내가 보낸 메시지면 그대로 따라 내려감
  if (wasNearBottom || isMine){ area.scrollTop = area.scrollHeight; }
  if (m.id && !m.deletedForEveryone) attachMsgLongPress(bubble, m);
}"""
    assert s.count(old_append_tail) == 1, "appendChatBubble 마지막 부분을 찾지 못함"
    new_append_tail = """  row.appendChild(timeRow);
  area.appendChild(row);
  // 스크롤을 올려 옛 메시지를 보고 있을 때는 화면을 강제로 내리지 않음(대신 새 메시지 pill로 알림). 하단 근처거나 내가 보낸 메시지면 그대로 따라 내려감
  if (wasNearBottom || isMine){ area.scrollTop = area.scrollHeight; }
  if (m.id && !m.deletedForEveryone) attachMsgLongPress(bubble, m);
  // 0-21: 상대가 보낸 메시지가 실제로 화면에 스크롤되어 보였을 때만 읽음 처리 대상으로 관찰
  if (!isMine && m.id && m.timestamp) { row.dataset.msgts = String(m.timestamp); ensureChatReadObserver().observe(row); }
}"""
    s = s.replace(old_append_tail, new_append_tail, 1)

    old_group_append_tail = """  row.appendChild(timeRow);
  area.appendChild(row);
  area.scrollTop = area.scrollHeight;
  if (m.id) attachGroupMsgLongPress(bubble, m);"""
    assert s.count(old_group_append_tail) == 1, "appendGroupChatBubble 마지막 부분을 찾지 못함"
    new_group_append_tail = """  row.appendChild(timeRow);
  area.appendChild(row);
  area.scrollTop = area.scrollHeight;
  if (m.id) attachGroupMsgLongPress(bubble, m);
  // 0-21: 다른 사람이 보낸 메시지가 실제로 화면에 스크롤되어 보였을 때만 읽음 처리 대상으로 관찰
  if (!isMine && m.id && m.timestamp) { row.dataset.msgts = String(m.timestamp); ensureGroupReadObserver().observe(row); }"""
    s = s.replace(old_group_append_tail, new_group_append_tail, 1)

    anchor_fn = "function appendChatBubble(m, checkDate=true){"
    assert s.count(anchor_fn) == 1, "appendChatBubble 함수 선언부를 찾지 못함"
    helper_block = """// 0-21: 1:1 채팅 - 메시지가 실제로 뷰포트에 보였을 때만 읽음 처리(방을 열자마자 전체를 읽음 처리하지 않음)
let chatReadObserver = null;
let chatMaxSeenTs = 0;
let chatMarkReadTimer = null;
function ensureChatReadObserver(){
  if (chatReadObserver) return chatReadObserver;
  const root = document.getElementById('chatMessageArea');
  chatReadObserver = new IntersectionObserver((entries)=>{
    let changed = false;
    entries.forEach(entry=>{
      if (entry.isIntersecting && !document.hidden){
        const ts = Number(entry.target.dataset.msgts || 0);
        if (ts > chatMaxSeenTs) { chatMaxSeenTs = ts; changed = true; }
        chatReadObserver.unobserve(entry.target);
      }
    });
    if (changed) scheduleChatMarkRead();
  }, { root, threshold: 0.6 });
  return chatReadObserver;
}
function scheduleChatMarkRead(){
  clearTimeout(chatMarkReadTimer);
  chatMarkReadTimer = setTimeout(()=>{
    if (activeRoomId && chatMaxSeenTs > 0) socket.emit('chat:mark_read', { roomId: activeRoomId, upToTimestamp: chatMaxSeenTs });
  }, 350);
}
function appendChatBubble(m, checkDate=true){"""
    s = s.replace(anchor_fn, helper_block, 1)

    anchor_group_fn = "function appendGroupChatBubble(m){"
    assert s.count(anchor_group_fn) == 1, "appendGroupChatBubble 함수 선언부를 찾지 못함"
    group_helper_block = """// 0-21: 단체채팅 - 메시지가 실제로 뷰포트에 보였을 때만 읽음 처리(방을 열자마자 전체를 읽음 처리하지 않음)
let groupReadObserver = null;
let groupMaxSeenTs = 0;
let groupMarkReadTimer = null;
function ensureGroupReadObserver(){
  if (groupReadObserver) return groupReadObserver;
  const root = document.getElementById('groupChatMessageArea');
  groupReadObserver = new IntersectionObserver((entries)=>{
    let changed = false;
    entries.forEach(entry=>{
      if (entry.isIntersecting && !document.hidden){
        const ts = Number(entry.target.dataset.msgts || 0);
        if (ts > groupMaxSeenTs) { groupMaxSeenTs = ts; changed = true; }
        groupReadObserver.unobserve(entry.target);
      }
    });
    if (changed) scheduleGroupMarkRead();
  }, { root, threshold: 0.6 });
  return groupReadObserver;
}
function scheduleGroupMarkRead(){
  clearTimeout(groupMarkReadTimer);
  groupMarkReadTimer = setTimeout(()=>{
    if (activeGroupRoomId && groupMaxSeenTs > 0) socket.emit('group:mark_read', { roomId: activeGroupRoomId, upToTimestamp: groupMaxSeenTs });
  }, 350);
}
function appendGroupChatBubble(m){"""
    s = s.replace(anchor_group_fn, group_helper_block, 1)

    old_open_modal = """  document.getElementById('chatTargetName').textContent = target.nickname || '';
  const area = document.getElementById('chatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';
  let lastDate = null;
  (messages||[]).forEach(m=>{
    if (m.timestamp){
      const dateStr = new Date(m.timestamp).toDateString();
      if (dateStr !== lastDate){ const sep=document.createElement('div'); sep.className='chat-date-sep'; sep.textContent=formatDateSep(m.timestamp); area.appendChild(sep); lastDate=dateStr; area.dataset.lastDate=dateStr; }
    }
    appendChatBubble(m, false);
  });
  area.scrollTop = area.scrollHeight;
  openModal('chatModal');
  socket.emit('chat:mark_read', {roomId});
}"""
    assert s.count(old_open_modal) == 1, "openChatModal 본문을 찾지 못함"
    new_open_modal = """  document.getElementById('chatTargetName').textContent = target.nickname || '';
  chatMaxSeenTs = 0;
  const area = document.getElementById('chatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';
  let lastDate = null;
  (messages||[]).forEach(m=>{
    if (m.timestamp){
      const dateStr = new Date(m.timestamp).toDateString();
      if (dateStr !== lastDate){ const sep=document.createElement('div'); sep.className='chat-date-sep'; sep.textContent=formatDateSep(m.timestamp); area.appendChild(sep); lastDate=dateStr; area.dataset.lastDate=dateStr; }
    }
    appendChatBubble(m, false);
  });
  area.scrollTop = area.scrollHeight;
  openModal('chatModal');
  // 0-21: 방을 여는 즉시 전체를 읽음 처리하지 않음. 지금 화면에 실제로 보이는 메시지는
  // 위 appendChatBubble에서 건 IntersectionObserver가 알아서 감지해 부분 읽음 처리함.
}"""
    s = s.replace(old_open_modal, new_open_modal, 1)

    old_close_chat = """function closeChatModal(){
  closeModal('chatModal');
  activeRoomId = null;
  activeChatTargetId = null;
  closeChatSearchBar();
}"""
    assert s.count(old_close_chat) == 1, "closeChatModal 함수를 찾지 못함"
    new_close_chat = """function closeChatModal(){
  closeModal('chatModal');
  activeRoomId = null;
  activeChatTargetId = null;
  closeChatSearchBar();
  clearTimeout(chatMarkReadTimer);
  chatMaxSeenTs = 0;
}"""
    s = s.replace(old_close_chat, new_close_chat, 1)

    old_new_msg = "    if (!isMine && message.senderId !== 'system') socket.emit('chat:mark_read', {roomId});\n"
    assert s.count(old_new_msg) == 1, "chat:new_message 내 블랭킷 mark_read 호출을 찾지 못함"
    s = s.replace(old_new_msg, "", 1)

    old_group_open = """  activeGroupLastReadAt = (cached && cached.lastReadAt) || {};
  document.getElementById('groupChatTitle').textContent = (cached && cached.meta && cached.meta.title) || '단체채팅방';
  const area = document.getElementById('groupChatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';
  (cached && cached.messages || []).forEach(m=>appendGroupChatBubble(m));
  area.scrollTop = area.scrollHeight;
  openFullScreen('groupChatModal');
  socket.emit('group:info', {roomId}, (res)=>{
    if (res && res.success){
      activeGroupRoomMeta = res;
      if (activeGroupRoomId===roomId && (res.blockedUserIds||[]).length){
        const area2 = document.getElementById('groupChatMessageArea'); area2.innerHTML=''; area2.dataset.lastDate='';
        (cached && cached.messages || []).forEach(m=>appendGroupChatBubble(m));
        area2.scrollTop = area2.scrollHeight;
      }
    }
  });
  socket.emit('group:mark_read', {roomId});
}"""
    assert s.count(old_group_open) == 1, "openGroupChatRoom 본문을 찾지 못함"
    new_group_open = """  activeGroupLastReadAt = (cached && cached.lastReadAt) || {};
  groupMaxSeenTs = 0;
  document.getElementById('groupChatTitle').textContent = (cached && cached.meta && cached.meta.title) || '단체채팅방';
  const area = document.getElementById('groupChatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';
  (cached && cached.messages || []).forEach(m=>appendGroupChatBubble(m));
  area.scrollTop = area.scrollHeight;
  openFullScreen('groupChatModal');
  socket.emit('group:info', {roomId}, (res)=>{
    if (res && res.success){
      activeGroupRoomMeta = res;
      if (activeGroupRoomId===roomId && (res.blockedUserIds||[]).length){
        const area2 = document.getElementById('groupChatMessageArea'); area2.innerHTML=''; area2.dataset.lastDate='';
        (cached && cached.messages || []).forEach(m=>appendGroupChatBubble(m));
        area2.scrollTop = area2.scrollHeight;
      }
    }
  });
  // 0-21: 방을 여는 즉시 전체를 읽음 처리하지 않음. 지금 화면에 실제로 보이는 메시지는
  // 위 appendGroupChatBubble에서 건 IntersectionObserver가 알아서 감지해 부분 읽음 처리함.
}"""
    s = s.replace(old_group_open, new_group_open, 1)

    old_close_group = """function closeGroupChatModal(){
  closeFullScreen('groupChatModal');
  activeGroupRoomId = null;
  activeGroupRoomMeta = null;
  closeGroupChatSearchBar();
  loadChatRoomList();
}"""
    assert s.count(old_close_group) == 1, "closeGroupChatModal 함수를 찾지 못함"
    new_close_group = """function closeGroupChatModal(){
  closeFullScreen('groupChatModal');
  activeGroupRoomId = null;
  activeGroupRoomMeta = null;
  closeGroupChatSearchBar();
  loadChatRoomList();
  clearTimeout(groupMarkReadTimer);
  groupMaxSeenTs = 0;
}"""
    s = s.replace(old_close_group, new_close_group, 1)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(s)
    print("public/index.html 패치 완료")


if __name__ == "__main__":
    patch_server()
    patch_index()
    print("0-21 패치 전체 완료")