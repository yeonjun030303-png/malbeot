# -*- coding: utf-8 -*-
"""
0-19: 최초 로그인시 개인 전화번호 1회 등록 + 나만의 페이지에 읽기전용 표시 + 변경은 고객센터 요청->관리자 승인 방식
실행 위치: malbeot 저장소 루트 (malbeot-app 폴더가 보이는 곳)
사용법: python3 patch_0_19_phone_number_feature.py
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
"""  // 어뷰징 의심(동일 기기로 계정 2개 이상) 그룹 목록 - 관리자만""",
"""  // ===================== 개인 전화번호 등록/변경 =====================
  // 카카오 가입 후 최초 1회만 본인 전화번호를 직접 입력받아 저장(카카오 실제번호 대조는 카카오 비즈앱 심사 필요해 이번 범위 아님).
  // 이미 번호가 등록돼 있으면 phoneChangeApproved(관리자 승인)가 true일 때만 재등록 가능하고, 성공하면 승인 플래그는 소모됨.
  socket.on('account:set_phone', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = userId ? await getUser(userId) : null;
      if (!target) return cb && cb({ success: false });
      if (target.phone && !target.phoneChangeApproved) return cb && cb({ success: false, message: '이미 등록된 전화번호가 있습니다. 변경은 고객센터로 문의해주세요.' });
      if (!/^01[0-9]{9}$/.test((data && data.phone) || '')) return cb && cb({ success: false, message: '휴대폰 번호를 정확히 입력해주세요. (예: 010-0000-0000)' });
      target.phone = data.phone;
      if (target.phoneChangeApproved) delete target.phoneChangeApproved;
      await saveUser(target);
      cb && cb({ success: true, phone: target.phone });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  // 번호 변경 요청 접수(고객센터) - 관리자가 승인해야만 실제 변경(account:set_phone) 가능해짐
  socket.on('account:request_phone_change', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = userId ? await getUser(userId) : null;
      if (!target) return cb && cb({ success: false });
      const ref = db.ref('phoneChangeRequests').push();
      const request = { id: ref.key, userId: target.id, currentPhone: target.phone || '', status: 'pending', requestedAt: Date.now() };
      await ref.set(request);
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  // 관리자: 번호 변경 요청 목록 조회
  socket.on('admin:phone_requests:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const snap = await db.ref('phoneChangeRequests').once('value');
      const all = snap.val() || {};
      const users = await getAllUsers();
      const list = Object.values(all)
        .map(r => ({ ...r, nickname: (users[r.userId] && users[r.userId].nickname) || '(탈퇴한 사용자)' }))
        .sort((a, b) => (a.status === 'pending' ? 0 : 1) - (b.status === 'pending' ? 0 : 1) || (b.requestedAt || 0) - (a.requestedAt || 0));
      cb && cb({ success: true, requests: list });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  // 관리자: 번호 변경 요청 승인 -> 해당 유저가 새 번호를 1회 입력할 수 있게 열어줌
  socket.on('admin:phone_requests:approve', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const reqSnap = await db.ref(`phoneChangeRequests/${data && data.requestId}`).once('value');
      const request = reqSnap.val();
      if (!request) return cb && cb({ success: false });
      const target = await getUser(request.userId);
      if (target) {
        target.phoneChangeApproved = true;
        await saveUser(target);
        const sId = userToSocket[target.id];
        if (sId) io.to(sId).emit('account:phone_change_approved', {});
        else sendWebPush(target.id, { title: '전화번호 변경 승인', body: '요청하신 전화번호 변경이 승인되었습니다. 앱에서 새 번호를 입력해주세요.', type: 'phone_change_approved' });
      }
      await db.ref(`phoneChangeRequests/${request.id}`).update({ status: 'approved', resolvedAt: Date.now() });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 어뷰징 의심(동일 기기로 계정 2개 이상) 그룹 목록 - 관리자만""",
    "전화번호 등록/변경요청/관리자승인 소켓 핸들러 3+1개 추가", SERVER)

write(SERVER, s)

# ==================== public/index.html ====================
h = read(INDEX)

