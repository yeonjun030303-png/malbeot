#!/usr/bin/env python3
# 0-10: 차단/신고 필터링을 커뮤니티 전체(글/댓글/투표)로 강화
#
# 실사 결과 발견한 3가지 실제 공백을 메움:
#  A) 투표(pollOptions) 텍스트는 게시글 본문과 달리 금칙어 검사가 전혀 없었음 -> 검사 추가
#  B) 댓글 신고가 "댓글"이 아니라 "프로필(작성자)" 신고로 들어가서 관리자가 어떤 댓글인지 특정 불가 ->
#     신고 유형에 'comment' 신설, 관리자 대시보드에 "댓글" 탭 추가, 댓글 단위 삭제 액션 추가
#  C) 전역 차단(user.blockedUserIds)이 실제로는 1:1 채팅 시작 차단에만 쓰이고 커뮤니티 피드/댓글에는
#     전혀 반영되지 않았음 -> 게시글 목록에서 차단 유저 글 제외, 댓글은 "차단한 사용자의 댓글입니다"로 대체
#
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_moderation_expand.py

import sys

def patch(path, replacements):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    for old, new, label in replacements:
        count = content.count(old)
        if count != 1:
            print(f"[실패] {path}: '{label}' 패턴이 {count}번 발견됨 (1번이어야 함) -> {old[:60]!r}")
            sys.exit(1)
        content = content.replace(old, new)
        print(f"[적용] {path} - {label}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[완료] {path} 저장\n")

