# -*- coding: utf-8 -*-
"""
0-12: 웹 푸시 알림(VAPID) 추가 + leftover 패치 스크립트/이상 파일 일괄 정리
실행 위치: malbeot 저장소 루트 (malbeot-app 폴더가 보이는 곳)
사용법: python3 patch_0_12_webpush_and_cleanup.py
"""
import os, re, sys

ROOT = os.getcwd()
APP = os.path.join(ROOT, "malbeot-app")
if not os.path.isdir(APP):
    print("!! malbeot-app 폴더를 찾을 수 없습니다. 저장소 루트에서 실행하세요."); sys.exit(1)

SERVER = os.path.join(APP, "server.js")
INDEX = os.path.join(APP, "public", "index.html")
PKG = os.path.join(APP, "package.json")
SW = os.path.join(APP, "public", "sw.js")

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def write(p, s):
    with open(p, "w", encoding="utf-8") as f: f.write(s)

def replace_once(content, old, new, label, path):
    if new in content:
        print(f"   (건너뜀-이미적용됨) {label}")
        return content
    if old not in content:
        print(f"!! 매칭 실패: {label} ({path}) — 수동 확인 필요"); sys.exit(1)
    if content.count(old) != 1:
        print(f"!! 매칭이 1개가 아님({content.count(old)}개): {label} ({path})"); sys.exit(1)
    print(f"   적용: {label}")
    return content.replace(old, new)

# ---------------- server.js ----------------
s = read(SERVER)

s = replace_once(s,
    "const { checkImageNsfw, containsBannedWord } = require('./moderation');",
    "const { checkImageNsfw, containsBannedWord } = require('./moderation');\nconst webpush = require('web-push');",
    "web-push require 추가", SERVER)

s = replace_once(s,
"""const db = admin.database();

const app = express();""",
"""const db = admin.database();

// ===== 웹 푸시 알림 (VAPID) =====
// .env에 VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT(예: mailto:본인이메일)를 설정핼야 동작함.
// 키가 없으면 웹 푸시만 조용히 비활성화되고 기존 소켓 기반 인앱 알림은 그대로 동작함.
const VAPID_PUBLIC_KEY = process.env.VAPID_PUBLIC_KEY || '';
const VAPID_PRIVATE_KEY = process.env.VAPID_PRIVATE_KEY || '';
const VAPID_SUBJECT = process.env.VAPID_SUBJECT || 'mailto:kickoff030303@gmail.com';
const PUSH_ENABLED = !!(VAPID_PUBLIC_KEY && VAPID_PRIVATE_KEY);
if (PUSH_ENABLED) {
  webpush.setVapidDetails(VAPID_SUBJECT, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY);
} else {
  console.warn('[경고] VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY가 .env에 없어 웹 푸시 알림이 비활성화됩니다.');
}

// 유저가 앱을 꺼두었을 때(소켓 미접속)도 도착하는 실제 브라우저 푸시 발송
// 만료/무효 구독(404/410)은 자동으로 정리함
async function sendWebPush(userId, payload) {
  if (!PUSH_ENABLED || !userId) return;
  try {
    const snap = await db.ref(`users/${userId}/pushSubscriptions`).once('value');
    const subs = snap.val();
    if (!subs) return;
    for (const [subId, sub] of Object.entries(subs)) {
      try {
        await webpush.sendNotification(sub, JSON.stringify(payload));
      } catch (err) {
        if (err.statusCode === 404 || err.statusCode === 410) {
          await db.ref(`users/${userId}/pushSubscriptions/${subId}`).remove();
        } else {
          console.error('[웹푸시 전송 오류]', err.statusCode, err.body);
        }
      }
    }
  } catch (e) { console.error('[웹푸시 조회 오류]', e); }
}

const app = express();""",
    "VAPID 설정 + sendWebPush 헬퍼", SERVER)