# 1) 전화번호 최초 등록 모달 HTML (warningModal 바로 아래에 추가, 같은 강제확인 스타일)
h = replace_once(h,
"""  <div id="warningHistoryModal" class="modal-overlay" onclick="if(event.target===this) closeModal('warningHistoryModal')">""",
"""  <!-- 개인 전화번호 최초 등록창: 카카오 가입 후 최초 로그인시 반드시 입력해야 닫힘(취소/뒤로가기 없음) -->
  <div id="phoneSetupModal" class="modal-overlay">
    <div class="mini-alert-card">
      <h3 style="margin-bottom:10px;"><i class="fa-solid fa-phone"></i> 전화번호 등록</h3>
      <p style="font-size:13px;color:#495057;line-height:1.6;margin-bottom:12px;">서비스 이용을 위해 본인의 전화번호를 등록해주세요. 등록 후에는 직접 수정할 수 없고, 변경이 필요하면 고객센터로 문의해주세요.</p>
      <input type="tel" id="phoneSetupInput" class="form-input" placeholder="010-0000-0000" maxlength="13">
      <div id="phoneSetupError" style="font-size:12px;color:var(--danger);margin-top:6px;display:none;"></div>
      <div style="display:flex;margin-top:14px;">
        <button type="button" class="btn btn-primary" style="flex:1;" onclick="submitPhoneSetup()">등록하기</button>
      </div>
    </div>
  </div>

  <div id="warningHistoryModal" class="modal-overlay" onclick="if(event.target===this) closeModal('warningHistoryModal')">""",
    "phoneSetupModal HTML 추가", INDEX)

# 2) 전화번호 등록 제출 로직 + 승인 리스너 (경고 리스너 바로 아래에 추가)
h = replace_once(h,
"""socket.on('account:warned', (data)=>{
  if (!currentUser) return;
  showWarningModal(data && data.message);
});""",
"""socket.on('account:warned', (data)=>{
  if (!currentUser) return;
  showWarningModal(data && data.message);
});
function openPhoneSetupModal(){
  document.getElementById('phoneSetupInput').value = '';
  document.getElementById('phoneSetupError').style.display = 'none';
  openModal('phoneSetupModal');
}
function submitPhoneSetup(){
  const raw = document.getElementById('phoneSetupInput').value.replace(/[^0-9]/g, '');
  const errEl = document.getElementById('phoneSetupError');
  if (!/^01[0-9]{9}$/.test(raw)){ errEl.textContent = PHONE_FORMAT_MSG; errEl.style.display = 'block'; return; }
  socket.emit('account:set_phone', {phone: raw}, (res)=>{
    if (res && res.success){
      currentUser.phone = res.phone; saveSession();
      closeModal('phoneSetupModal');
      if (currentProfileUserId === currentUser.id) refreshOpenProfileIfNeeded();
    } else {
      errEl.textContent = (res && res.message) || '등록에 실패했습니다.'; errEl.style.display = 'block';
    }
  });
}
// 관리자가 번호 변경 요청을 승인하면, 접속 중인 유저에게 즉시 재입력창을 다시 띄워줌
socket.on('account:phone_change_approved', ()=>{
  if (!currentUser) return;
  showMiniAlert('전화번호 변경 요청이 승인되었습니다. 새 번호를 입력해주세요.', [{label:'확인', primary:true, onClick:()=>{ openPhoneSetupModal(); }}]);
});""",
    "전화번호 등록 제출 함수 + 관리자승인 리스너 추가", INDEX)

# 3) 로그인 성공 시(기존 유저) 번호 미등록이면 등록창 띄움
h = replace_once(h,
"""        if (res.repPhotoSuggestNotify){
          showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
            {label:'나중에', primary:false},
            {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
          ]);
        }
      } else {
        clearSession();
        resetToLandingScreen();
      }
    });
  }
});""",
"""        if (res.repPhotoSuggestNotify){
          showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
            {label:'나중에', primary:false},
            {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
          ]);
        }
        if (!currentUser.phone) openPhoneSetupModal();
      } else {
        clearSession();
        resetToLandingScreen();
      }
    });
  }
});""",
    "세션복구 로그인시 전화번호 미등록이면 등록창 표시", INDEX)

# 4) 카카오 로그인(신규+기존 공용 콜백) 성공시에도 동일하게 체크
h = replace_once(h,
"""        if (res.repPhotoSuggestNotify){
          showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
            {label:'나중에', primary:false},
            {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
          ]);
        }
      } else if (res.needProfile){""",
"""        if (res.repPhotoSuggestNotify){
          showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
            {label:'나중에', primary:false},
            {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
          ]);
        }
        if (!currentUser.phone) openPhoneSetupModal();
      } else if (res.needProfile){""",
    "카카오 로그인 콜백 전화번호 미등록시 등록창 표시", INDEX)

# 5) 카카오 신규가입 완료 직후에도 최초 1회 등록창 띄움
h = replace_once(h,
"""    } else showMiniAlert(res.message || '가입 중 오류가 발생했습니다. 카카오 로그인을 다시 시도해주세요.', [{label:'확인', primary:true, onClick:()=>{ closeModal('authModal'); openModal('landingScreen'); }}]);""",
"""    } else showMiniAlert(res.message || '가입 중 오류가 발생했습니다. 카카오 로그인을 다시 시도해주세요.', [{label:'확인', primary:true, onClick:()=>{ closeModal('authModal'); openModal('landingScreen'); }}]);
    if (res.success && !currentUser.phone) openPhoneSetupModal();""",
    "카카오 신규가입 완료 직후 전화번호 등록창 표시", INDEX)