server_replacements = [
# A-1) posts:create - 투표 옵션도 금칙어 검사 대상에 포함되도록 순서 재구성
(
"""      const bannedWord = containsBannedWord(data.content);
      if (bannedWord && data.confirmed !== true) return cb({ success: false, needsConfirm: true });
      let imageBlocked = false;
      if (data.photo) {
        const nsfwResult = await checkImageNsfw(data.photo);
        imageBlocked = nsfwResult.isNsfw;
      }
      const isFiltered = bannedWord || imageBlocked;

      const todayStr = new Date().toISOString().slice(0, 10);
      let earned = false;
      if (user.lastPostDate !== todayStr) { user.points += 50; user.lastPostDate = todayStr; earned = true; }
      await saveUser(user);
      const category = data.category === 'vote' ? 'vote' : 'normal';
      let pollOptions = null, pollVotes = null;
      if (category !== 'normal') {
        const rawOptions = Array.isArray(data.pollOptions) ? data.pollOptions.map(t => (t || '').trim()).filter(Boolean) : [];
        const min = 2, max = VOTE_MAX_OPTIONS;
        if (rawOptions.length < min || rawOptions.length > max) return cb({ success: false, message: '투표 항목 개수를 확인해주세요.' });
        pollOptions = rawOptions.slice(0, max).map((text, i) => ({ id: 'o' + i, text: text.slice(0, 30) }));
        pollVotes = {};
      }""",
"""      // 투표 항목 텍스트도 게시글 본문과 동일하게 금칙어 검사 대상에 포함시키기 위해
      // pollOptions 파싱을 먼저 수행한 뒤 content + 옵션 전체를 합쳐서 한 번에 필터링함.
      const category = data.category === 'vote' ? 'vote' : 'normal';
      let rawOptions = [];
      if (category !== 'normal') {
        rawOptions = Array.isArray(data.pollOptions) ? data.pollOptions.map(t => (t || '').trim()).filter(Boolean) : [];
        const min = 2, max = VOTE_MAX_OPTIONS;
        if (rawOptions.length < min || rawOptions.length > max) return cb({ success: false, message: '투표 항목 개수를 확인해주세요.' });
      }
      const bannedWord = containsBannedWord(data.content) || rawOptions.some(t => containsBannedWord(t));
      if (bannedWord && data.confirmed !== true) return cb({ success: false, needsConfirm: true });
      let imageBlocked = false;
      if (data.photo) {
        const nsfwResult = await checkImageNsfw(data.photo);
        imageBlocked = nsfwResult.isNsfw;
      }
      const isFiltered = bannedWord || imageBlocked;

      const todayStr = new Date().toISOString().slice(0, 10);
      let earned = false;
      if (user.lastPostDate !== todayStr) { user.points += 50; user.lastPostDate = todayStr; earned = true; }
      await saveUser(user);
      let pollOptions = null, pollVotes = null;
      if (category !== 'normal') {
        pollOptions = rawOptions.slice(0, VOTE_MAX_OPTIONS).map((text, i) => ({ id: 'o' + i, text: text.slice(0, 30) }));
        pollVotes = {};
      }""",
"A) posts:create 투표 옵션 금칙어 검사 추가"
),
# C-1) posts:get_list - 내가 차단한 유저의 글은 목록에서 제외
(
"""      const myUserId = socketToUser[socket.id];
      const myUser = myUserId ? await getUser(myUserId) : null;
      list = sortPostsByType(list, filters.sort, myUser && myUser.region);
      cb({ success: true, posts: list });""",
"""      const myUserId = socketToUser[socket.id];
      const myUser = myUserId ? await getUser(myUserId) : null;
      if (myUser && myUser.blockedUserIds && myUser.blockedUserIds.length) {
        list = list.filter(p => !myUser.blockedUserIds.includes(p.authorId));
      }
      list = sortPostsByType(list, filters.sort, myUser && myUser.region);
      cb({ success: true, posts: list });""",
"C) posts:get_list 차단 유저 글 제외"
),
# B-1) getAccusedUserId - 댓글 신고 시 피신고자(댓글 작성자) 찾기
(
"""  } else if (report.type === 'chat') {
    const room = await getRoom(report.targetId);
    return room && room.userIds ? room.userIds.find(uid => uid !== report.reporterUid) : null;
  }
  return null;
}""",
"""  } else if (report.type === 'chat') {
    const room = await getRoom(report.targetId);
    return room && room.userIds ? room.userIds.find(uid => uid !== report.reporterUid) : null;
  } else if (report.type === 'comment') {
    const [postId, commentId] = (report.targetId || '').split('::');
    const p = postId ? await getPost(postId) : null;
    const c = p && p.comments && p.comments[commentId];
    return c ? c.authorId : null;
  }
  return null;
}""",
"B) getAccusedUserId에 댓글 유형 추가"
),
# B-2) admin:reports:list - 댓글 신고 표시 + counts에 comment 추가
(
"""        } else if (r.type === 'chat') {
          targetLabel = `채팅방 ${r.targetId}`;
          const room = await getRoom(r.targetId);
          const otherId = room && room.userIds ? room.userIds.find(uid => uid !== r.reporterUid) : null;
          accusedNickname = otherId && users[otherId] ? users[otherId].nickname : '(알 수 없음)';
        }
        const reporter = users[r.reporterUid];
        return { ...r, targetLabel, accusedNickname, reporterNickname: reporter ? reporter.nickname : '(알 수 없음)' };
      }));
      const counts = { post: 0, user: 0, chat: 0 };""",
"""        } else if (r.type === 'chat') {
          targetLabel = `채팅방 ${r.targetId}`;
          const room = await getRoom(r.targetId);
          const otherId = room && room.userIds ? room.userIds.find(uid => uid !== r.reporterUid) : null;
          accusedNickname = otherId && users[otherId] ? users[otherId].nickname : '(알 수 없음)';
        } else if (r.type === 'comment') {
          const [postId, commentId] = (r.targetId || '').split('::');
          const p = postId ? await getPost(postId) : null;
          const c = p && p.comments && p.comments[commentId];
          targetLabel = c ? (c.content || '').slice(0, 40) : '(삭제된 댓글)';
          accusedNickname = c && users[c.authorId] ? users[c.authorId].nickname : '(탈퇴한 사용자)';
        }
        const reporter = users[r.reporterUid];
        return { ...r, targetLabel, accusedNickname, reporterNickname: reporter ? reporter.nickname : '(알 수 없음)' };
      }));
      const counts = { post: 0, user: 0, chat: 0, comment: 0 };""",
"B) admin:reports:list 댓글 표시 + 카운트"
),
# B-3) admin:reports:resolve - delete_comment 액션 추가
(
"""      } else if (action === 'delete_room' && report.type === 'chat') {
        await deleteRoom(report.targetId);
      } else if (action === 'warn_user') {""",
"""      } else if (action === 'delete_room' && report.type === 'chat') {
        await deleteRoom(report.targetId);
      } else if (action === 'delete_comment' && report.type === 'comment') {
        const [postId, commentId] = (report.targetId || '').split('::');
        const post = postId ? await getPost(postId) : null;
        const c = post && post.comments && post.comments[commentId];
        if (c) {
          c.deleted = true;
          c.deletedAt = Date.now();
          c.deletedByAdmin = true;
          await savePost(post);
          broadcastPosts();
        }
      } else if (action === 'warn_user') {""",
"B) admin:reports:resolve 댓글 삭제 액션 추가"
),
]

