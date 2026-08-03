import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """function switchTab(tab){
  document.querySelectorAll('.bottom-nav .nav-item').forEach(n=>n.classList.toggle('active', n.dataset.tab===tab));"""

new = """function switchTab(tab){
  // 채팅방을 보다가 하단 탭으로 이동하면 activeRoomId가 안 지워져서
  // 홈 등 다른 화면에 있어도 새 메시지가 자동 읽음 처리되는 버그가 있었음 -> 탭 이동 시 채팅모달 강제로 닫기
  if (activeRoomId) closeChatModal();
  document.querySelectorAll('.bottom-nav .nav-item').forEach(n=>n.classList.toggle('active', n.dataset.tab===tab));"""

count = content.count(old)
if count != 1:
    print(f'[경고] 매치 {count}개 (1개여야 정상) - 수동 확인 필요')
else:
    content = content.replace(old, new)
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('[완료] switchTab 수정')

print('저장 완료')