s = replace_once(s,
    "app.get('/health', (req, res) => res.status(200).send('ok'));",
"""app.get('/health', (req, res) => res.status(200).send('ok'));

// ===== 웹 푸시 구독 관리 API =====
app.get('/api/push/vapid-public-key', (req, res) => {
  res.json({ publicKey: VAPID_PUBLIC_KEY });
});
app.post('/api/push/subscribe', async (req, res) => {
  try {
    const { userId, subscription } = req.body;
    if (!userId || !subscription || !subscription.endpoint) return res.status(400).json({ error: '필수 항목이 누락되었습니다.' });
    const subId = Buffer.from(subscription.endpoint).toString('base64').replace(/[^a-zA-Z0-9]/g, '').slice(-40);
    await db.ref(`users/${userId}/pushSubscriptions/${subId}`).set(subscription);
    res.json({ success: true });
  } catch (e) { console.error('[푸시 구독 저장 오류]', e); res.status(500).json({ error: '구독 저장 실패' }); }
});
app.post('/api/push/unsubscribe', async (req, res) => {
  try {
    const { userId, endpoint } = req.body;
    if (!userId || !endpoint) return res.status(400).json({ error: '필수 항목이 누락되었습니다.' });
    const subId = Buffer.from(endpoint).toString('base64').replace(/[^a-zA-Z0-9]/g, '').slice(-40);
    await db.ref(`users/${userId}/pushSubscriptions/${subId}`).remove();
    res.json({ success: true });
  } catch (e) { console.error('[푸시 구독 해제 오류]', e); res.status(500).json({ error: '구독 해제 실패' }); }
});""",
    "웹 푸시 구독/해제/공개키 API 라우트", SERVER)

s = replace_once(s,
"""function notifyUser(userId, payload) {
  if (!userId) return;
  const sId = userToSocket[userId];
  if (sId) io.to(sId).emit('notify:new', payload);
}""",
"""function notifyUser(userId, payload) {
  if (!userId) return;
  const sId = userToSocket[userId];
  if (sId) io.to(sId).emit('notify:new', payload);
  // 소켓 미접속(=앱이 꺼져있음) 상태일 때만 웹 푸시로 대신 알림 (앱 켜져있을 땐 인앱 알림으로 충분)
  else sendWebPush(userId, { title: payload.title || '말벗', body: payload.body || payload.text || '', type: payload.type || null, postId: payload.postId || null, userId: payload.userId || null });
}""",
    "notifyUser에 오프라인 웹푸시 연결", SERVER)

s = replace_once(s,
"""      cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
      });
      broadcastUsers();""",
"""      cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
        else if (uid !== user.id) sendWebPush(uid, { title: user.nickname || '말벗', body: msg.type === 'image' ? '사진을 보냈습니다' : (msg.text || ''), type: 'chat', roomId });
      });
      broadcastUsers();""",
    "1:1 채팅 첫 메시지(신규방) 오프라인 웹푸시", SERVER)

s = replace_once(s,
"""      const msg = await addMessage(data.roomId, msgPayload);
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      });
    } catch (e) { console.error(e); }
  });""",
"""      const msg = await addMessage(data.roomId, msgPayload);
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
        else if (uid !== userId) sendWebPush(uid, { title: (sender && sender.nickname) || '말벗', body: msg.text || '', type: 'chat', roomId: data.roomId });
      });
    } catch (e) { console.error(e); }
  });""",
    "chat:send_message 오프라인 웹푸시", SERVER)

s = replace_once(s,
"""      const msg = await addMessage(data.roomId, { senderId: userId, type: 'image', data: data.image, timestamp: Date.now(), read: false });
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      });
      cb && cb({ success: true });""",
"""      const msg = await addMessage(data.roomId, { senderId: userId, type: 'image', data: data.image, timestamp: Date.now(), read: false });
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
        else if (uid !== userId) sendWebPush(uid, { title: (sender && sender.nickname) || '말벗', body: '사진을 보냈습니다', type: 'chat', roomId: data.roomId });
      });
      cb && cb({ success: true });""",
    "chat:send_image 오프라인 웹푸시", SERVER)

s = replace_once(s,
"""      cb && cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
      });
      broadcastUsers();""",
"""      cb && cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
        else if (uid !== user.id) sendWebPush(uid, { title: user.nickname || '말벗', body: msg.type === 'image' ? '사진을 보냈습니다' : (msg.text || ''), type: 'chat', roomId });
      });
      broadcastUsers();""",
    "chat:forward_message 오프라인 웹푸시", SERVER)

write(SERVER, s)

