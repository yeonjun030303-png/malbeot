# 0-31: 구독(골드/플래티넘) 만료 임박(24시간 이내) 유저에게 1회 알림

path = "server.js"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()

anchor = "setInterval(purgeExpiredFilteredPosts, 60 * 60 * 1000);"
assert anchor in s, "purgeExpiredFilteredPosts setInterval을 찾을 수 없습니다"

addition = anchor + '''

/* =====================================================================
   0-31: 구독(골드/플래티넘) 만료 임박 알림
   - 활성 구독의 만료(expiresAt)까지 24시간 이내로 남은 유저에게 1회만 알림(재알림 방지용
     subscription.expiryNotifiedAt 플래그를 저장) - 접속 중이면 인앱 미니알림, 아니면 웹푸시
===================================================================== */
async function notifySubscriptionsExpiringSoon() {
  try {
    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000;
    const allUsers = await getAllUsers();
    for (const user of Object.values(allUsers)) {
      const sub = user.subscription;
      if (!sub || !sub.tier || !sub.expiresAt) continue;
      const remaining = sub.expiresAt - now;
      if (remaining <= 0 || remaining > oneDay) continue;
      if (sub.expiryNotifiedAt) continue; // 이미 알림 보냄
      const tierLabel = sub.tier === 'platinum' ? '플래티넘' : '골드';
      const msg = `${tierLabel} 구독이 곧 만료돼요. 계속 이용하시려면 다시 구독해주세요.`;
      const sId = userToSocket[user.id];
      if (sId) io.to(sId).emit('subscription:expiring_soon_notify', { message: msg, tier: sub.tier });
      else sendWebPush(user.id, { title: '구독 만료 임박', body: msg, type: 'subscription_expiring' });
      user.subscription.expiryNotifiedAt = now;
      await saveUser(user);
    }
  } catch (e) { console.error('[구독 만료임박 알림 오류]', e); }
}
setInterval(notifySubscriptionsExpiringSoon, 60 * 60 * 1000);'''

s = s.replace(anchor, addition)

with open(path, "w", encoding="utf-8") as f:
    f.write(s)

print("✅ [1/2] server.js — 구독 만료 임박(24시간 이내) 1회 알림 발송 로직 추가 완료")

# 클라이언트: 만료 임박 알림 수신 시 미니알림 표시
path_html = "public/index.html"
with open(path_html, "r", encoding="utf-8") as f:
    h = f.read()

old_client = '''// 0-30: 내가 넣은 신고가 처리되면 결과를 미니알림으로 알려줌
socket.on('report:resolved_notify', (data)=>{
  if (!currentUser) return;
  showMiniAlert((data && data.message) || '신고하신 내용의 처리가 완료되었습니다.', [{label:'확인', primary:true}]);
});'''
assert old_client in h, "0-30 클라이언트 리스너를 찾을 수 없습니다(0-30을 먼저 적용해주세요)"

new_client = old_client + '''
// 0-31: 구독 만료 임박(24시간 이내) 시 미니알림으로 알려주고, 누르면 바로 구독화면으로 이동
socket.on('subscription:expiring_soon_notify', (data)=>{
  if (!currentUser) return;
  showMiniAlert((data && data.message) || '구독이 곧 만료돼요.', [
    {label:'나중에', primary:false},
    {label:'구독 연장하기', primary:true, onClick:()=>{ openSubscriptionScreen(); }}
  ]);
});'''

h = h.replace(old_client, new_client)

with open(path_html, "w", encoding="utf-8") as f:
    f.write(h)

print("✅ [2/2] public/index.html — 구독 만료 임박 알림 수신 처리 추가 완료")
print("0-31 패치 전체 완료")