# -*- coding: utf-8 -*-
"""
0-18: 신고 3회 이상 누적된 대상을 관리자모드 목록 최상단에 노출 + 경고 처리 시 오프라인 유저에게도 웹푸시 발송
실행 위치: malbeot 저장소 루트 (malbeot-app 폴더가 보이는 곳)
사용법: python3 patch_0_18_report_urgent_and_warn_push.py
"""
import os, sys

ROOT = os.getcwd()
APP = os.path.join(ROOT, "malbeot-app")
if not os.path.isdir(APP):
    print("!! malbeot-app 폴더를 찾을 수 없습니다. 저장소 루트에서 실행하세요."); sys.exit(1)

SERVER = os.path.join(APP, "server.js")
INDEX = os.path.join(APP, "public", "index.html")

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def write(p, s):
    with open(p, "w", encoding="utf-8") as f: f.write(s)

def replace_once(content, old, new, label, path):
    if new in content:
        print(f"   (건너뜀-이미적용됨) {label}")
        return content
    if old not in content:
        print(f"!! 패치 실패: {label} ({path}) — 원본 텍스트 못찾음"); sys.exit(1)
    if content.count(old) != 1:
        print(f"!! 패치실패 1개 아님({content.count(old)}개): {label} ({path})"); sys.exit(1)
    print(f"   적용: {label}")
    return content.replace(old, new)

# ==================== server.js ====================
s = read(SERVER)

s = replace_once(s,
"""  // ===================== 관리자 대시보드 =====================
  // 신고 목록 조회(게시글/프로필/채팅 전체) + 종류별 미처리(pending) 개수 집계
  socket.on('admin:reports:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const snap = await db.ref('reports').once('value');
      const all = snap.val() || {};
      const list = Object.values(all).sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));""",
"""  // ===================== 관리자 대시보드 =====================
  // 같은 대상(type+targetId)에 대해 미처리 신고가 이 횟수 이상 누적되면 관리자 목록 최상단에 강조 노출함
  const URGENT_REPORT_THRESHOLD = 3;
  // 신고 목록 조회(게시글/프로필/채팅 전체) + 종류별 미처리(pending) 개수 집계
  socket.on('admin:reports:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const snap = await db.ref('reports').once('value');
      const all = snap.val() || {};
      // 같은 대상(type::targetId)에 미처리 신고가 몇 건 쌓였는지 먼저 집계
      const pendingCountByTarget = {};
      Object.values(all).forEach(r => {
        if (r.status !== 'pending') return;
        const key = `${r.type}::${r.targetId}`;
        pendingCountByTarget[key] = (pendingCountByTarget[key] || 0) + 1;
      });
      // 누적 신고 많은 대상(내림차순) 우선, 그다음 최신순 정렬
      const list = Object.values(all).sort((a, b) => {
        const ac = pendingCountByTarget[`${a.type}::${a.targetId}`] || 0;
        const bc = pendingCountByTarget[`${b.type}::${b.targetId}`] || 0;
        if (bc !== ac) return bc - ac;
        return (b.createdAt || 0) - (a.createdAt || 0);
      });""",
    "admin:reports:list 신고 누적 집계+정렬 추가", SERVER)

s = replace_once(s,
"""        const reporter = users[r.reporterUid];
        return { ...r, targetLabel, accusedNickname, reporterNickname: reporter ? reporter.nickname : '(알 수 없음)' };
      }));""",
"""        const reporter = users[r.reporterUid];
        const sameTargetPendingCount = pendingCountByTarget[`${r.type}::${r.targetId}`] || 0;
        return { ...r, targetLabel, accusedNickname, reporterNickname: reporter ? reporter.nickname : '(알 수 없음)', sameTargetPendingCount, isUrgent: sameTargetPendingCount >= URGENT_REPORT_THRESHOLD };
      }));""",
    "신고 항목에 누적건수/긴급여부 필드 추가", SERVER)

s = replace_once(s,
"""      } else if (action === 'warn_user') {
        const accusedId = await getAccusedUserId(report);
        const target = accusedId ? await getUser(accusedId) : null;
        if (target) {
          target.warnings = target.warnings || [];
          target.warnings.push({ reason: report.category || '', at: Date.now() });
          target.pendingWarningNotify = { at: Date.now(), notified: false };
          const sId = userToSocket[target.id];
          if (sId) { io.to(sId).emit('account:warned', { message: WARNING_MESSAGE }); target.pendingWarningNotify.notified = true; }
          await saveUser(target);
        }
      }""",
"""      } else if (action === 'warn_user') {
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
      }""",
    "경고 처리 시 오프라인 유저 웹푸시 발송", SERVER)

write(SERVER, s)

# ==================== public/index.html ====================
h = read(INDEX)

h = replace_once(h,
"""    return `<div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
      <div style="display:flex;justify-content:space-between;"><b>${escapeHtml(ADMIN_REPORT_TYPE_LABEL[r.type]||r.type)} · ${escapeHtml(r.category||'')}</b><span style="font-size:11px;color:var(--text-muted);">${r.status==='pending'?'미처리':(r.status==='resolved'?'처리완료':r.status)}</span></div>""",
"""    return `<div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;${r.isUrgent?'border:1.5px solid var(--danger);background:rgba(220,53,69,0.06);':''}">
      <div style="display:flex;justify-content:space-between;"><b>${escapeHtml(ADMIN_REPORT_TYPE_LABEL[r.type]||r.type)} · ${escapeHtml(r.category||'')}</b><span style="font-size:11px;color:var(--text-muted);">${r.status==='pending'?'미처리':(r.status==='resolved'?'처리완료':r.status)}</span></div>
      ${r.isUrgent?`<div style="font-size:11px;color:var(--danger);font-weight:700;margin-top:2px;"><i class="fa-solid fa-triangle-exclamation"></i> 같은 대상 신고 ${r.sameTargetPendingCount}건 누적</div>`:''}""",
    "관리자 신고 목록에 누적 강조 뱃지 표시", INDEX)

write(INDEX, h)

print("\n✅ 0-18 패치 적용 완료 (server.js + public/index.html).")
print("다음: node -c malbeot-app/server.js 로 문법 확인 후 브라우저에서 관리자모드>신고관리 화면에서 강조 표시 확인, git add -A && git commit && git push")