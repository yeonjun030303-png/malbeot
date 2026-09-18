import re

path = "public\index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

patches = []

# ① 첫 메시지 전송 후 새로 만들어진 채팅방을 바로 열기
patches.append((
"""    currentUser.points = res.points; updateUserUI(); saveSession();
    closeMessageComposeScreen(); closeProfileDetailScreen();
    switchTab('tab-chat'); loadChatRoomList();
  });
}""",
"""    currentUser.points = res.points; updateUserUI(); saveSession();
    closeMessageComposeScreen(); closeProfileDetailScreen();
    switchTab('tab-chat');
    loadChatRoomList();
    if (res.roomId) openChatRoomById(res.roomId);
  });
}"""
))

# ③ 차단하기: 메뉴를 확인창 띄우기 전에 즉시 닫도록 (신고하기와 동일한 순서로)
patches.append((
"""function handleBlockAction(){
  // 0-47: 네이티브 confirm() 대신 앱 자체 확인창 사용 + 취소 시엔 blockReportModal을 닫지 않고 그대로 유지
  showMiniAlert('이 사용자를 차단하시겠습니까? 차단하면 서로 연락을 주고받을 수 없습니다.', [
    {label:'취소'},
    {label:'차단', danger:true, onClick:()=>{
      closeModal('blockReportModal');
      let targetId = blockReportContext.id;""",
"""function handleBlockAction(){
  // 0-79: 신고하기와 동일하게, 확인창을 띄우기 전에 먼저 메뉴(blockReportModal)를 닫아서
  // 두 모달이 겹쳐 렌더링되며 커서/포커스가 꼬이던 문제를 방지함
  closeModal('blockReportModal');
  showMiniAlert('이 사용자를 차단하시겠습니까? 차단하면 서로 연락을 주고받을 수 없습니다.', [
    {label:'취소'},
    {label:'차단', danger:true, onClick:()=>{
      let targetId = blockReportContext.id;"""
))

# ④ 전화번호 등록 안내 문구 - 스캠방지 권고 + 예시
patches.append((
"""      <p style="font-size:13px;color:#495057;line-height:1.6;margin-bottom:12px;">서비스 이용을 위해 본인의 전화번호를 등록해주세요. 등록 후에는 직접 수정할 수 없고, 변경이 필요하면 고객센터로 문의해주세요.</p>""",
"""      <p style="font-size:13px;color:#495057;line-height:1.6;margin-bottom:6px;">서비스 이용을 위해 본인의 전화번호를 등록해주세요. 등록 후에는 직접 수정할 수 없고, 변경이 필요하면 고객센터로 문의해주세요.</p>
      <p style="font-size:12px;color:#868e96;line-height:1.5;margin-bottom:12px;">스캠 방지를 위해 실제 사용 중인 번호를 입력하시는 것을 권장드립니다. 원하지 않으실 경우 010-0000-0000과 같은 형식으로 입력하셔도 됩니다.</p>"""
))

# ⑤ 회원탈퇴: 30일 이내 개인정보 폐기 안내 문구 추가
patches.append((
"""function triggerWithdraw(){
  showMiniAlert('정말 탈퇴하시겠습니까? 작성한 게시글/스토리/릴스가 모두 삭제되며 되돌릴 수 없습니다.', [""",
"""function triggerWithdraw(){
  showMiniAlert('정말 탈퇴하시겠습니까? 작성한 게시글/스토리/릴스가 모두 삭제되며 되돌릴 수 없습니다. 탈퇴 처리된 개인정보는 30일 이내에 안전하게 폐기됩니다.', ["""
))

applied = 0
missing = []
for old, new in patches:
    count = content.count(old)
    if count == 1:
        content = content.replace(old, new)
        applied += 1
    elif count == 0:
        missing.append(old[:50] + "...")
    else:
        print(f"[경고] 패턴이 {count}번 발견됨(1번이어야 함), 건너뜀: {old[:50]}...")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"[완료] {applied}/{len(patches)}개 패치 적용됨")
if missing:
    print("[누락된 패턴]")
    for m in missing:
        print(" -", m)
