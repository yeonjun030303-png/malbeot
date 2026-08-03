import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = []

# 1. 회원가입 폼(authForm) - 카카오 신규가입 + 전화번호 신규가입 둘 다 confirmed 플래그 처리
old1 = """document.getElementById('authForm').onsubmit = ()=>{
  // 카카오 신규가입: 전화번호/SMS/비밀번호 없이 닉네임/지역/성별/나이/사진만으로 계정 생성
  if (authMode === 'kakao'){
    const kakaoData = {
      pendingToken: pendingKakaoToken,
      nickname: document.getElementById('regNickname').value.trim(),
      region: document.getElementById('regRegion').value,
      gender: document.getElementById('regGender').value,
      age: document.getElementById('regAge').value,
      bio: '반갑습니다!',
      photos: regPhotoBase64 ? [regPhotoBase64] : []
    };
    socket.emit('auth:kakao_complete_profile', kakaoData, (res)=>{
      if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); authMode='phone'; initApp(); }
      else showMiniAlert(res.message || '가입 중 오류가 발생했습니다. 카카오 로그인을 다시 시도해주세요.', [{label:'확인', primary:true, onClick:()=>{ closeModal('authModal'); openModal('landingScreen'); }}]);
    });
    return;
  }
  if (!isSmsVerified) { showMiniAlert('본인인증을 먼저 진행해 주세요.', [{label:'확인', primary:true}]); return; }
  const authData = {
    phone: normalizePhone(document.getElementById('inputPhone').value),
    password: document.getElementById('regPassword').value,
    nickname: document.getElementById('regNickname').value.trim(),
    region: document.getElementById('regRegion').value,
    gender: document.getElementById('regGender').value,
    age: document.getElementById('regAge').value,
    bio: '반갑습니다!',
    photos: regPhotoBase64 ? [regPhotoBase64] : []
  };
  socket.emit('auth:signup', authData, (res)=>{
    if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); initApp(); }
    else if (res.alreadyExists){
      showMiniAlert('이미 등록된 번호입니다.', [{label:'확인', primary:true, onClick:()=>{
        closeModal('authModal');
        document.getElementById('loginPhone').value = authData.phone;
        openModal('loginModal');
      }}]);
    } else showMiniAlert(res.message || '가입 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
};"""

new1 = """document.getElementById('authForm').onsubmit = ()=>{
  // 카카오 신규가입: 전화번호/SMS/비밀번호 없이 닉네임/지역/성별/나이/사진만으로 계정 생성
  if (authMode === 'kakao'){
    submitKakaoSignup(false);
    return;
  }
  if (!isSmsVerified) { showMiniAlert('본인인증을 먼저 진행해 주세요.', [{label:'확인', primary:true}]); return; }
  submitPhoneSignup(false);
};
function submitKakaoSignup(confirmed){
  const kakaoData = {
    pendingToken: pendingKakaoToken,
    nickname: document.getElementById('regNickname').value.trim(),
    region: document.getElementById('regRegion').value,
    gender: document.getElementById('regGender').value,
    age: document.getElementById('regAge').value,
    bio: '반갑습니다!',
    photos: regPhotoBase64 ? [regPhotoBase64] : [],
    confirmed
  };
  socket.emit('auth:kakao_complete_profile', kakaoData, (res)=>{
    if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); authMode='phone'; initApp(); }
    else if (res.needsConfirm){
      showMiniAlert('닉네임에 부적절한 단어가 발견되었습니다. \\"삭제된 닉네임입니다\\"로 표기됩니다. 그래도 사용하시겠습니까?', [
        {label:'취소', primary:false},
        {label:'확인', primary:true, onClick:()=>submitKakaoSignup(true)}
      ]);
    } else showMiniAlert(res.message || '가입 중 오류가 발생했습니다. 카카오 로그인을 다시 시도해주세요.', [{label:'확인', primary:true, onClick:()=>{ closeModal('authModal'); openModal('landingScreen'); }}]);
  });
}
function submitPhoneSignup(confirmed){
  const authData = {
    phone: normalizePhone(document.getElementById('inputPhone').value),
    password: document.getElementById('regPassword').value,
    nickname: document.getElementById('regNickname').value.trim(),
    region: document.getElementById('regRegion').value,
    gender: document.getElementById('regGender').value,
    age: document.getElementById('regAge').value,
    bio: '반갑습니다!',
    photos: regPhotoBase64 ? [regPhotoBase64] : [],
    confirmed
  };
  socket.emit('auth:signup', authData, (res)=>{
    if (res.success){ currentUser = res.user; saveSession(res.token); closeModal('authModal'); initApp(); }
    else if (res.alreadyExists){
      showMiniAlert('이미 등록된 번호입니다.', [{label:'확인', primary:true, onClick:()=>{
        closeModal('authModal');
        document.getElementById('loginPhone').value = authData.phone;
        openModal('loginModal');
      }}]);
    } else if (res.needsConfirm){
      showMiniAlert('닉네임에 부적절한 단어가 발견되었습니다. \\"삭제된 닉네임입니다\\"로 표기됩니다. 그래도 사용하시겠습니까?', [
        {label:'취소', primary:false},
        {label:'확인', primary:true, onClick:()=>submitPhoneSignup(true)}
      ]);
    } else showMiniAlert(res.message || '가입 중 오류가 발생했습니다.', [{label:'확인', primary:true}]);
  });
}"""
replacements.append((old1, new1, 'authForm 회원가입'))

# 2. 프로필수정 폼(profileForm) - confirmed 플래그 처리
old2 = """document.getElementById('profileForm').onsubmit = ()=>{
  const nickname = document.getElementById('editNickname').value.trim();
  if (!nickname) { showMiniAlert('별명을 입력하세요.', [{label:'확인', primary:true}]); return; }
  const data = {
    nickname, region: document.getElementById('editRegion').value,
    gender: document.getElementById('editGender').value,
    age: parseInt(document.getElementById('editAge').value,10),
    bio: document.getElementById('editBio').value.trim(),
    photos: editPhotoBase64 ? [editPhotoBase64] : [],
    photoPosition: editPhotoBase64 ? editPhotoPosition : null
  };
  socket.emit('profile:update', data, (res)=>{
    if (res.success){ currentUser = res.user; saveSession(); updateUserUI(); showMiniAlert('프로필이 저장되었습니다.', [{label:'확인', primary:true}]); }
  });
};"""

new2 = """document.getElementById('profileForm').onsubmit = ()=>{
  const nickname = document.getElementById('editNickname').value.trim();
  if (!nickname) { showMiniAlert('별명을 입력하세요.', [{label:'확인', primary:true}]); return; }
  submitProfileUpdate(false);
};
function submitProfileUpdate(confirmed){
  const nickname = document.getElementById('editNickname').value.trim();
  const data = {
    nickname, region: document.getElementById('editRegion').value,
    gender: document.getElementById('editGender').value,
    age: parseInt(document.getElementById('editAge').value,10),
    bio: document.getElementById('editBio').value.trim(),
    photos: editPhotoBase64 ? [editPhotoBase64] : [],
    photoPosition: editPhotoBase64 ? editPhotoPosition : null,
    confirmed
  };
  socket.emit('profile:update', data, (res)=>{
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
replacements.append((old2, new2, 'profileForm 프로필수정'))

for old, new, label in replacements:
    count = content.count(old)
    if count != 1:
        print(f'[경고] {label}: 매치 {count}개 (1개여야 정상) - 수동 확인 필요')
        continue
    content = content.replace(old, new)
    print(f'[완료] {label}')

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('저장 완료')