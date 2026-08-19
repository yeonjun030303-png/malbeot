# -*- coding: utf-8 -*-
# 0-51: 채팅창으로 이동하기 버튼 회색 처리, 단톡방 이름 옆 참가인원수 표시,
#       채팅목록 알림꺼짐 종모양 표시, 팔로잉/팔로워 수 불일치(탈퇴유저 잔여참조) 버그 수정
# 반드시 malbeot-app 폴더 안에서 실행하세요 (server.js, public/index.html 이 같은 폴더에 있어야 함)

import os

def apply(path, replacements):
    if not os.path.exists(path):
        print(f"❌ 파일을 찾을 수 없습니다: {path} (실행 위치를 확인하세요)")
        raise SystemExit(1)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        cnt = content.count(old)
        if cnt != 1:
            print(f"❌ {path} 에서 패턴을 정확히 1곳에서 찾지 못했습니다(발견 {cnt}회). 이미 적용됐거나 코드가 변경되었을 수 있습니다.")
            print("---- 찾으려던 내용 ----")
            print(old[:200])
            raise SystemExit(1)
        content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

INDEX_HTML = "public/index.html"
SERVER_JS = "server.js"

index_replacements = [
    (
        '<div class="chat-header-nick" id="groupChatTitle" style="cursor:default;">단체채팅방</div>',
        '<div class="chat-header-nick" style="cursor:default;"><span id="groupChatTitle">단체채팅방</span> <span id="groupChatMemberCount" style="color:var(--text-muted);font-weight:400;font-size:12px;"></span></div>'
    ),
    (
        '''          ? '<button class="btn btn-primary btn-block" onclick="handleSendMessageClick()"><i class="fa-solid fa-comment-dots"></i> 채팅창으로 이동하기</button>''' + "'",
        '''          ? '<button class="btn btn-secondary btn-block" style="color:var(--primary);" onclick="handleSendMessageClick()"><i class="fa-solid fa-comment-dots"></i> 채팅창으로 이동하기</button>''' + "'"
    ),
    (
        '''<div class="chat-row-nick">${escapeHtml(meta.title||'')} <span style="color:var(--text-muted);font-weight:400;">${(meta.memberIds||[]).length}</span></div>''',
        '''<div class="chat-row-nick">${escapeHtml(meta.title||'')} <span style="color:var(--text-muted);font-weight:400;">${(meta.memberIds||[]).length}</span>${room.muted?' <i class="fa-solid fa-bell-slash" style="color:var(--text-muted);font-size:11px;"></i>':''}</div>'''
    ),
    (
        '''        <span onclick="event.stopPropagation();openProfileDetailScreen('${target.id}')" style="cursor:pointer;display:inline-block;">${avatarHtmlFor(target,'avatar-sm')}</span>
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div>''',
        '''        <span onclick="event.stopPropagation();openProfileDetailScreen('${target.id}')" style="cursor:pointer;display:inline-block;">${avatarHtmlFor(target,'avatar-sm')}</span>
        <div class="chat-row-text">
          <div class="chat-row-nick">${escapeHtml(target.nickname||'')}${room.muted?' <i class="fa-solid fa-bell-slash" style="color:var(--text-muted);font-size:11px;"></i>':''}</div>'''
    ),
    (
        '''  document.getElementById('groupChatTitle').textContent = (cached && cached.meta && cached.meta.title) || '단체채팅방';
  const area = document.getElementById('groupChatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';''',
        '''  document.getElementById('groupChatTitle').textContent = (cached && cached.meta && cached.meta.title) || '단체채팅방';
  document.getElementById('groupChatMemberCount').textContent = (cached && cached.meta && cached.meta.memberIds) ? cached.meta.memberIds.length : '';
  const area = document.getElementById('groupChatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';'''
    ),
    (
        '''    if (res && res.success){
      activeGroupRoomMeta = res;
      if (activeGroupRoomId===roomId && (res.blockedUserIds||[]).length){''',
        '''    if (res && res.success){
      activeGroupRoomMeta = res;
      if (activeGroupRoomId===roomId && res.meta && res.meta.memberIds){
        document.getElementById('groupChatMemberCount').textContent = res.meta.memberIds.length;
      }
      if (activeGroupRoomId===roomId && (res.blockedUserIds||[]).length){'''
    ),
    (
        '''socket.on('group:member_joined', ()=>{ if (activeGroupRoomId) socket.emit('group:info', {roomId:activeGroupRoomId}, (res)=>{ if (res && res.success){ activeGroupRoomMeta = res; if (document.getElementById('groupInfoScreen').classList.contains('active')) renderGroupInfoScreen(); } }); });
socket.on('group:member_left', ()=>{ if (activeGroupRoomId) socket.emit('group:info', {roomId:activeGroupRoomId}, (res)=>{ if (res && res.success){ activeGroupRoomMeta = res; if (document.getElementById('groupInfoScreen').classList.contains('active')) renderGroupInfoScreen(); } }); });''',
        '''socket.on('group:member_joined', ()=>{ if (activeGroupRoomId) socket.emit('group:info', {roomId:activeGroupRoomId}, (res)=>{ if (res && res.success){ activeGroupRoomMeta = res; if (res.meta && res.meta.memberIds) document.getElementById('groupChatMemberCount').textContent = res.meta.memberIds.length; if (document.getElementById('groupInfoScreen').classList.contains('active')) renderGroupInfoScreen(); } }); });
socket.on('group:member_left', ()=>{ if (activeGroupRoomId) socket.emit('group:info', {roomId:activeGroupRoomId}, (res)=>{ if (res && res.success){ activeGroupRoomMeta = res; if (res.meta && res.meta.memberIds) document.getElementById('groupChatMemberCount').textContent = res.meta.memberIds.length; if (document.getElementById('groupInfoScreen').classList.contains('active')) renderGroupInfoScreen(); } }); });'''
    ),
]

