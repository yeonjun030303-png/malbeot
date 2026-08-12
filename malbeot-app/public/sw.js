// 말벗 웹 푸시 서비스워커
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
