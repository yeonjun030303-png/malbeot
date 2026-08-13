# ===== server.js =====
path = "server.js"
with open(path, encoding="utf-8") as f:
    content = f.read()

old_const = """const WARNING_MESSAGE = '다른 사용자와의 대화(게시물, 댓글) 등 신고를 접수받아 검토한 결과, 부적절한 단어나 상대방이 불쾌할 수 있는 언행을 하여 경고했습니다. 다음에는 주의해 주세요.';"""
new_const = old_const + """
// 0-25: 관리자가 신고 처리 화면에서 수동으로 강제탈퇴시킬 때 쓰는 메시지(자동 임계값 처리는 하지 않음 - 관리자 판단으로만 실행)
const FORCE_WITHDRAW_MESSAGE = '신고 접수 내용을 검토한 결과, 이용약관 위반으로 계정이 강제 탈퇴 처리되었습니다. 재가입은 가능하나, 반복될 경우 재가입이 제한될 수 있습니다.';"""
assert content.count(old_const) == 1, "const count=%d" % content.count(old_const)
content = content.replace(old_const, new_const, 1)

old_withdraw_handler_marker = """  socket.on('account:withdraw', async (data, cb) => {"""
assert content.count(old_withdraw_handler_marker) == 1, "marker count=%d" % content.count(old_withdraw_handler_marker)

helper_fn = """  // 0-25: 관리자 강제탈퇴용 - account:withdraw와 동일한 삭제 로직(게시글 삭제, 채팅방 탈퇴 표시, 계정 제거)을 재사용
  async function forceWithdrawUserAccount(userId, systemMessageText) {
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
        await addMessage(roomId, { senderId: 'system', text: systemMessageText, timestamp: Date.now() });
        await saveRoomMeta(roomId, { withdrawnAt: Date.now() });
        const otherId = room.userIds.find(id => id !== userId);
        const sId = userToSocket[otherId];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: { senderId: 'system', text: systemMessageText, timestamp: Date.now() } });
      }
    }
    await db.ref(`users/${userId}`).remove();
  }

"""
content = content.replace(old_withdraw_handler_marker, helper_fn + old_withdraw_handler_marker, 1)

old_warn_branch = """      } else if (action === 'warn_user') {
        const accusedId = await getAccusedUserId(report);
        const target = accusedId ? await getUser(accusedId) : null;
        if (target) {
          target.warnings = target.warnings || [];
          target.warnings.push({ reason: report.category || '', at: Date.now() });
          target.pendingWarningNotify = { at: Date.now(), notified: false };
          const sId = userToSocket[target.id];
          if (sId) { io.to(sId).emit('account:warned', { message: WARNING_MESSAGE }); target.pendingWarningNotify.notified = true; }
          // 앱을 꺼놨거나 로그아웃 상태여도 확실히 알 수 있도록 웹푸시도 함께 발송(문자X, 인앱 알림창 성격의 푸시)
          else sendWebPush(target.id, { title: '경고 안내', body: WARNING_MESSAGE, type: 'warning' });
          await saveUser(target);
        }
      }"""
new_warn_branch = """      } else if (action === 'warn_user') {
        const accusedId = await getAccusedUserId(report);
        const target = accusedId ? await getUser(accusedId) : null;
        if (target) {
          target.warnings = target.warnings || [];
          target.warnings.push({ reason: report.category || '', at: Date.now() });
          target.pendingWarningNotify = { at: Date.now(), notified: false };
          const sId = userToSocket[target.id];
          if (sId) { io.to(sId).emit('account:warned', { message: WARNING_MESSAGE }); target.pendingWarningNotify.notified = true; }
          // 앱을 꺼놨거나 로그아웃 상태여도 확실히 알 수 있도록 웹푸시도 함께 발송(문자X, 인앱 알림창 성격의 푸시)
          else sendWebPush(target.id, { title: '경고 안내', body: WARNING_MESSAGE, type: 'warning' });
          await saveUser(target);
        }
      } else if (action === 'force_withdraw_user') {
        // 0-25: 경고 누적 자동처리는 하지 않고, 관리자가 신고 화면에서 수동으로 강제탈퇴시킬 때만 실행됨
        const accusedId = await getAccusedUserId(report);
        if (accusedId) {
          const sId = userToSocket[accusedId];
          if (sId) { io.to(sId).emit('account:force_withdrawn', { message: FORCE_WITHDRAW_MESSAGE }); delete userToSocket[accusedId]; }
          else sendWebPush(accusedId, { title: '계정 탈퇴 안내', body: FORCE_WITHDRAW_MESSAGE, type: 'force_withdrawn' });
          await forceWithdrawUserAccount(accusedId, '이용약관 위반으로 강제 탈퇴 처리된 사용자입니다.');
          broadcastUsers();
          broadcastPosts();
        }
      }"""
