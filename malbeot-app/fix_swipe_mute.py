#!/usr/bin/env python3
# 0-8: 채팅창 스와이프 나가기 버튼 개선
# - 1:1 채팅에는 원래 알림끄기(mute) 기능 자체가 없었음(단체채팅에만 있었음) -> chat:toggle_mute 서버 이벤트 신규 추가
# - 채팅목록 스와이프 시 휴지통(나가기) 왼쪽에 종모양 알림끄기 아이콘 추가 (1:1 + 단체 둘 다), 카카오 스타일
# - 스와이프 폭을 -70px(버튼1개) -> -140px(버튼2개)로 확장
# - 종 아이콘 클릭 시 스와이프는 안 닫힌 채로 mute만 토글되고 아이콘이 벨/벨-슬래시로 즉시 전환됨
# - 1:1 채팅은 muted 상태면 백그라운드 메시지 알림배너(showNotifyBanner)/OS알림을 건너뛰도록 함
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_swipe_mute.py

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
"""  socket.on('chat:get_list', async (cb) => {
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
        rooms.push({ roomId, targetUser, messages, unreadCount, lastReadAt: room.lastReadAt || {} });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });""",
"""  socket.on('chat:get_list', async (cb) => {
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
  });

  // 1:1 채팅 알림끄기(mute) 토글 - 기존에는 단체채팅에만 있던 기능을 1:1에도 동일하게 추가
  socket.on('chat:toggle_mute', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false });
      const snap = await db.ref(`chats/${data.roomId}/muted/${userId}`).once('value');
      const nowMuted = !snap.val();
      await db.ref(`chats/${data.roomId}/muted/${userId}`).set(nowMuted);
      cb && cb({ success: true, muted: nowMuted });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });"""
),
]

css_replacements = [
(
""".chat-row-fg{position:relative;background:#fff;display:flex;gap:12px;align-items:center;padding:12px 4px;cursor:pointer;touch-action:pan-y;}""",
""".chat-row-fg{position:relative;background:#fff;display:flex;gap:12px;align-items:center;padding:12px 4px;cursor:pointer;touch-action:pan-y;}
.chat-row-mute{position:absolute;top:0;right:70px;width:70px;height:100%;background:var(--bg-subtle);display:flex;align-items:center;justify-content:center;color:var(--text-main);font-size:16px;cursor:pointer;}"""
),
]

