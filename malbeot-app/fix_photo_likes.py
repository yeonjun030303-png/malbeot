#!/usr/bin/env python3
# 0-11: 프로필 사진별 개별 좋아요 + 대표사진 변경 제안 알림(평생 1회)
#
# ⚠️ 작업 중 발견한 중요 사실: 기존 로드맵엔 "사진별 좋아요"라고만 적혀 있었지만,
#    실제 코드를 까보니 프로필 사진은 지금까지 "대표사진 1장"만 지원했고(photos 배열이 항상 0~1개),
#    profileDetailScreen의 사진 캐러셀/점(dot) UI는 여러 장을 염두에 두고 만들어졌지만 실제로 여러 장을
#    올릴 방법 자체가 없어서 그동안 사실상 죽은 코드였습니다.
#    그래서 이번에 "추가 사진(최대 4장, 대표사진 포함 총 5장)" 업로드 기능부터 새로 만들고,
#    그 위에 사진별 좋아요 + 대표사진 변경 제안을 얹었습니다.
#
# 구현 범위(스스로 판단해서 정한 기본값입니다 - 마음에 안 드시면 말씀해주세요):
#  - 대표 사진: 기존 그대로(위치조절 가능) / 추가 사진: 최대 4장, 그리드로 추가만 가능(위치조절 없음)
#  - 좋아요는 본인 제외 다른 유저만 가능, 대표사진 포함 모든 사진에 가능
#  - 사진 구성(순서/개수)이 바뀌면 인덱스 기반 좋아요 데이터를 초기화함(어긋난 좋아요를 잘못된 사진에 표시하는 것보다 안전)
#  - 대표사진이 아닌 다른 사진의 좋아요 수가 대표사진을 추월하면, 평생 딱 1회만 "대표사진 바꿔보시겠어요?" 알림
#
# 실행 위치: malbeot-app 폴더 안에서 python3 fix_photo_likes.py

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
# 1) popPendingWarningNotify 바로 뒤에 popPendingRepPhotoSuggest 함수 신설
(
"""async function popPendingWarningNotify(user) {
  if (user.pendingWarningNotify && !user.pendingWarningNotify.notified) {
    const info = { message: WARNING_MESSAGE };
    user.pendingWarningNotify.notified = true;
    await saveUser(user);
    return info;
  }
  return null;
}""",
"""async function popPendingWarningNotify(user) {
  if (user.pendingWarningNotify && !user.pendingWarningNotify.notified) {
    const info = { message: WARNING_MESSAGE };
    user.pendingWarningNotify.notified = true;
    await saveUser(user);
    return info;
  }
  return null;
}
// 대표사진이 아닌 다른 사진이 좋아요를 더 많이 받으면 "대표사진을 바꿔보세요"를 딱 1회(평생)만 알려주기 위해
// 대기시켜둔 알림을 꺼내는 함수. popPendingWarningNotify와 완전히 동일한 패턴(접속 중이면 즉시 소켓으로 보여주고
// notified:true 처리, 오프라인이면 다음 로그인 응답에 실어서 전달).
async function popPendingRepPhotoSuggest(user) {
  if (user.pendingRepPhotoSuggest && !user.pendingRepPhotoSuggest.notified) {
    const info = { photoIndex: user.pendingRepPhotoSuggest.photoIndex };
    user.pendingRepPhotoSuggest.notified = true;
    await saveUser(user);
    return info;
  }
  return null;
}""",
"popPendingRepPhotoSuggest 함수 신설"
),
# 2) profile:update - 사진 전부 NSFW 검사 + 사진 구성 변경 시 좋아요 초기화
(
"""      if (data.photos && data.photos[0]) {
        const nsfwResult = await checkImageNsfw(data.photos[0]);
        if (nsfwResult.isNsfw) return cb({ success: false, message: '부적절한 프로필 사진으로 감지되어 변경할 수 없습니다.' });
      }

      Object.assign(user, data, { profileUpdatedAt: Date.now() });
      await saveUser(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) } });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });
// 회원탈퇴""",
"""      // 대표사진뿐 아니라 추가 사진까지(최대 5장) 전부 검사
      if (data.photos && data.photos.length) {
        for (const photoData of data.photos) {
          if (!photoData) continue;
          const nsfwResult = await checkImageNsfw(photoData);
          if (nsfwResult.isNsfw) return cb({ success: false, message: '부적절한 사진이 포함되어 있어 변경할 수 없습니다.' });
        }
      }

      // 사진 구성(순서/개수)이 바뀌면 인덱스 기반 사진별 좋아요가 엉뚱한 사진을 가리킬 수 있어
      // 안전하게 초기화함(좋아요 자체가 사라지는 게 아니라 새 구성 기준으로 다시 쌓이는 것)
      const photosChanged = data.photos && JSON.stringify(data.photos) !== JSON.stringify(user.photos || []);

      Object.assign(user, data, { profileUpdatedAt: Date.now() });
      if (photosChanged) user.photoLikes = {};
      await saveUser(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) } });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });
  // 프로필 사진별 개별 좋아요 토글 (본인 사진은 좋아요 불가)
  socket.on('photo:like', async (data, cb) => {
    try {
      const myId = socketToUser[socket.id];
      const targetId = data && data.targetUserId;
      const photoIndex = data && typeof data.photoIndex === 'number' ? data.photoIndex : null;
      if (!myId || !targetId || photoIndex === null || myId === targetId) return cb && cb({ success: false });
      const target = await getUser(targetId);
      if (!target || !target.photos || !target.photos[photoIndex]) return cb && cb({ success: false });
      if (!target.photoLikes) target.photoLikes = {};
      if (!target.photoLikes[photoIndex]) target.photoLikes[photoIndex] = {};
      const alreadyLiked = !!target.photoLikes[photoIndex][myId];
      if (alreadyLiked) delete target.photoLikes[photoIndex][myId];
      else target.photoLikes[photoIndex][myId] = true;

      // 대표사진(0번)이 아닌 사진이 새로 좋아요를 받아 대표사진보다 많아지면, 평생 1회만 대표사진 변경을 제안함
      if (!alreadyLiked && photoIndex !== 0 && !target.repPhotoSuggestShown) {
        const repCount = Object.keys(target.photoLikes[0] || {}).length;
        const thisCount = Object.keys(target.photoLikes[photoIndex] || {}).length;
        if (thisCount > repCount) {
          target.repPhotoSuggestShown = true;
          target.pendingRepPhotoSuggest = { photoIndex, at: Date.now(), notified: false };
          const sId = userToSocket[targetId];
          if (sId) {
            io.to(sId).emit('account:rep_photo_suggest', { photoIndex });
            target.pendingRepPhotoSuggest.notified = true;
          }
        }
      }

      await saveUser(target);
      cb && cb({ success: true, liked: !alreadyLiked, likeCount: Object.keys(target.photoLikes[photoIndex] || {}).length });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
// 회원탈퇴""",
"profile:update 전체사진 NSFW검사+좋아요초기화, photo:like 핸들러 신설"
),
# 3) auth:login - repPhotoSuggestNotify 추가
(
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 세션 토큰으로 자동 로그인""",
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      const repPhotoSuggestNotify = await popPendingRepPhotoSuggest(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, repPhotoSuggestNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 세션 토큰으로 자동 로그인""",
"auth:login에 repPhotoSuggestNotify 추가"
),
# 4) auth:session_resume - repPhotoSuggestNotify 추가
(
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id); // 갱신(연장)
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }""",
"""      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id); // 갱신(연장)
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      const repPhotoSuggestNotify = await popPendingRepPhotoSuggest(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, repPhotoSuggestNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }""",
"auth:session_resume에 repPhotoSuggestNotify 추가"
),
# 5) 카카오 로그인 - repPhotoSuggestNotify 추가
(
"""        const dailyRewardAmount = grantDailyLoginRewardIfNeeded(existing);
        await saveUser(existing);
        socketToUser[socket.id] = existing.id;
        userToSocket[existing.id] = socket.id;
        const token = issueSessionToken(existing.id);
        const rewardNotify = await popPendingRewardNotify(existing);
        const warningNotify = await popPendingWarningNotify(existing);
        cb({ success: true, user: { ...existing, isAdmin: isAdmin(existing) }, token, rewardNotify, warningNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
        broadcastUsers();""",
"""        const dailyRewardAmount = grantDailyLoginRewardIfNeeded(existing);
        await saveUser(existing);
        socketToUser[socket.id] = existing.id;
        userToSocket[existing.id] = socket.id;
        const token = issueSessionToken(existing.id);
        const rewardNotify = await popPendingRewardNotify(existing);
        const warningNotify = await popPendingWarningNotify(existing);
        const repPhotoSuggestNotify = await popPendingRepPhotoSuggest(existing);
        cb({ success: true, user: { ...existing, isAdmin: isAdmin(existing) }, token, rewardNotify, warningNotify, repPhotoSuggestNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
        broadcastUsers();""",
"카카오 로그인에 repPhotoSuggestNotify 추가"
),
]

html_replacements = [
# A) 대표사진 아래에 "추가 사진" 섹션 신설
(
"""            <div id="editPhotoPositionWrap" class="hidden">
              <div class="photo-position-box" id="editPhotoPositionBox"><img id="editPhotoPositionImg" src="" alt=""></div>
              <div class="photo-position-hint">사진을 드래그해서 보여줄 위치를 맞춰주세요</div>
            </div>
          </div>
          <form id="profileForm" onsubmit="return false;">""",
"""            <div id="editPhotoPositionWrap" class="hidden">
              <div class="photo-position-box" id="editPhotoPositionBox"><img id="editPhotoPositionImg" src="" alt=""></div>
              <div class="photo-position-hint">사진을 드래그해서 보여줄 위치를 맞춰주세요</div>
            </div>
          </div>
          <div class="form-group">
            <label>추가 사진 <span style="font-weight:400;color:var(--text-muted);">(최대 4장, 사진마다 좋아요를 받을 수 있어요)</span></label>
            <div class="photo-slots" id="editExtraPhotoSlots" style="flex-wrap:wrap;"></div>
            <input type="file" id="editExtraPhotoInput" accept="image/*" class="hidden" onchange="handleEditExtraPhotoUpload(event)">
          </div>
          <form id="profileForm" onsubmit="return false;">""",
"A) 프로필 편집화면에 추가 사진 섹션 마크업 추가"
),
# A-2) 추가 사진 JS 로직 (loadProfileToForm 바로 앞에 삽입)
(
"""function loadProfileToForm(){
  if (!currentUser) return;""",
"""const EXTRA_PHOTO_MAX = 4;
let editExtraPhotos = [];
function renderExtraPhotoSlots(){
  const wrap = document.getElementById('editExtraPhotoSlots');
  let html = editExtraPhotos.map((src,i)=>`
    <div class="photo-slot" style="flex:0 0 68px;width:68px;height:68px;">
      <img src="${src}" class="photo-preview">
      <span onclick="event.stopPropagation();removeExtraPhoto(${i})" style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,.55);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;cursor:pointer;"><i class="fa-solid fa-xmark"></i></span>
    </div>`).join('');
  if (editExtraPhotos.length < EXTRA_PHOTO_MAX){
    html += `<div class="photo-slot" style="flex:0 0 68px;width:68px;height:68px;" onclick="document.getElementById('editExtraPhotoInput').click()"><span><i class="fa-solid fa-plus"></i></span></div>`;
  }
  wrap.innerHTML = html;
}
function removeExtraPhoto(i){ editExtraPhotos.splice(i,1); renderExtraPhotoSlots(); }
async function handleEditExtraPhotoUpload(e){
  const file = e.target.files[0]; if (!file) return;
  if (editExtraPhotos.length >= EXTRA_PHOTO_MAX) { e.target.value=''; return; }
  const b64 = await compressImageFile(file);
  editExtraPhotos.push(b64);
  renderExtraPhotoSlots();
  e.target.value = '';
}
function loadProfileToForm(){
  if (!currentUser) return;""",
"A) 추가 사진 렌더/추가/삭제 JS 함수 신설"
),
# A-3) loadProfileToForm에서 currentUser.photos[1:]로 editExtraPhotos 초기화
(
"""    document.getElementById('editPhotoPositionWrap').classList.remove('hidden');
  } else {
    editPhotoBase64 = '';
    preview.classList.add('hidden'); document.getElementById('editPhotoPlaceholder').classList.remove('hidden');
    document.getElementById('editPhotoPositionWrap').classList.add('hidden');
  }
}""",
"""    document.getElementById('editPhotoPositionWrap').classList.remove('hidden');
  } else {
    editPhotoBase64 = '';
    preview.classList.add('hidden'); document.getElementById('editPhotoPlaceholder').classList.remove('hidden');
    document.getElementById('editPhotoPositionWrap').classList.add('hidden');
  }
  editExtraPhotos = (currentUser.photos || []).slice(1);
  renderExtraPhotoSlots();
}""",
"A) loadProfileToForm에서 추가 사진 초기화"
),
# A-4) submitProfileUpdate에서 대표사진+추가사진 합쳐서 전송
(
"""    photos: editPhotoBase64 ? [editPhotoBase64] : [],""",
"""    photos: editPhotoBase64 ? [editPhotoBase64, ...editExtraPhotos] : [],""",
"A) submitProfileUpdate 전송 데이터에 추가 사진 포함"
),
# B) 프로필 상세화면 - 점(dot) 클릭 네비게이션 + 사진별 좋아요 버튼
(
"""  const dots = photos.map((_,i)=>`<span class="${i===profilePhotoIndex?'active':''}"></span>`).join('');""",
"""  const dots = photos.map((_,i)=>`<span class="${i===profilePhotoIndex?'active':''}" style="cursor:pointer;" onclick="changeProfilePhoto(${i})"></span>`).join('');
  const myPhotoLikes = (user.photoLikes && user.photoLikes[profilePhotoIndex]) || {};
  const photoLikeCount = Object.keys(myPhotoLikes).length;
  const iLikedThisPhoto = currentUser && !!myPhotoLikes[currentUser.id];""",
"B) 점 클릭 네비게이션 + 현재 사진 좋아요 상태 계산"
),
(
"""      ${photos.length>1?`<div class="profile-photo-dots">${dots}</div>`:''}
    </div>""",
"""      ${photos.length>1?`<div class="profile-photo-dots">${dots}</div>`:''}
      ${(!isMe && hasPhotos)?`<button class="photo-like-btn" onclick="toggleProfilePhotoLike('${user.id}', ${profilePhotoIndex})"><i class="fa-${iLikedThisPhoto?'solid':'regular'} fa-heart" style="color:${iLikedThisPhoto?'#ff4d6d':'#fff'};"></i> <span>${photoLikeCount}</span></button>`:''}
    </div>""",
"B) 사진별 좋아요 버튼(하트+숫자) 오버레이 추가"
),
# B-2) 사진 전환/좋아요 토글 함수 신설 (renderProfileDetail 함수 바로 앞)
(
"""function renderProfileDetail(user){""",
"""function changeProfilePhoto(i){ profilePhotoIndex = i; if (currentProfileUserCache) renderProfileDetail(currentProfileUserCache); }
function toggleProfilePhotoLike(targetUserId, photoIndex){
  socket.emit('photo:like', {targetUserId, photoIndex}, (res)=>{
    if (!res || !res.success || !currentProfileUserCache) return;
    if (!currentProfileUserCache.photoLikes) currentProfileUserCache.photoLikes = {};
    if (!currentProfileUserCache.photoLikes[photoIndex]) currentProfileUserCache.photoLikes[photoIndex] = {};
    if (res.liked) currentProfileUserCache.photoLikes[photoIndex][currentUser.id] = true;
    else delete currentProfileUserCache.photoLikes[photoIndex][currentUser.id];
    renderProfileDetail(currentProfileUserCache);
  });
}
function renderProfileDetail(user){""",
"B) changeProfilePhoto/toggleProfilePhotoLike 함수 신설"
),
# B-3) 사진별 좋아요 버튼 CSS
(
""".profile-photo-dots span.active{background:#fff;}""",
""".profile-photo-dots span.active{background:#fff;}
.photo-like-btn{position:absolute;right:12px;bottom:14px;background:rgba(0,0,0,.45);color:#fff;border:none;border-radius:99px;padding:7px 12px;display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;cursor:pointer;}""",
"B) 사진별 좋아요 버튼 CSS 추가"
),
# C) 대표사진 변경 제안 알림 소켓 핸들러
(
"""socket.on('account:warned', (data)=>{
  if (!currentUser) return;
  showWarningModal(data && data.message);
});""",
"""socket.on('account:warned', (data)=>{
  if (!currentUser) return;
  showWarningModal(data && data.message);
});
// 대표사진이 아닌 다른 사진이 좋아요를 더 많이 받았을 때 평생 1회만 뜨는 제안 알림
socket.on('account:rep_photo_suggest', (data)=>{
  if (!currentUser) return;
  showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
    {label:'나중에', primary:false},
    {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
  ]);
});""",
"C) 대표사진 변경 제안 알림 소켓 핸들러 신설(접속 중 실시간 수신용)"
),
# C-2) 세션 자동복원 로그인 성공 콜백에도 repPhotoSuggestNotify 반영 (오프라인이었다가 재접속 시 수신용)
(
"""        currentUser = res.user; saveSession(res.token);
        closeModal('landingScreen'); closeModal('authModal');
        initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.dailyRewardNotify){
          showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }""",
"""        currentUser = res.user; saveSession(res.token);
        closeModal('landingScreen'); closeModal('authModal');
        initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.dailyRewardNotify){
          showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }
        if (res.repPhotoSuggestNotify){
          showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
            {label:'나중에', primary:false},
            {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
          ]);
        }""",
"C) 세션 자동복원(auth:session_resume) 콜백에 repPhotoSuggestNotify 반영"
),
# C-3) 카카오 로그인 성공 콜백에도 repPhotoSuggestNotify 반영
(
"""        currentUser = res.user; saveSession(res.token);
        closeModal('landingScreen'); initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.dailyRewardNotify){
          showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }""",
"""        currentUser = res.user; saveSession(res.token);
        closeModal('landingScreen'); initApp();
        if (res.rewardNotify){
          showMiniAlert(`어제의 인기 투표로 선정되셔서 포인트 ${res.rewardNotify.amount}개를 지급했어요!`, [{label:'확인', primary:true}]);
        }
        if (res.dailyRewardNotify){
          showMiniAlert(`오늘의 접속 보상으로 쌀 ${res.dailyRewardNotify.amount}개가 지급되었습니다!`, [{label:'확인', primary:true}]);
        }
        if (res.warningNotify){ showWarningModal(res.warningNotify.message); }
        if (res.repPhotoSuggestNotify){
          showMiniAlert('다른 사진이 대표사진보다 좋아요를 더 많이 받았어요! 대표사진을 바꿔보시겠어요?', [
            {label:'나중에', primary:false},
            {label:'프로필 편집하기', primary:true, onClick:()=>{ openSettingsScreen(); loadProfileToForm(); }}
          ]);
        }""",
"C) 카카오 로그인(auth:kakao_login) 콜백에 repPhotoSuggestNotify 반영"
),
]

patch('server.js', server_replacements)
patch('public/index.html', html_replacements)

print("다음 순서로 진행하세요:")
print("1) node -c server.js")
print("2) git add -A && git commit -m \"0-11: 프로필 사진별 개별 좋아요 + 추가 사진(최대 4장) 업로드 + 대표사진 변경 제안 알림\"")
print("3) (모아뒀다가 원하실 때) git push")