# 6) 나만의 페이지(프로필 상세, 본인일 때만)에 별명 밑 전화번호 칸 노출
h = replace_once(h,
"""      <div class="profile-tags"><span class="tag">${user.region}</span><span class="tag">${user.gender==='female'?'여성':'남성'}</span><span class="tag">${user.age}세</span></div>""",
"""      ${isMe?`<div style="font-size:12px;color:var(--text-muted);margin:2px 0 6px 0;"><i class="fa-solid fa-phone" style="margin-right:4px;"></i>${user.phone?formatPhoneDisplay(user.phone):'전화번호 미등록'}</div>`:''}
      <div class="profile-tags"><span class="tag">${user.region}</span><span class="tag">${user.gender==='female'?'여성':'남성'}</span><span class="tag">${user.age}세</span></div>""",
    "나만의 페이지 전화번호 표시(읽기전용)", INDEX)

# 7) 고객센터 화면에 "전화번호 변경 요청" 메뉴 추가
h = replace_once(h,
"""      <div class="settings-list-item" onclick="openSupportMailCompose()" style="border:1px solid var(--border-color);border-radius:12px;padding:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:40px;height:40px;border-radius:50%;background:var(--bg-subtle);display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa-solid fa-envelope"></i></div>
          <div><div class="sli-label">1:1 메일 문의</div><div class="sli-sub">kickoff030303@gmail.com</div></div>
        </div>
        <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
      </div>
    </div>
  </div>""",
"""      <div class="settings-list-item" onclick="openSupportMailCompose()" style="border:1px solid var(--border-color);border-radius:12px;padding:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:40px;height:40px;border-radius:50%;background:var(--bg-subtle);display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa-solid fa-envelope"></i></div>
          <div><div class="sli-label">1:1 메일 문의</div><div class="sli-sub">kickoff030303@gmail.com</div></div>
        </div>
        <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
      </div>
      <div class="settings-list-item" onclick="requestPhoneChange()" style="border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-top:12px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:40px;height:40px;border-radius:50%;background:var(--bg-subtle);display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa-solid fa-phone"></i></div>
          <div><div class="sli-label">전화번호 변경 요청</div><div class="sli-sub">관리자 승인 후 새 번호를 등록할 수 있어요</div></div>
        </div>
        <div class="sli-right"><i class="fa-solid fa-chevron-right"></i></div>
      </div>
    </div>
  </div>""",
    "고객센터 화면에 전화번호 변경 요청 메뉴 추가", INDEX)

# 8) 전화번호 변경 요청 제출 함수 (고객센터 챗봇 함수들 근처에 추가)
h = replace_once(h,
"""function openCustomerServiceScreen(){ openFullScreen('customerServiceScreen'); }""",
"""function openCustomerServiceScreen(){ openFullScreen('customerServiceScreen'); }
function requestPhoneChange(){
  showMiniAlert('전화번호 변경을 요청하시겠습니까? 관리자 승인 후 새 번호를 등록할 수 있습니다.', [
    {label:'취소', primary:false},
    {label:'요청하기', primary:true, onClick:()=>{
      socket.emit('account:request_phone_change', {}, (res)=>{
        if (res && res.success) showMiniAlert('전화번호 변경 요청이 접수되었습니다. 승인되면 알려드릴게요.', [{label:'확인', primary:true}]);
        else showMiniAlert('요청 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
      });
    }}
  ]);
}""",
    "requestPhoneChange 함수 추가", INDEX)

# 9) 관리자모드에 "번호변경" 탭 추가
h = replace_once(h,
"""        <button id="adminTabAbuseBtn" class="btn btn-secondary" style="flex:1;" onclick="switchAdminTab('abuse')">어뷰징 의심</button>
      </div>""",
"""        <button id="adminTabAbuseBtn" class="btn btn-secondary" style="flex:1;" onclick="switchAdminTab('abuse')">어뷰징 의심</button>
        <button id="adminTabPhoneBtn" class="btn btn-secondary" style="flex:1;" onclick="switchAdminTab('phone')">번호변경</button>
      </div>""",
    "관리자모드 번호변경 탭 버튼 추가", INDEX)

