# -*- coding: utf-8 -*-
"""
0-78 패치: 채팅방 열고닫기 반복 시 검은화면+렉 발생 원인 수정

원인: 1:1/단체채팅방 모두 "읽음처리용 IntersectionObserver"가 방을 새로 열 때마다
      새로 만들어지는 게 아니라 앱 전체에서 딱 하나만 재사용되는 싱글턴인데,
      방을 나가거나 다른 방으로 바꿀 때 area.innerHTML=''로 말풍선 DOM만 지우고
      그 말풍선들을 옵저버에서 unobserve() 해주지 않았음.
      -> 아직 한 번도 화면에 안 보여서(스크롤 안 해서) 옵저버가 계속 감시 중이던
         말풍선들이 DOM에서만 사라지고 옵저버 내부에는 계속 쌓임.
      -> 채팅방을 열고닫는 걸 반복할수록(특히 안읽은 메시지가 많은 방일수록)
         감시 대상이 계속 누적되어 메모리를 잡아먹고, 결국 렉/검은화면(웹뷰 메모리부족)으로 이어짐.

수정: 방을 새로 열 때(area.innerHTML='' 직전)와 방을 닫을 때, 옵저버를 disconnect()해서
      쌓여있던 감시 대상을 전부 정리함. disconnect() 후에도 옵저버 객체 자체는 재사용되고
      다음에 observe()하면 정상 동작함(기존 ensureChatReadObserver/ensureGroupReadObserver
      싱글턴 구조와 호환됨).

사용법 (PowerShell, C:\\malbeot 에서):
  python3 patch_0-78.py
"""
import pathlib

FILE = pathlib.Path("malbeot-app/public/index.html")
html = FILE.read_text(encoding="utf-8")

# 1) 1:1 채팅방 열 때 - area.innerHTML 지우기 직전에 옵저버 정리
old1 = """  document.getElementById('chatTargetName').textContent = target.nickname || '';
  chatMaxSeenTs = 0;
  const area = document.getElementById('chatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';"""
assert html.count(old1) == 1, "old1 매칭 실패"
new1 = """  document.getElementById('chatTargetName').textContent = target.nickname || '';
  chatMaxSeenTs = 0;
  // 0-78: 이전 방에서 아직 안 읽혀서 감시 중이던 말풍선들을 여기서 한 번에 정리(누적 방지)
  if (chatReadObserver) chatReadObserver.disconnect();
  const area = document.getElementById('chatMessageArea'); area.innerHTML=''; area.dataset.lastDate='';"""
html = html.replace(old1, new1)

# 2) 1:1 채팅방 닫을 때도 한 번 더 정리(안전망)
old2 = """function closeChatModal(){
  closeModal('chatModal');
  closeFullScreen('chatInfoScreen');
  closeFullScreen('chatGalleryScreen');
  activeRoomId = null;
  activeChatTargetId = null;
  closeChatSearchBar();
  clearTimeout(chatMarkReadTimer);
  chatMaxSeenTs = 0;
}"""
assert html.count(old2) == 1, "old2 매칭 실패"
new2 = """function closeChatModal(){
  closeModal('chatModal');
  closeFullScreen('chatInfoScreen');
  closeFullScreen('chatGalleryScreen');
  activeRoomId = null;
  activeChatTargetId = null;
  closeChatSearchBar();
  clearTimeout(chatMarkReadTimer);
  chatMaxSeenTs = 0;
  // 0-78: 방을 닫을 때도 옵저버 감시 대상 정리(누적 방지 안전망)
  if (chatReadObserver) chatReadObserver.disconnect();
}"""
html = html.replace(old2, new2)

# 3) 단체채팅방 열 때
old3 = """  groupMaxSeenTs = 0;
  document.getElementById('groupChatTitle').textContent = (cached && cached.meta && cached.meta.title) || '단체채팅방';"""
assert html.count(old3) == 1, "old3 매칭 실패"
new3 = """  groupMaxSeenTs = 0;
  // 0-78: 이전 방에서 아직 안 읽혀서 감시 중이던 말풍선들을 여기서 한 번에 정리(누적 방지)
  if (groupReadObserver) groupReadObserver.disconnect();
  document.getElementById('groupChatTitle').textContent = (cached && cached.meta && cached.meta.title) || '단체채팅방';"""
html = html.replace(old3, new3)

# 4) 단체채팅방 닫을 때도 한 번 더 정리(안전망)
old4 = """function closeGroupChatModal(){
  closeFullScreen('groupChatModal');
  activeGroupRoomId = null;
  activeGroupRoomMeta = null;
  closeGroupChatSearchBar();
  loadChatRoomList();
  clearTimeout(groupMarkReadTimer);
  groupMaxSeenTs = 0;
}"""
assert html.count(old4) == 1, "old4 매칭 실패"
new4 = """function closeGroupChatModal(){
  closeFullScreen('groupChatModal');
  activeGroupRoomId = null;
  activeGroupRoomMeta = null;
  closeGroupChatSearchBar();
  loadChatRoomList();
  clearTimeout(groupMarkReadTimer);
  groupMaxSeenTs = 0;
  // 0-78: 방을 닫을 때도 옵저버 감시 대상 정리(누적 방지 안전망)
  if (groupReadObserver) groupReadObserver.disconnect();
}"""
html = html.replace(old4, new4)

FILE.write_text(html, encoding="utf-8")
print("0-78 패치 완료")