server_replacements = [
    (
        '''        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: { senderId: 'system', text: systemMessageText, timestamp: Date.now() } });
      }
    }
    await db.ref(`users/${userId}`).remove();
  }''',
        '''        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: { senderId: 'system', text: systemMessageText, timestamp: Date.now() } });
      }
    }
    // 0-51: 탈퇴한 유저의 흔적(팔로우/팔로워/프로필좋아요)이 다른 유저들의 배열에 그대로 남아
    // "밖에서 보이는 팔로잉 숫자"와 "실제 목록에 뜨는 인원수"가 어긋나는 버그가 있었음 -> 탈퇴 시 전체 유저를 훑어 정리
    const usersSnap = await db.ref('users').once('value');
    const allUsers = usersSnap.val() || {};
    for (const uid of Object.keys(allUsers)) {
      if (uid === userId) continue;
      const u = allUsers[uid];
      const updates = {};
      if (Array.isArray(u.followingIds) && u.followingIds.includes(userId)) updates.followingIds = u.followingIds.filter(id => id !== userId);
      if (Array.isArray(u.followerIds) && u.followerIds.includes(userId)) updates.followerIds = u.followerIds.filter(id => id !== userId);
      if (Array.isArray(u.profileLikedBy) && u.profileLikedBy.includes(userId)) updates.profileLikedBy = u.profileLikedBy.filter(id => id !== userId);
      if (Object.keys(updates).length) await db.ref(`users/${uid}`).update(updates);
    }
    await db.ref(`users/${userId}`).remove();
  }'''
    ),
    (
        '''      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      const postsSnap = await db.ref('posts').once('value');
      const allPosts = postsSnap.val() || {};
      for (const pid of Object.keys(allPosts)) {
        if (allPosts[pid].authorId === userId) await deletePostDb(pid);
      }

      const chatsSnap = await db.ref('chats').once('value');
      const allChats = chatsSnap.val() || {};
      for (const roomId of Object.keys(allChats)) {
        const room = allChats[roomId];
        if (room.userIds && room.userIds.includes(userId)) {
          await addMessage(roomId, { senderId: 'system', text: '탈퇴한 사용자입니다.', timestamp: Date.now() });
          await saveRoomMeta(roomId, { withdrawnAt: Date.now() });
          const otherId = room.userIds.find(id => id !== userId);
          const sId = userToSocket[otherId];
          if (sId) io.to(sId).emit('chat:new_message', { roomId, message: { senderId: 'system', text: '탈퇴한 사용자입니다.', timestamp: Date.now() } });
        }
      }

      await db.ref(`users/${userId}`).remove();
      delete socketToUser[socket.id];''',
        '''      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      await forceWithdrawUserAccount(userId, '탈퇴한 사용자입니다.');
      delete socketToUser[socket.id];'''
    ),
]

apply(INDEX_HTML, index_replacements)
print("✅ public/index.html 패치 적용 완료")
apply(SERVER_JS, server_replacements)
print("✅ server.js 패치 적용 완료")
print("✅ 0-51 패치 전체 완료")