h = replace_once(h,
"""      <div id="adminAbuseTab" class="hidden">
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">같은 기기에서 가입한 계정이 2개 이상인 그룹만 표시됩니다.</div>
        <div id="adminAbuseList"></div>
      </div>
    </div>
  </div>""",
"""      <div id="adminAbuseTab" class="hidden">
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">같은 기기에서 가입한 계정이 2개 이상인 그룹만 표시됩니다.</div>
        <div id="adminAbuseList"></div>
      </div>
      <div id="adminPhoneTab" class="hidden">
        <div id="adminPhoneRequestList"></div>
      </div>
    </div>
  </div>""",
    "관리자모드 번호변경 탭 내용 영역 추가", INDEX)

h = replace_once(h,
"""  const rBtn = document.getElementById('adminTabReportsBtn');
  const cBtn = document.getElementById('adminTabChatsBtn');
  const aBtn = document.getElementById('adminTabAbuseBtn');
  rBtn.style.background = tab==='reports' ? 'var(--primary)' : '';
  rBtn.style.color = tab==='reports' ? '#fff' : '';
  cBtn.style.background = tab==='chats' ? 'var(--primary)' : '';
  cBtn.style.color = tab==='chats' ? '#fff' : '';
  aBtn.style.background = tab==='abuse' ? 'var(--primary)' : '';
  aBtn.style.color = tab==='abuse' ? '#fff' : '';
  document.getElementById('adminReportsTab').classList.toggle('hidden', tab!=='reports');
  document.getElementById('adminChatsTab').classList.toggle('hidden', tab!=='chats');
  document.getElementById('adminAbuseTab').classList.toggle('hidden', tab!=='abuse');
  if (tab==='reports') loadAdminReports();
  else if (tab==='chats') loadAdminChatRooms();
  else loadAdminAbuse();
}""",
"""  const rBtn = document.getElementById('adminTabReportsBtn');
  const cBtn = document.getElementById('adminTabChatsBtn');
  const aBtn = document.getElementById('adminTabAbuseBtn');
  const pBtn = document.getElementById('adminTabPhoneBtn');
  rBtn.style.background = tab==='reports' ? 'var(--primary)' : '';
  rBtn.style.color = tab==='reports' ? '#fff' : '';
  cBtn.style.background = tab==='chats' ? 'var(--primary)' : '';
  cBtn.style.color = tab==='chats' ? '#fff' : '';
  aBtn.style.background = tab==='abuse' ? 'var(--primary)' : '';
  aBtn.style.color = tab==='abuse' ? '#fff' : '';
  pBtn.style.background = tab==='phone' ? 'var(--primary)' : '';
  pBtn.style.color = tab==='phone' ? '#fff' : '';
  document.getElementById('adminReportsTab').classList.toggle('hidden', tab!=='reports');
  document.getElementById('adminChatsTab').classList.toggle('hidden', tab!=='chats');
  document.getElementById('adminAbuseTab').classList.toggle('hidden', tab!=='abuse');
  document.getElementById('adminPhoneTab').classList.toggle('hidden', tab!=='phone');
  if (tab==='reports') loadAdminReports();
  else if (tab==='chats') loadAdminChatRooms();
  else if (tab==='phone') loadAdminPhoneRequests();
  else loadAdminAbuse();
}
function loadAdminPhoneRequests(){
  socket.emit('admin:phone_requests:list', {}, (res)=>{
    const box = document.getElementById('adminPhoneRequestList');
    if (!res || !res.success){ box.innerHTML=''; return; }
    if (!res.requests.length){ box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);">번호 변경 요청이 없습니다.</div>`; return; }
    box.innerHTML = res.requests.map(r=>`
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div style="display:flex;justify-content:space-between;"><b>${escapeHtml(r.nickname)}</b><span style="font-size:11px;color:var(--text-muted);">${r.status==='pending'?'미처리':'승인완료'}</span></div>
        <div style="font-size:12px;color:var(--text-muted);margin:4px 0;">현재 번호: ${r.currentPhone?formatPhoneDisplay(r.currentPhone):'(미등록)'} · ${formatRelativeTime(r.requestedAt)}</div>
        ${r.status==='pending'?`<button class="btn btn-secondary" onclick="approveAdminPhoneRequest('${r.id}')">승인</button>`:''}
      </div>`).join('');
  });
}
function approveAdminPhoneRequest(requestId){
  socket.emit('admin:phone_requests:approve', {requestId}, (res)=>{
    if (res && res.success) loadAdminPhoneRequests();
    else showMiniAlert('처리 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
}""",
    "관리자모드 번호변경 탭 전환/조회/승인 로직 추가", INDEX)

write(INDEX, h)
print("\n✅ 0-19 패치 적용 완료 (server.js + public/index.html).")
print("다음: node -c malbeot-app/server.js 로 문법 확인 후 git add -A && git commit && git push")