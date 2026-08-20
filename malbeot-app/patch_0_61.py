# -*- coding: utf-8 -*-
# 0-61: 프로필 저장 화면 멈춤 + 채팅 사진 전송 안 되는 문제 - 근본원인(NSFW 모델 콜드로드) 대응
import os

if not os.path.exists("server.js"):
    print("❌ malbeot-app 폴더 안에서 실행해야 합니다. 현재 위치:", os.getcwd())
    raise SystemExit(1)

# 1) moderation.js - loadNsfwModel 내보내기 추가
with open("moderation.js", encoding="utf-8") as f:
    mod = f.read()
old_mod = """module.exports = {
  BANNED_WORDS,
  containsBannedWord,
  checkImageNsfw
};"""
if old_mod not in mod:
    print("❌ moderation.js 패치 대상 코드를 못 찾았습니다."); raise SystemExit(1)
mod = mod.replace(old_mod, """module.exports = {
  BANNED_WORDS,
  containsBannedWord,
  checkImageNsfw,
  loadNsfwModel
};""")
with open("moderation.js", "w", encoding="utf-8") as f:
    f.write(mod)

# 2) server.js - 서버 시작시 NSFW 모델 예열
with open("server.js", encoding="utf-8") as f:
    srv = f.read()
old_req = "const { checkImageNsfw, containsBannedWord } = require('./moderation');"
if old_req not in srv:
    print("❌ server.js require 패치 대상을 못 찾았습니다."); raise SystemExit(1)
srv = srv.replace(old_req, "const { checkImageNsfw, containsBannedWord, loadNsfwModel } = require('./moderation');")

old_listen = "server.listen(PORT, () => console.log(`말벗 서버 실행 중 (Firebase 연동): http://localhost:${PORT}`));"
if old_listen not in srv:
    print("❌ server.js listen 패치 대상을 못 찾았습니다."); raise SystemExit(1)
srv = srv.replace(old_listen, old_listen + """
// 0-61: NSFW 모델을 서버 시작 시점에 미리 로드(예열)해둠.
// 기존엔 사용자가 사진을 처음 저장/전송하는 순간에 처음 로드되면서 그 요청이 응답 없이 오래 멈춰있는
// 것처럼 보이는 문제(프로필 저장 화면 멈춤, 채팅 사진 전송 안 됨)가 있었음 — 특히 Render 무료 플랜은
// 재시작(502 등)이 잦아 재시작 직후 첫 요청마다 이 문제가 반복됨.
loadNsfwModel()
  .then(() => console.log('✅ NSFW 이미지 검사 모델 예열 완료'))
  .catch(err => console.error('⚠️ NSFW 모델 예열 실패(사용자 요청 시점에 재시도됨):', err.message));""")
with open("server.js", "w", encoding="utf-8") as f:
    f.write(srv)

# 3) public/index.html - 프로필 저장 & 채팅사진 전송에 로딩표시+타임아웃 안내 추가
with open("public/index.html", encoding="utf-8") as f:
    html = f.read()

old_profile = """  socket.emit('profile:update', data, (res)=>{
    if (res.success){ currentUser = res.user; saveSession(); updateUserUI(); showMiniAlert('프로필이 저장되었습니다.', [{label:'확인', primary:true}]); }
    else if (res.needsConfirm){
      showMiniAlert('닉네임에 부적절한 단어가 발견되었습니다. \\"삭제된 닉네임입니다\\"로 표기됩니다. 그래도 사용하시겠습니까?', [
        {label:'취소', primary:false},
        {label:'확인', primary:true, onClick:()=>submitProfileUpdate(true)}
      ]);
    } else {
      showMiniAlert('프로필 저장에 실패했습니다. 네트워크 상태를 확인하고 다시 시도해주세요.', [{label:'확인', primary:true}]);
    }
  });
}"""
if old_profile not in html:
    print("❌ 프로필 저장 패치 대상을 못 찾았습니다(이미 적용됐거나 코드가 변경됨)."); raise SystemExit(1)
new_profile = """  const saveBtn = document.querySelector('#profileForm button[type=\\"submit\\"]');
  if (saveBtn){ saveBtn.disabled = true; saveBtn.dataset.origHtml = saveBtn.innerHTML; saveBtn.innerHTML = '<i class=\\"fa-solid fa-spinner fa-spin\\"></i> 저장 중...'; }
  let profileSaveDone = false;
  const profileSaveTimeout = setTimeout(()=>{
    if (profileSaveDone) return;
    profileSaveDone = true;
    if (saveBtn){ saveBtn.disabled = false; if (saveBtn.dataset.origHtml) saveBtn.innerHTML = saveBtn.dataset.origHtml; }
    showMiniAlert('서버 응답이 지연되고 있어요. 저장이 안 됐을 수 있으니 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  }, 20000);
  socket.emit('profile:update', data, (res)=>{
    if (profileSaveDone) return;
    profileSaveDone = true;
    clearTimeout(profileSaveTimeout);
    if (saveBtn){ saveBtn.disabled = false; if (saveBtn.dataset.origHtml) saveBtn.innerHTML = saveBtn.dataset.origHtml; }
    if (res.success){ currentUser = res.user; saveSession(); updateUserUI(); showMiniAlert('프로필이 저장되었습니다.', [{label:'확인', primary:true}]); }
    else if (res.needsConfirm){
      showMiniAlert('닉네임에 부적절한 단어가 발견되었습니다. \\"삭제된 닉네임입니다\\"로 표기됩니다. 그래도 사용하시겠습니까?', [
        {label:'취소', primary:false},
        {label:'확인', primary:true, onClick:()=>submitProfileUpdate(true)}
      ]);
    } else {
      showMiniAlert('프로필 저장에 실패했습니다. 네트워크 상태를 확인하고 다시 시도해주세요.', [{label:'확인', primary:true}]);
    }
  });
}"""
html = html.replace(old_profile, new_profile)

old_send = """  const onResult = (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  };
  if (meta.isGroup) socket.emit('group:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
  else socket.emit('chat:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
}"""
if old_send not in html:
    print("❌ 채팅 사진전송 패치 대상을 못 찾았습니다(이미 적용됐거나 코드가 변경됨)."); raise SystemExit(1)
new_send = """  let photoSendDone = false;
  const photoSendTimeout = setTimeout(()=>{
    if (photoSendDone) return;
    photoSendDone = true;
    showMiniAlert('서버 응답이 지연되고 있어요. 전송이 안 됐을 수 있으니 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  }, 15000);
  const onResult = (res)=>{
    if (photoSendDone) return;
    photoSendDone = true;
    clearTimeout(photoSendTimeout);
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  };
  if (meta.isGroup) socket.emit('group:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
  else socket.emit('chat:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
}"""
html = html.replace(old_send, new_send)

with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ 0-61 패치 적용 완료: NSFW 모델 서버시작시 예열 + 프로필저장/채팅사진전송 타임아웃 안내 추가")