html_replacements = [
# B-4) 댓글 신고 버튼: 프로필 신고 -> 댓글 단위 신고로 변경 (부모 댓글)
(
"""    : (currentUser ? `<button class=\"post-action-btn\" style=\"padding:2px 6px;\" onclick=\"openBlockReportModal('user','${c.authorId}')\"><i class=\"fa-solid fa-ellipsis\"></i></button>` : '');""",
"""    : (currentUser ? `<button class=\"post-action-btn\" style=\"padding:2px 6px;\" onclick=\"openBlockReportModal('comment','${p.id}::${c.id}','${c.authorId}')\"><i class=\"fa-solid fa-ellipsis\"></i></button>` : '');""",
"B) 부모 댓글 신고 버튼을 댓글 단위 신고로 변경"
),
# B-5) 댓글 신고 버튼: 답글(reply)도 동일하게 변경
(
"""      : (currentUser ? `<button class=\"post-action-btn\" style=\"padding:2px 6px;\" onclick=\"openBlockReportModal('user','${r.authorId}')\"><i class=\"fa-solid fa-ellipsis\"></i></button>` : '');""",
"""      : (currentUser ? `<button class=\"post-action-btn\" style=\"padding:2px 6px;\" onclick=\"openBlockReportModal('comment','${p.id}::${r.id}','${r.authorId}')\"><i class=\"fa-solid fa-ellipsis\"></i></button>` : '');""",
"B) 답글 신고 버튼을 댓글 단위 신고로 변경"
),
# B-6) openBlockReportModal / handleBlockAction - authorId 파라미터 지원
(
"""function openBlockReportModal(type, id){ blockReportContext = {type, id: id||currentProfileUserId}; openModal('blockReportModal'); }
function handleBlockAction(){
  closeModal('blockReportModal');
  if (!confirm('이 사용자를 차단하시겠습니까? 차단하면 서로 연락을 주고받을 수 없습니다.')) return;
  let targetId = blockReportContext.id;
  if (blockReportContext.type==='post' && currentPostCache) targetId = currentPostCache.authorId;
  socket.emit('user:block', targetId, ()=>{""",
"""function openBlockReportModal(type, id, authorId){ blockReportContext = {type, id: id||currentProfileUserId, authorId}; openModal('blockReportModal'); }
function handleBlockAction(){
  closeModal('blockReportModal');
  if (!confirm('이 사용자를 차단하시겠습니까? 차단하면 서로 연락을 주고받을 수 없습니다.')) return;
  let targetId = blockReportContext.id;
  if (blockReportContext.type==='post' && currentPostCache) targetId = currentPostCache.authorId;
  if (blockReportContext.type==='comment' && blockReportContext.authorId) targetId = blockReportContext.authorId;
  socket.emit('user:block', targetId, ()=>{""",
"B) 댓글 신고에서 '차단'을 눌렀을 때 댓글 작성자를 차단하도록 처리"
),
# B-7) 관리자 대시보드 신고 탭에 "댓글" 탈리 박스 추가
(
"""          <div style="flex:1;text-align:center;padding:14px 0;border:1px solid var(--border-color);border-radius:10px;cursor:pointer;" onclick="filterAdminReports('chat')">
            <div id="adminTallyChat" style="font-size:22px;font-weight:700;">0</div>
            <div style="font-size:12px;color:var(--text-muted);">채팅</div>
          </div>
        </div>""",
"""          <div style="flex:1;text-align:center;padding:14px 0;border:1px solid var(--border-color);border-radius:10px;cursor:pointer;" onclick="filterAdminReports('chat')">
            <div id="adminTallyChat" style="font-size:22px;font-weight:700;">0</div>
            <div style="font-size:12px;color:var(--text-muted);">채팅</div>
          </div>
          <div style="flex:1;text-align:center;padding:14px 0;border:1px solid var(--border-color);border-radius:10px;cursor:pointer;" onclick="filterAdminReports('comment')">
            <div id="adminTallyComment" style="font-size:22px;font-weight:700;">0</div>
            <div style="font-size:12px;color:var(--text-muted);">댓글</div>
          </div>
        </div>""",
"B) 관리자 대시보드 '댓글' 탈리 박스 추가"
),
# B-8) loadAdminReports - comment 카운트 반영
(
"""    document.getElementById('adminTallyChat').textContent = res.counts.chat;
    renderAdminReports();""",
"""    document.getElementById('adminTallyChat').textContent = res.counts.chat;
    document.getElementById('adminTallyComment').textContent = res.counts.comment;
    renderAdminReports();""",
"B) 관리자 신고 로드 시 댓글 카운트 반영"
),
# B-9) 라벨 맵 + 처리 액션 버튼(댓글용) 추가
(
"""const ADMIN_REPORT_TYPE_LABEL = { post:'게시글', user:'프로필', chat:'채팅' };""",
"""const ADMIN_REPORT_TYPE_LABEL = { post:'게시글', user:'프로필', chat:'채팅', comment:'댓글' };""",
"B) 신고유형 라벨 맵에 댓글 추가"
),
(
"""      } else if (r.type==='chat'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_room')">채팅방 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      }""",
"""      } else if (r.type==='chat'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_room')">채팅방 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      } else if (r.type==='comment'){
        actions = `<button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','delete_comment')">댓글 삭제</button><button class="btn btn-secondary" style="flex:1;color:var(--danger);" onclick="resolveAdminReport('${r.id}','warn_user')">경고</button><button class="btn btn-secondary" style="flex:1;" onclick="resolveAdminReport('${r.id}','complete_only')">처리완료 표시만</button>`;
      }""",
"B) 댓글 신고 처리 액션 버튼(댓글삭제/경고/처리완료) 추가"
),
# C-2) 댓글 내용 렌더링: 차단한 사용자의 댓글이면 대체 문구 표시
(
"""function renderCommentContent(content, filtered, deleted, deletedByAdmin){
  if (filtered) return `<span style="color:var(--text-muted);">부적절한 댓글입니다.</span>`;
  if (deleted) return `<span style="color:var(--text-muted);">${deletedByAdmin ? '관리자에 의해 삭제된 댓글입니다.' : '삭제된 댓글입니다.'}</span>`;""",
"""function renderCommentContent(content, filtered, deleted, deletedByAdmin, blockedAuthor){
  if (blockedAuthor) return `<span style="color:var(--text-muted);">차단한 사용자의 댓글입니다.</span>`;
  if (filtered) return `<span style="color:var(--text-muted);">부적절한 댓글입니다.</span>`;
  if (deleted) return `<span style="color:var(--text-muted);">${deletedByAdmin ? '관리자에 의해 삭제된 댓글입니다.' : '삭제된 댓글입니다.'}</span>`;""",
"C) renderCommentContent에 차단 유저 대체 문구 분기 추가"
),
(
"""              <div style="font-size:13px;flex:1;min-width:0;">${renderCommentContent(r.content, r.filtered, r.deleted, r.deletedByAdmin)}</div>""",
"""              <div style="font-size:13px;flex:1;min-width:0;">${renderCommentContent(r.content, r.filtered, r.deleted, r.deletedByAdmin, currentUser && (currentUser.blockedUserIds||[]).includes(r.authorId))}</div>""",
"C) 답글 렌더링에 차단 여부 전달"
),
(
"""            <div style="font-size:13px;flex:1;min-width:0;">${renderCommentContent(c.content, c.filtered, c.deleted, c.deletedByAdmin)}</div>""",
"""            <div style="font-size:13px;flex:1;min-width:0;">${renderCommentContent(c.content, c.filtered, c.deleted, c.deletedByAdmin, currentUser && (currentUser.blockedUserIds||[]).includes(c.authorId))}</div>""",
"C) 최상위 댓글 렌더링에 차단 여부 전달"
),
]

patch('server.js', server_replacements)
patch('public/index.html', html_replacements)

print("다음 순서로 진행하세요:")
print("1) node -c server.js")
print("2) git add -A && git commit -m \"0-10: 차단/신고 필터링 강화 - 투표 금칙어 검사, 댓글 단위 신고/삭제, 커뮤니티 전역 차단 반영\"")
print("3) (모아뒀다가 원하실 때) git push")