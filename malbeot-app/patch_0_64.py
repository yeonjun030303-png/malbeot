# -*- coding: utf-8 -*-
import re, sys

def patch_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    applied = 0
    for old, new, label in replacements:
        count = content.count(old)
        if count == 1:
            content = content.replace(old, new)
            applied += 1
            print(f"완료: {label}")
        elif count == 0:
            print(f"매치 0건(이미 적용되었거나 코드가 변경됨): {label}")
        else:
            print(f"매치 {count}건(고유하지 않음, 건너뜀): {label}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return applied

mod_old = """// imageInput: 이미지 파일의 Buffer 또는 data URI 문자열(data:image/...;base64,...)
async function checkImageNsfw(imageInput) {
  const task = nsfwQueue.then(async () => {
    const rss = currentRssMb();
    if (rss >= MEMORY_GUARD_RSS_MB) {
      console.warn(`NSFW 검사 스킵(메모리 보호): 현재 RSS ${rss.toFixed(0)}MB`);
      return { isNsfw: false, score: 0, error: `메모리 보호로 검사 스킵(RSS ${rss.toFixed(0)}MB, 통과 처리)` };
    }
    try {
      return await runNsfwCheck(imageInput);
    } catch (err) {
      console.error('NSFW 검사 중 오류:', err);
      // 검사 실패 시 안전하게 통과시킬지 차단할지는 정책 결정 필요 (기본: 통과)
      return { isNsfw: false, score: 0, error: err.message };
    }
  });
  // 이번 검사가 실패하더라도 큐 자체는 끊기지 않고 다음 검사로 이어지게 함
  nsfwQueue = task.catch(() => {});
  return task;
}"""

mod_new = """// imageInput: 이미지 파일의 Buffer 또는 data URI 문자열(data:image/...;base64,...)
const NSFW_CHECK_TIMEOUT_MS = 12000; // 0-64: 검사 1건이 이 시간을 넘기면 포기하고 통과 처리(큐가 영구히 막히는 것 방지)

function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((resolve) => {
    timer = setTimeout(() => {
      console.warn(`NSFW 검사 타임아웃(${ms}ms 초과, 통과 처리): ${label}`);
      resolve({ isNsfw: false, score: 0, error: `타임아웃(${ms}ms) - 통과 처리` });
    }, ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

async function checkImageNsfw(imageInput) {
  // 0-64: 이번 검사 결과를 기다리는 것과 별개로, 큐는 타임아웃 시점에 무조건 다음으로 넘어가게 함
  // (기존에는 runNsfwCheck가 응답 없이 멈추면 큐 전체가 영구히 막혀서 이후의 모든 사진 전송/프로필저장이
  //  같이 멈추는 문제가 있었음 - 채팅 사진전송/프로필 사진저장이 동시에 "먹통"이 되던 버그의 원인)
  const task = nsfwQueue.then(async () => {
    const rss = currentRssMb();
    if (rss >= MEMORY_GUARD_RSS_MB) {
      console.warn(`NSFW 검사 스킵(메모리 보호): 현재 RSS ${rss.toFixed(0)}MB`);
      return { isNsfw: false, score: 0, error: `메모리 보호로 검사 스킵(RSS ${rss.toFixed(0)}MB, 통과 처리)` };
    }
    try {
      return await withTimeout(runNsfwCheck(imageInput), NSFW_CHECK_TIMEOUT_MS, 'checkImageNsfw');
    } catch (err) {
      console.error('NSFW 검사 중 오류:', err);
      // 검사 실패 시 안전하게 통과시킬지 차단할지는 정책 결정 필요 (기본: 통과)
      return { isNsfw: false, score: 0, error: err.message };
    }
  });
  // 이번 검사가 실패/타임아웃되더라도 큐 자체는 끊기지 않고 다음 검사로 이어지게 함
  nsfwQueue = task.catch(() => {});
  return task;
}"""

srv_send_image_old = """  socket.on('chat:send_image', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return cb && cb({ success: false });
      const nsfwResult = await checkImageNsfw(data.image);
      if (nsfwResult.isNsfw) return cb && cb({ success: false, blocked: true, message: '부적절한 사진으로 감지되어 전송할 수 없습니다.' });
      const msg = await addMessage(data.roomId, { senderId: userId, type: 'image', data: data.image, timestamp: Date.now(), read: false });
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
        else if (uid !== userId) sendWebPush(uid, { title: (sender && sender.nickname) || '말벗', body: '사진을 보냈습니다', type: 'chat', roomId: data.roomId });
      });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });"""

srv_send_image_new = """  socket.on('chat:send_image', async (data, cb) => {
    // 0-64: cb를 두 번 이상 부르지 않도록 가드 + 어떤 경우에도 15초 안에는 반드시 cb가 호출되도록 안전망
    let responded = false;
    const safeCb = (res) => { if (responded) return; responded = true; cb && cb(res); };
    const hardTimeout = setTimeout(() => safeCb({ success: false, message: '서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.' }), 15000);
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) { clearTimeout(hardTimeout); return safeCb({ success: false }); }
      const nsfwResult = await checkImageNsfw(data.image);
      if (nsfwResult.isNsfw) { clearTimeout(hardTimeout); return safeCb({ success: false, blocked: true, message: '부적절한 사진으로 감지되어 전송할 수 없습니다.' }); }
      const msg = await addMessage(data.roomId, { senderId: userId, type: 'image', data: data.image, timestamp: Date.now(), read: false });
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
        else if (uid !== userId) sendWebPush(uid, { title: (sender && sender.nickname) || '말벗', body: '사진을 보냈습니다', type: 'chat', roomId: data.roomId });
      });
      clearTimeout(hardTimeout);
      safeCb({ success: true });
    } catch (e) { console.error(e); clearTimeout(hardTimeout); safeCb({ success: false }); }
  });"""

srv_profile_old = """  socket.on('profile:update', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      if (data.nickname && containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      if (data.nickname) {
        data.nicknameFiltered = containsBannedWord(data.nickname);
      }

      // 0-43: 이미 검사를 통과한 기존 사진은 매번 재검사하지 않고, 새로 추가/변경된 사진만 검사함
      // (사진 5장 전부를 저장할 때마다 재검사하면 서버 메모리 부담이 커져 Render에서 502/재시작이 발생할 수 있었음)
      if (data.photos && data.photos.length) {
        const prevPhotos = user.photos || [];
        for (const photoData of data.photos) {
          if (!photoData) continue;
          if (prevPhotos.includes(photoData)) continue; // 기존에 이미 검사 통과한 사진은 스킵
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
  });"""

srv_profile_new = """  socket.on('profile:update', async (data, cb) => {
    // 0-64: cb 이중호출 방지 + 어떤 이유로든 20초 안에는 반드시 응답이 가도록 안전망
    // (NSFW 검사 큐가 막히거나 DB 저장이 지연되면 클라이언트가 "저장 중..." 상태로 영원히 멈추고,
    //  새로고침해도 실제로는 저장이 안 된 상태로 남는 버그의 원인이었음)
    let responded = false;
    const safeCb = (res) => { if (responded) return; responded = true; cb && cb(res); };
    const hardTimeout = setTimeout(() => safeCb({ success: false, message: '서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.' }), 20000);
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) { clearTimeout(hardTimeout); return safeCb({ success: false }); }

      if (data.nickname && containsBannedWord(data.nickname) && data.confirmed !== true) {
        clearTimeout(hardTimeout); return safeCb({ success: false, needsConfirm: true });
      }
      if (data.nickname) {
        data.nicknameFiltered = containsBannedWord(data.nickname);
      }

      // 0-43: 이미 검사를 통과한 기존 사진은 매번 재검사하지 않고, 새로 추가/변경된 사진만 검사함
      // (사진 5장 전부를 저장할 때마다 재검사하면 서버 메모리 부담이 커져 Render에서 502/재시작이 발생할 수 있었음)
      if (data.photos && data.photos.length) {
        const prevPhotos = user.photos || [];
        for (const photoData of data.photos) {
          if (!photoData) continue;
          if (prevPhotos.includes(photoData)) continue; // 기존에 이미 검사 통과한 사진은 스킵
          const nsfwResult = await checkImageNsfw(photoData);
          if (nsfwResult.isNsfw) { clearTimeout(hardTimeout); return safeCb({ success: false, message: '부적절한 사진이 포함되어 있어 변경할 수 없습니다.' }); }
        }
      }

      // 사진 구성(순서/개수)이 바뀌면 인덱스 기반 사진별 좋아요가 엉뚱한 사진을 가리킬 수 있어
      // 안전하게 초기화함(좋아요 자체가 사라지는 게 아니라 새 구성 기준으로 다시 쌓이는 것)
      const photosChanged = data.photos && JSON.stringify(data.photos) !== JSON.stringify(user.photos || []);

      Object.assign(user, data, { profileUpdatedAt: Date.now() });
      if (photosChanged) user.photoLikes = {};
      await saveUser(user);
      clearTimeout(hardTimeout);
      safeCb({ success: true, user: { ...user, isAdmin: isAdmin(user) } });
      broadcastUsers();
    } catch (e) { console.error(e); clearTimeout(hardTimeout); safeCb({ success: false }); }
  });"""

print("=== moderation.js 패치 ===")
patch_file('moderation.js', [(mod_old, mod_new, 'NSFW 검사 큐 타임아웃 추가')])

print("=== server.js 패치 ===")
patch_file('server.js', [
    (srv_send_image_old, srv_send_image_new, 'chat:send_image 핸들러 안전망 타임아웃'),
    (srv_profile_old, srv_profile_new, 'profile:update 핸들러 안전망 타임아웃'),
])

print("완료")