# ---------------- public/index.html ----------------
h = read(INDEX)
h = replace_once(h,
"""function requestNotifyPermissionIfNeeded(){
  if ('Notification' in window && Notification.permission === 'default') { Notification.requestPermission(); }
}""",
"""function requestNotifyPermissionIfNeeded(){
  if (!('Notification' in window)) return;
  if (Notification.permission === 'default') { Notification.requestPermission().then(()=>{ setupWebPush(); }); }
  else if (Notification.permission === 'granted') { setupWebPush(); }
}
// base64 형식의 VAPID 공개키를 브라우저 푸시 구독용 Uint8Array로 변환
function urlBase64ToUint8Array(base64String){
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}
let _vapidPublicKeyCache = null;
// 서비스워커 등록 + 브라우저 푸시 구독 + 서버에 구독정보 저장 (앱이 꺼져있어도 알림이 오게 하기 위함)
async function setupWebPush(){
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
  if (!currentUser || Notification.permission !== 'granted') return;
  try{
    const reg = await navigator.serviceWorker.register('/sw.js');
    let sub = await reg.pushManager.getSubscription();
    if (!sub){
      if (!_vapidPublicKeyCache){
        const res = await fetch('/api/push/vapid-public-key');
        const data = await res.json();
        _vapidPublicKeyCache = data.publicKey;
      }
      if (!_vapidPublicKeyCache) return; // 서버에 VAPID 키 미설정 시 조용히 종료(기존 인앱 알림은 그대로 동작)
      sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(_vapidPublicKeyCache) });
    }
    await fetch('/api/push/subscribe', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ userId: currentUser.id, subscription: sub }) });
  }catch(e){ console.warn('[웹푸시 구독 실패]', e); }
}""",
    "웹 푸시 구독 등록 로직", INDEX)
write(INDEX, h)

# ---------------- package.json ----------------
p = read(PKG)
if '"web-push"' not in p:
    p = replace_once(p, '"socket.io": "^4.7.5"', '"socket.io": "^4.7.5",\n    "web-push": "^3.6.7"', "package.json에 web-push 의존성 추가", PKG)
    write(PKG, p)
else:
    print("   (건너뜀-이미적용됨) package.json web-push 의존성")

# ---------------- public/sw.js ----------------
if not os.path.exists(SW):
    write(SW, """// 말벗 웹 푸시 서비스워커
// 앱(탭)이 꺼져있거나 백그라운드일 때도 알림을 표시하기 위한 백그라운드 스크립트

self.addEventListener('install', () => { self.skipWaiting(); });
self.addEventListener('activate', (event) => { event.waitUntil(self.clients.claim()); });

self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = { title: '말벗', body: event.data ? event.data.text() : '' }; }
  const title = data.title || '말벗';
  const options = {
    body: data.body || '',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    data: { type: data.type || null, roomId: data.roomId || null, postId: data.postId || null, userId: data.userId || null }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

// 알림을 클릭하면 이미 열려있는 말벗 탭이 있으면 그 탭에 포커스, 없으면 새로 엶
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow('/');
    })
  );
});
""")
    print("   생성: public/sw.js")
else:
    print("   (건너뜀-이미존재함) public/sw.js")

# ---------------- leftover 파일 정리 ----------------
LEFTOVERS = [
    os.path.join(ROOT, "fix_chat_header_profile.py"),
    os.path.join(ROOT, "main.py"),
    os.path.join(APP, "fix_chat_fullscreen.py"),
    os.path.join(APP, "fix_chat_read.py"),
    os.path.join(APP, "fix_interest_subaccordion.py"),
    os.path.join(APP, "fix_interests_and_avatar_click.py"),
    os.path.join(APP, "Integrations"),
    os.path.join(APP, "Project"),
    os.path.join(APP, "Webhooks"),
    os.path.join(APP, "cat"),
    os.path.join(APP, "^C"),
]
removed = 0
for f in LEFTOVERS:
    if os.path.exists(f):
        os.remove(f)
        print(f"   삭제: {os.path.relpath(f, ROOT)}")
        removed += 1
print(f"   leftover 파일 {removed}개 삭제 완료")

print("\n✅ 패치 적용 완료. 다음 순서로 진행하세요:")
print("1) cd malbeot-app && npm install")
print("2) node -e \"console.log(JSON.stringify(require('web-push').generateVAPIDKeys()))\" 로 VAPID 키 생성")
print("3) .env에 VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY 추가 (VAPID_SUBJECT는 생략 가능, 기본값 사용)")
print("4) Render 대시보드 환경변수에도 동일하게 VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY 추가")
print("5) node -c server.js 로 문법 재확인 후 git add -A && git commit")