assert content.count(old_warn_branch) == 1, "warn_branch count=%d" % content.count(old_warn_branch)
content = content.replace(old_warn_branch, new_warn_branch, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ [1/3] server.js — 관리자 수동 강제탈퇴(force_withdraw_user) 액션 추가 완료")

# ===== public/index.html =====
path = "public/index.html"
with open(path, encoding="utf-8") as f:
    content = f.read()

old_listener = """socket.on('account:warned', (data)=>{
  if (!currentUser) return;
  showWarningModal(data && data.message);
});"""
new_listener = old_listener + """
// 0-25: 관리자가 신고 처리에서 강제탈퇴시켰을 때 - 확인 누르면 세션 정리 후 로그인 화면으로 리로드
socket.on('account:force_withdrawn', (data)=>{
  document.getElementById('warningModalText').textContent = (data && data.message) || '이용약관 위반으로 계정이 강제 탈퇴 처리되었습니다.';
  openModal('warningModal');
  const btn = document.querySelector('#warningModal .btn-primary');
  if (btn) btn.onclick = ()=>{ closeModal('warningModal'); clearSession(); location.reload(); };
});"""
assert content.count(old_listener) == 1, "listener count=%d" % content.count(old_listener)
content = content.replace(old_listener, new_listener, 1)

old_actions = """      if (r.type==='post'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_post')">게시글 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='user'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','ban_user')">계정 정지</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='chat'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_room')">채팅방 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='comment'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_comment')">댓글 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      }"""
force_btn = """<button class="btn btn-secondary" style="flex:1;color:#fff;background:var(--danger,#ef4444);" onclick="confirmForceWithdraw('${r.id}')">강제탈퇴</button>"""
new_actions = """      if (r.type==='post'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_post')">게시글 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button>""" + force_btn + """<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='user'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','ban_user')">계정 정지</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button>""" + force_btn + """<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='chat'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_room')">채팅방 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button>""" + force_btn + """<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='comment'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_comment')">댓글 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button>""" + force_btn + """<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      }"""
assert content.count(old_actions) == 1, "actions count=%d" % content.count(old_actions)
content = content.replace(old_actions, new_actions, 1)

old_resolve_fn = """function resolveAdminReport(reportId, action){
  socket.emit('admin:reports:resolve', {reportId, action}, (res)=>{
    if (res && res.success) loadAdminReports();
    else showMiniAlert('처리 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
}"""
new_resolve_fn = old_resolve_fn + """
// 0-25: 강제탈퇴는 되돌릴 수 없으므로 실행 전 반드시 확인창을 거침(자동 임계값 처리 없이 관리자 수동 판단으로만 동작)
function confirmForceWithdraw(reportId){
  showMiniAlert('해당 유저를 강제탈퇴 처리하시겠습니까? 게시글이 모두 삭제되고 계정이 즉시 탈퇴 처리되며, 되돌릴 수 없습니다.', [
    {label:'취소', primary:false},
    {label:'강제탈퇴', primary:true, danger:true, onClick:()=>resolveAdminReport(reportId,'force_withdraw_user')}
  ]);
}"""
assert content.count(old_resolve_fn) == 1, "resolve_fn count=%d" % content.count(old_resolve_fn)
content = content.replace(old_resolve_fn, new_resolve_fn, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ [2/3] public/index.html — 관리자 신고 화면에 강제탈퇴 버튼+확인창+강제로그아웃 처리 추가 완료")

# ===== refund-policy.html =====
path = "public/refund-policy.html"
with open(path, encoding="utf-8") as f:
    content = f.read()

old_li = """        <li>동일 이용자가 결제·환불을 반복해 서비스를 부당하게 이용하는 것으로 판단되는 경우, 이후 결제 및 서비스 이용이 제한될 수 있어요.</li>"""
new_li = old_li + """
        <li>신고 접수 내용을 검토한 결과 이용약관 위반으로 계정이 강제 탈퇴 처리된 경우 — 약관 위반에 따른 조치이므로 잔여 쌀에 대한 환불이 제공되지 않아요.</li>"""
assert content.count(old_li) == 1, "li count=%d" % content.count(old_li)
content = content.replace(old_li, new_li, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ [3/3] refund-policy.html — 신고 강제탈퇴시 환불불가 조항 추가 완료")
print("0-25 패치 전체 완료")