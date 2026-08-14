import os, sys

def find(rel):
    for base in ['.', 'malbeot-app']:
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            return p
    print(f"❌ {rel} 를 찾을 수 없습니다. 현재 위치: {os.getcwd()}")
    sys.exit(1)

SERVER = find('server.js')
CLIENT = find('public/index.html')
print(f"server.js: {SERVER}")
print(f"index.html: {CLIENT}")

def apply(path, edits):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new, label in edits:
        cnt = content.count(old)
        if cnt != 1:
            print(f"❌ [{path}] '{label}' 매칭 실패 (발견 {cnt}회, 1회여야 함) — 이미 패치됐거나 코드가 달라졌을 수 있습니다.")
            sys.exit(1)
        content = content.replace(old, new)
        print(f"  ✔ {label}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

server_edits = [
(
"""  // 신고 처리: action은 'delete_post'|'ban_user'|'delete_room'|'complete_only' 중 하나
  // (채팅 메시지 1개 단위 삭제는 롱프레스 신고 기능(messageId 확보) 구현 후 추가 예정 — 현재는 방 단위만 가능)""",
"""  // 신고 처리: action은 'delete_post'|'ban_user'|'delete_room'|'delete_message'|'complete_only' 중 하나
  // 0-37: 채팅 메시지 1개 단위 삭제 구현 완료(messageId가 있는 신고는 방 전체가 아니라 해당 메시지만 삭제 가능)""",
"server.js: 주석 갱신"
),
(
"""      } else if (action === 'delete_room' && report.type === 'chat') {
        await deleteRoom(report.targetId);
      } else if (action === 'delete_comment' && report.type === 'comment') {""",
"""      } else if (action === 'delete_room' && report.type === 'chat') {
        await deleteRoom(report.targetId);
      } else if (action === 'delete_message' && report.type === 'chat' && report.messageId) {
        // 0-37: 방 전체가 아니라 신고된 메시지 1개만 삭제(기존 '나에게만/모두에게 삭제'와 동일한 소프트 삭제 방식 재사용)
        await db.ref(`chats/${report.targetId}/messages/${report.messageId}`).update({ deletedForEveryone: true, text: '', data: null });
        const msgRoom = await getRoom(report.targetId);
        if (msgRoom && msgRoom.userIds) {
          msgRoom.userIds.forEach(uid => {
            const sId = userToSocket[uid];
            if (sId) io.to(sId).emit('chat:message_deleted', { roomId: report.targetId, messageId: report.messageId, mode: 'everyone' });
          });
        }
      } else if (action === 'delete_comment' && report.type === 'comment') {""",
"server.js: admin:reports:resolve 에 delete_message 액션 추가"
),
(
"""      const ref = db.ref('reports').push();
      const report = {
        id: ref.key,
        type: targetContext.type,
        targetId: targetContext.id,
        reporterUid: userId || null,
        category,
        status: 'pending',
        createdAt: Date.now()
      };
      await ref.set(report);""",
"""      const ref = db.ref('reports').push();
      const report = {
        id: ref.key,
        type: targetContext.type,
        targetId: targetContext.id,
        reporterUid: userId || null,
        category,
        status: 'pending',
        createdAt: Date.now()
      };
      // 0-37: 채팅 메시지 롱프레스 신고는 messageId를 함께 보내 메시지 단위로 특정함
      if (targetContext.messageId) {
        report.messageId = targetContext.messageId;
        if (targetContext.messagePreview) report.messagePreview = targetContext.messagePreview;
      }
      await ref.set(report);""",
"server.js: user:report 핸들러에 messageId 저장 추가"
),
(
"""        } else if (r.type === 'chat') {
          targetLabel = `채팅방 ${r.targetId}`;
          const room = await getRoom(r.targetId);
          const otherId = room && room.userIds ? room.userIds.find(uid => uid !== r.reporterUid) : null;
          accusedNickname = otherId && users[otherId] ? users[otherId].nickname : '(알 수 없음)';
        } else if (r.type === 'comment') {""",
"""        } else if (r.type === 'chat') {
          const room = await getRoom(r.targetId);
          const otherId = room && room.userIds ? room.userIds.find(uid => uid !== r.reporterUid) : null;
          accusedNickname = otherId && users[otherId] ? users[otherId].nickname : '(알 수 없음)';
          if (r.messageId) {
            // 0-37: 메시지 단위 신고는 방 이름 대신 신고된 메시지 내용을 미리보기로 보여줌
            const msg = room && room.messages && room.messages[r.messageId];
            targetLabel = msg
              ? (msg.deletedForEveryone ? '(이미 삭제된 메시지)' : (msg.type === 'image' ? '(이미지)' : (msg.text || '').slice(0, 40)))
              : (r.messagePreview || '(삭제된 메시지)');
          } else {
            targetLabel = `채팅방 ${r.targetId}`;
          }
        } else if (r.type === 'comment') {""",
"server.js: admin:reports:list 채팅 신고 미리보기 처리"
),
]
apply(SERVER, server_edits)

client_edits = [
(
"""function openBlockReportModal(type, id, authorId){ blockReportContext = {type, id: id||currentProfileUserId, authorId}; openModal('blockReportModal'); }""",
"""function openBlockReportModal(type, id, authorId){ blockReportContext = {type, id: id||currentProfileUserId, authorId}; openModal('blockReportModal'); }
// 0-37: 채팅 메시지 롱프레스 신고 - 방 전체가 아니라 메시지 1개(messageId)를 신고 대상으로 지정 (기존엔 이 함수가 정의돼있지 않아 신고 자체가 에러로 안 되던 버그였음)
function reportMessage(roomId, messageId, otherUserId, previewText){
  blockReportContext = { type:'chat', id: roomId, authorId: otherUserId, messageId, messagePreview: (previewText||'').slice(0,60) };
  openReportCategoryModal();
}""",
"index.html: reportMessage() 함수 신규 정의(버그 수정)"
),
(
"""      } else if (r.type==='chat'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_room')">채팅방 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;color:#fff;background:var(--danger,#ef4444);" onclick="confirmForceWithdraw('${r.id}')">강제탈퇴</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='comment'){""",
"""      } else if (r.type==='chat'){
        const chatDelBtn = r.messageId
          ? `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_message')">메시지 삭제</button>`
          : `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_room')">채팅방 삭제</button>`;
        actions = `${chatDelBtn}<button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;color:#fff;background:var(--danger,#ef4444);" onclick="confirmForceWithdraw('${r.id}')">강제탈퇴</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='comment'){""",
"index.html: 관리자 신고목록 - 메시지 신고면 '메시지 삭제' 버튼으로 교체"
),
(
"""      <div style="display:flex;justify-content:space-between;"><b>${escapeHtml(ADMIN_REPORT_TYPE_LABEL[r.type]||r.type)} · ${escapeHtml(r.category||'')}</b><span style="font-size:11px;color:var(--text-muted);">${r.status==='pending'?'미처리':(r.status==='resolved'?'처리완료':r.status)}</span></div>""",
"""      <div style="display:flex;justify-content:space-between;"><b>${escapeHtml((ADMIN_REPORT_TYPE_LABEL[r.type]||r.type) + (r.type==='chat' && r.messageId ? '(메시지)' : ''))} · ${escapeHtml(r.category||'')}</b><span style="font-size:11px;color:var(--text-muted);">${r.status==='pending'?'미처리':(r.status==='resolved'?'처리완료':r.status)}</span></div>""",
"index.html: 신고목록 라벨에 (메시지) 표시 추가"
),
]
apply(CLIENT, client_edits)

print("\n✅ 0-37 패치 완료: 채팅 메시지 신고 시 메시지 단위 삭제 구현 + reportMessage 미정의 버그 수정")
print("다음 명령으로 커밋/푸시하세요:")
print('  git add -A && git commit -m "0-37: 채팅 메시지 신고 시 메시지 단위 삭제 구현 + reportMessage 미정의 버그 수정" && git push')