html_replacements = [
(
"""    const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
    wrap.innerHTML = `
      <div class="chat-row-delete" onclick="leaveGroupRoomFromList('${room.roomId}')"><i class="fa-solid fa-right-from-bracket"></i></div>
      <div class="chat-row-fg" data-roomid="${room.roomId}">
        <div class="avatar-sm" style="display:flex;align-items:center;justify-content:center;background:var(--bg-secondary,#eee);"><i class="fa-solid fa-users"></i></div>
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(meta.title||'')} <span style="color:var(--text-muted);font-weight:400;">${(meta.memberIds||[]).length}</span></div>
          <div class="chat-row-last">${escapeHtml(lastPreview)}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <div class="chat-row-time">${lastMsg.timestamp?formatRelativeTime(lastMsg.timestamp):''}</div>
          ${unread>0?`<div class="unread-badge">${unread>99?'99+':unread}</div>`:''}
        </div>
      </div>`;
    const fg = wrap.querySelector('.chat-row-fg');
    attachSwipe(fg);
    fg.addEventListener('click', ()=>{ if (fg.dataset.swiped==='1') return; openGroupChatRoom(room.roomId); });
    c.appendChild(wrap);""",
"""    const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
    wrap.innerHTML = `
      <div class="chat-row-delete" onclick="leaveGroupRoomFromList('${room.roomId}')"><i class="fa-solid fa-right-from-bracket"></i></div>
      <div class="chat-row-mute" onclick="toggleGroupMuteFromList('${room.roomId}', this)"><i class="fa-solid ${room.muted?'fa-bell-slash':'fa-bell'}"></i></div>
      <div class="chat-row-fg" data-roomid="${room.roomId}">
        <div class="avatar-sm" style="display:flex;align-items:center;justify-content:center;background:var(--bg-secondary,#eee);"><i class="fa-solid fa-users"></i></div>
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(meta.title||'')} <span style="color:var(--text-muted);font-weight:400;">${(meta.memberIds||[]).length}</span></div>
          <div class="chat-row-last">${escapeHtml(lastPreview)}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <div class="chat-row-time">${lastMsg.timestamp?formatRelativeTime(lastMsg.timestamp):''}</div>
          ${unread>0?`<div class="unread-badge">${unread>99?'99+':unread}</div>`:''}
        </div>
      </div>`;
    const fg = wrap.querySelector('.chat-row-fg');
    attachSwipe(fg);
    fg.addEventListener('click', ()=>{ if (fg.dataset.swiped==='1') return; openGroupChatRoom(room.roomId); });
    c.appendChild(wrap);"""
),
(
"""    const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
    wrap.innerHTML = `
      <div class="chat-row-delete" onclick="deleteRoomFromList('${room.roomId}')"><i class="fa-solid fa-trash-can"></i></div>
      <div class="chat-row-fg" data-roomid="${room.roomId}">
        ${avatarHtmlFor(target,'avatar-sm')}
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div>
          <div class="chat-row-last">${escapeHtml(lastPreview)}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <div class="chat-row-time">${lastMsg.timestamp?formatRelativeTime(lastMsg.timestamp):''}</div>
          ${unread>0?`<div class="unread-badge">${unread>99?'99+':unread}</div>`:''}
        </div>
      </div>`;
    const fg = wrap.querySelector('.chat-row-fg');
    attachSwipe(fg);
    fg.addEventListener('click', ()=>{ if (fg.dataset.swiped==='1') return; openChatModal(room.roomId, target, room.messages); });
    c.appendChild(wrap);""",
"""    const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
    wrap.innerHTML = `
      <div class="chat-row-delete" onclick="deleteRoomFromList('${room.roomId}')"><i class="fa-solid fa-trash-can"></i></div>
      <div class="chat-row-mute" onclick="toggleChatMuteFromList('${room.roomId}', this)"><i class="fa-solid ${room.muted?'fa-bell-slash':'fa-bell'}"></i></div>
      <div class="chat-row-fg" data-roomid="${room.roomId}">
        ${avatarHtmlFor(target,'avatar-sm')}
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div>
          <div class="chat-row-last">${escapeHtml(lastPreview)}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <div class="chat-row-time">${lastMsg.timestamp?formatRelativeTime(lastMsg.timestamp):''}</div>
          ${unread>0?`<div class="unread-badge">${unread>99?'99+':unread}</div>`:''}
        </div>
      </div>`;
    const fg = wrap.querySelector('.chat-row-fg');
    attachSwipe(fg);
    fg.addEventListener('click', ()=>{ if (fg.dataset.swiped==='1') return; openChatModal(room.roomId, target, room.messages); });
    c.appendChild(wrap);"""
),
(
"""function attachSwipe(el){
  let startX=0, currentX=0, dragging=false;
  const start=(x)=>{ startX=x; dragging=true; el.style.transition='none'; };
  const move=(x)=>{ if(!dragging) return; currentX=Math.min(0,Math.max(-70,x-startX)); el.style.transform=`translateX(${currentX}px)`; };
  const end=()=>{
    if(!dragging) return;
    dragging=false;
    el.style.transition='transform .2s';
    const wrap = el.closest('.chat-row-wrap');
    if (currentX<-35){
      if (currentlySwipedWrap && currentlySwipedWrap!==wrap) closeSwipedRow();
      el.style.transform='translateX(-70px)'; el.dataset.swiped='1';
      currentlySwipedWrap = wrap;
    } else {
      el.style.transform='translateX(0)'; el.dataset.swiped='0';
      if (currentlySwipedWrap===wrap) currentlySwipedWrap = null;
    }
  };
  el.addEventListener('touchstart', e=>start(e.touches[0].clientX));
  el.addEventListener('touchmove', e=>move(e.touches[0].clientX));
  el.addEventListener('touchend', end);
  el.addEventListener('mousedown', e=>start(e.clientX));
  el.addEventListener('mousemove', e=>{ if(dragging) move(e.clientX); });
  document.addEventListener('mouseup', end);
}""",
"""function attachSwipe(el){
  let startX=0, currentX=0, dragging=false;
  const start=(x)=>{ startX=x; dragging=true; el.style.transition='none'; };
  const move=(x)=>{ if(!dragging) return; currentX=Math.min(0,Math.max(-140,x-startX)); el.style.transform=`translateX(${currentX}px)`; };
  const end=()=>{
    if(!dragging) return;
    dragging=false;
    el.style.transition='transform .2s';
    const wrap = el.closest('.chat-row-wrap');
    if (currentX<-70){
      if (currentlySwipedWrap && currentlySwipedWrap!==wrap) closeSwipedRow();
      el.style.transform='translateX(-140px)'; el.dataset.swiped='1';
      currentlySwipedWrap = wrap;
    } else {
      el.style.transform='translateX(0)'; el.dataset.swiped='0';
      if (currentlySwipedWrap===wrap) currentlySwipedWrap = null;
    }
  };
  el.addEventListener('touchstart', e=>start(e.touches[0].clientX));
  el.addEventListener('touchmove', e=>move(e.touches[0].clientX));
  el.addEventListener('touchend', end);
  el.addEventListener('mousedown', e=>start(e.clientX));
  el.addEventListener('mousemove', e=>{ if(dragging) move(e.clientX); });
  document.addEventListener('mouseup', end);
}
// 채팅목록 스와이프에서 종모양 아이콘 클릭 시 mute 토글 (스와이프는 닫지 않고 아이콘만 즉시 전환)
let mutedChatRoomIds = new Set();
function toggleChatMuteFromList(roomId, iconWrapEl){
  socket.emit('chat:toggle_mute', {roomId}, (res)=>{
    if (!res || !res.success) return;
    const icon = iconWrapEl.querySelector('i');
    icon.className = res.muted ? 'fa-solid fa-bell-slash' : 'fa-solid fa-bell';
    if (res.muted) mutedChatRoomIds.add(roomId); else mutedChatRoomIds.delete(roomId);
  });
}
function toggleGroupMuteFromList(roomId, iconWrapEl){
  socket.emit('group:toggle_mute', {roomId}, (res)=>{
    if (!res || !res.success) return;
    const icon = iconWrapEl.querySelector('i');
    icon.className = res.muted ? 'fa-solid fa-bell-slash' : 'fa-solid fa-bell';
  });
}"""
),
(
"""  } else if (message.senderId !== 'system' && !isMine && getEffectiveSettings().notifyChat) {""",
"""  } else if (message.senderId !== 'system' && !isMine && getEffectiveSettings().notifyChat && !mutedChatRoomIds.has(roomId)) {"""
),
(
"""function renderChatRoomList(){
  currentlySwipedWrap = null;
  const c = document.getElementById('chatRoomList'); c.innerHTML='';""",
"""function renderChatRoomList(){
  currentlySwipedWrap = null;
  mutedChatRoomIds = new Set(currentChatRooms.filter(r=>r.muted).map(r=>r.roomId));
  const c = document.getElementById('chatRoomList'); c.innerHTML='';"""
),
]

patch('server.js', server_replacements)
patch('public/index.html', css_replacements + html_replacements)
print("\n패치 완료. 다음 순서로 진행하세요:")
print("1) node -c server.js")
print("2) git add -A && git commit -m \"0-8: 채팅창 스와이프 나가기 버튼 개선 - 1:1 채팅 알림끄기 신규 추가 + 스와이프에 종모양 버튼 노출\"")
print("3) (모아뒀다가 원하실 때) git push")
