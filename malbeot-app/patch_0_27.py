path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) 초대코드 계산부: URL에 없으면 sessionStorage에 저장해둔 값도 확인(카카오 로그인 후 복귀 대비)
old1 = '''let pendingInviteCode = (function(){
  const m = location.pathname.match(/^\\/join\\/([A-Za-z0-9]+)/);
  return m ? m[1] : null;
})();'''
assert old1 in content, "pendingInviteCode 초기화부를 찾을 수 없습니다"

new1 = '''let pendingInviteCode = (function(){
  const m = location.pathname.match(/^\\/join\\/([A-Za-z0-9]+)/);
  if (m) return m[1];
  // 카카오 로그인은 페이지를 완전히 이동했다 돌아오는 방식이라 위 location.pathname이 사라짐 ->
  // startKakaoLogin()에서 미리 저장해둔 값을 여기서 복원함(1회용, 바로 제거)
  const saved = sessionStorage.getItem('malbeot_pending_invite_code');
  if (saved) sessionStorage.removeItem('malbeot_pending_invite_code');
  return saved || null;
})();'''

content = content.replace(old1, new1)

# 2) startKakaoLogin(): 카카오로 이동하기 전 초대코드를 sessionStorage에 저장
old2 = '''function startKakaoLogin(){
  if (!KAKAO_REST_API_KEY || KAKAO_REST_API_KEY === 'YOUR_KAKAO_REST_API_KEY_HERE'){
    showMiniAlert('카카오 로그인이 아직 설정되지 않았습니다. (KAKAO_REST_API_KEY 미설정)', [{label:'확인', primary:true}]);
    return;
  }
  const redirectUri = window.location.origin + '/';'''
assert old2 in content, "startKakaoLogin 함수를 찾을 수 없습니다"

new2 = '''function startKakaoLogin(){
  if (!KAKAO_REST_API_KEY || KAKAO_REST_API_KEY === 'YOUR_KAKAO_REST_API_KEY_HERE'){
    showMiniAlert('카카오 로그인이 아직 설정되지 않았습니다. (KAKAO_REST_API_KEY 미설정)', [{label:'확인', primary:true}]);
    return;
  }
  // 0-27: 초대링크(/join/코드)로 들어온 상태에서 카카오 로그인을 누르면 브라우저가 카카오로 완전히 이동했다가
  // redirect_uri(origin+'/')로 돌아오기 때문에 pendingInviteCode 값이 사라짐 -> sessionStorage에 잠깐 저장해뒀다가
  // 위쪽 pendingInviteCode 초기화 로직에서 복원함
  if (pendingInviteCode) sessionStorage.setItem('malbeot_pending_invite_code', pendingInviteCode);
  const redirectUri = window.location.origin + '/';'''

content = content.replace(old2, new2)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 0-27 패치 적용 완료: 카카오 로그인 경유 시 초대링크 자동입장 코드 유실 버그 수정")