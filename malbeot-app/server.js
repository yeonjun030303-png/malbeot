require('dotenv').config();
const express = require('express');
const http = require('http');
const path = require('path');
const { Server } = require('socket.io');
const admin = require('firebase-admin');

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: process.env.FIREBASE_DB_URL
});
const db = admin.database();

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' }, maxHttpBufferSize: 1.5e7 });
app.use(express.static(path.join(__dirname, 'public')));

// 상시 구동 확인용 헬스체크 엔드포인트 (UptimeRobot 등 외부 핑 서비스로 주기적으로 호출하면
// 호스팅 서비스가 무접속 상태에서 슬립 모드로 전환되는 것을 막는 데 사용할 수 있음)
app.get('/health', (req, res) => res.status(200).send('ok'));

let socketToUser = {};
let userToSocket = {};

const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000;
const genId = (p) => `${p}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
const roomIdFor = (a, b) => [a, b].sort().join('_room_');

async function getAllUsers() {
  const snap = await db.ref('users').once('value');
  return snap.val() || {};
}
async function findUserByPhone(phone) {
  const users = await getAllUsers();
  return Object.values(users).find(u => u.phone === phone);
}
async function getUser(id) {
  const snap = await db.ref(`users/${id}`).once('value');
  return snap.val();
}
async function saveUser(user) {
  await db.ref(`users/${user.id}`).set(user);
}
async function getRawPosts() {
  const snap = await db.ref('posts').once('value');
  const val = snap.val() || {};
  return Object.values(val);
}
async function getPost(id) {
  const snap = await db.ref(`posts/${id}`).once('value');
  return snap.val();
}
async function savePost(post) {
  await db.ref(`posts/${post.id}`).set(post);
}
async function deletePostDb(id) {
  await db.ref(`posts/${id}`).remove();
}
async function getRoom(roomId) {
  const snap = await db.ref(`chats/${roomId}`).once('value');
  return snap.val();
}
async function saveRoomMeta(roomId, meta) {
  await db.ref(`chats/${roomId}`).update(meta);
}
async function addMessage(roomId, msg) {
  const ref = db.ref(`chats/${roomId}/messages`).push();
  await ref.set(msg);
}
async function deleteRoom(roomId) {
  await db.ref(`chats/${roomId}`).remove();
}
async function setReadAt(roomId, userId, ts) {
  await db.ref(`chats/${roomId}/readAt/${userId}`).set(ts);
}

// 게시물/댓글에 작성자의 "현재" 닉네임/지역/성별/나이/사진을 실시간으로 붙여주는 함수
// -> 유저가 닉네임을 바꾸면 예전 글에도 자동으로 새 닉네임이 반영됨
async function enrichPosts(rawPosts) {
  const users = await getAllUsers();
  return rawPosts.map(p => {
    const author = users[p.authorId] || {};
    const rawComments = p.comments ? Object.values(p.comments) : [];
    const comments = rawComments.map(c => {
      const cu = users[c.authorId] || {};
      return { ...c, authorNickname: cu.nickname || '(탈퇴한 사용자)' };
    });
    return {
      ...p,
      authorNickname: author.nickname || '(탈퇴한 사용자)',
      authorRegion: author.region || '',
      authorGender: author.gender || 'female',
      authorAge: author.age || 0,
      authorPhoto: (author.photos && author.photos[0]) || '',
      comments
    };
  });
}

function broadcastUsers() { io.emit('users:updated'); }
function broadcastPosts() { io.emit('posts:updated'); }

// 특정 유저에게만 알림을 보냄 (그 유저가 접속 중일 때만 전송됨)
function notifyUser(userId, payload) {
  if (!userId) return;
  const sId = userToSocket[userId];
  if (sId) io.to(sId).emit('notify:new', payload);
}

io.on('connection', (socket) => {

  // 전화번호만으로 로그인 (세션 자동복구 + "로그인" 버튼 둘 다 이걸 씀)
  socket.on('auth:login', async (data, cb) => {
    try {
      const user = await findUserByPhone(data.phone);
      if (!user) return cb({ success: false, notFound: true });
      user.isOnline = true;
      user.lastSeen = Date.now();
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      cb({ success: true, user });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 회원가입 (이미 등록된 번호면 거부)
  socket.on('auth:signup', async (data, cb) => {
    try {
      const existing = await findUserByPhone(data.phone);
      if (existing) return cb({ success: false, alreadyExists: true });
      const user = {
        id: genId('u'), phone: data.phone, nickname: data.nickname,
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),
        bio: data.bio || '반갑습니다!', photos: data.photos || [], points: 100,
        isOnline: true, lastSeen: Date.now(), blockedUserIds: [],
        lastPostDate: null, adWatchCountToday: 0, lastAdChargeDate: null,
        profileUpdatedAt: Date.now()
      };
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      cb({ success: true, user });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 회원가입 전 번호 중복 체크
  socket.on('auth:check_phone', async (data, cb) => {
    try {
      const user = await findUserByPhone(data.phone);
      cb({ exists: !!user });
    } catch (e) { console.error(e); cb({ exists: false }); }
  });

  socket.on('profile:update', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });
      Object.assign(user, data, { profileUpdatedAt: Date.now() });
      await saveUser(user);
      cb({ success: true, user });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 홈 리스트: 나 자신 포함, 프로필 수정 최신순 정렬
  socket.on('users:get_list', async (filters, cb) => {
    try {
      const users = await getAllUsers();
      let list = Object.values(users);
      if (filters.region && filters.region !== '전체') list = list.filter(u => u.region === filters.region);
      if (filters.gender && filters.gender !== '전체') list = list.filter(u => u.gender === filters.gender);
      list = list.filter(u => u.age >= filters.ageMin && u.age <= filters.ageMax);
      list.sort((a, b) => (b.profileUpdatedAt || b.lastSeen || 0) - (a.profileUpdatedAt || a.lastSeen || 0));
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  socket.on('posts:get_list', async (filters, cb) => {
    try {
      const now = Date.now();
      let list = await enrichPosts(await getRawPosts());
      list = list.filter(p => (now - (p.updatedAt || p.createdAt)) < THIRTY_DAYS);
      if (filters.region && filters.region !== '전체') list = list.filter(p => p.authorRegion === filters.region);
      if (filters.gender && filters.gender !== '전체') list = list.filter(p => p.authorGender === filters.gender);
      list = list.filter(p => p.authorAge >= filters.ageMin && p.authorAge <= filters.ageMax);
      list.sort((a, b) => (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt));
      cb({ success: true, posts: list });
    } catch (e) { console.error(e); cb({ success: false, posts: [] }); }
  });

  socket.on('posts:create', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });
      const todayStr = new Date().toISOString().slice(0, 10);
      let earned = false;
      if (user.lastPostDate !== todayStr) { user.points += 50; user.lastPostDate = todayStr; earned = true; }
      await saveUser(user);
      const post = {
        id: genId('p'), authorId: user.id,
        content: data.content, photo: data.photo || '',
        createdAt: Date.now(), updatedAt: Date.now(), likes: 0, likedBy: [], comments: {}
      };
      await savePost(post);
      cb({ success: true, earned, points: user.points });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:update', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post || post.authorId !== userId) return cb({ success: false });
      post.content = data.content;
      post.photo = data.photo || '';
      post.updatedAt = Date.now();
      await savePost(post);
      cb({ success: true });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:delete', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post || post.authorId !== userId) return cb({ success: false });
      await deletePostDb(data.id);
      cb({ success: true });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:like', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post) return cb({ success: false });
      if (!post.likedBy) post.likedBy = [];
      const i = post.likedBy.indexOf(userId);
      let liked = false;
      if (i !== -1) { post.likedBy.splice(i, 1); post.likes = Math.max(0, (post.likes || 1) - 1); }
      else { post.likedBy.push(userId); post.likes = (post.likes || 0) + 1; liked = true; }
      await savePost(post);
      cb({ success: true, likes: post.likes, liked });
      broadcastPosts();
      if (liked && post.authorId && post.authorId !== userId) {
        const liker = await getUser(userId);
        const name = (liker && liker.nickname) || '누군가';
        notifyUser(post.authorId, { type: 'like', postId: post.id, text: `${name}님이 게시글에 공감하였습니다` });
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:add', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      if (!post) return cb({ success: false });
      const commentId = genId('c');
      const comment = {
        id: commentId, authorId: userId,
        content: data.content, parentId: data.parentId || null,
        createdAt: Date.now(), updatedAt: Date.now()
      };
      if (!post.comments) post.comments = {};
      const parentComment = data.parentId ? post.comments[data.parentId] : null;
      post.comments[commentId] = comment;
      await savePost(post);
      cb({ success: true });
      broadcastPosts();

      const commenter = await getUser(userId);
      const name = (commenter && commenter.nickname) || '누군가';
      if (parentComment) {
        if (parentComment.authorId && parentComment.authorId !== userId) {
          notifyUser(parentComment.authorId, { type: 'reply', postId: post.id, text: `${name}님이 내 댓글에 답글을 달았습니다` });
        }
      } else if (post.authorId && post.authorId !== userId) {
        notifyUser(post.authorId, { type: 'comment', postId: post.id, text: `${name}님이 게시글에 댓글을 달았습니다` });
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:edit', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      const c = post && post.comments && post.comments[data.commentId];
      if (!c || c.authorId !== userId) return cb({ success: false });
      c.content = data.content;
      c.updatedAt = Date.now();
      await savePost(post);
      cb({ success: true });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:delete', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      if (!post || !post.comments) return cb({ success: false });
      const c = post.comments[data.commentId];
      if (!c || c.authorId !== userId) return cb({ success: false });
      delete post.comments[data.commentId];
      Object.keys(post.comments).forEach(cid => {
        if (post.comments[cid].parentId === data.commentId) delete post.comments[cid];
      });
      await savePost(post);
      cb({ success: true });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('chat:get_list', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const snap = await db.ref('chats').once('value');
      const allChats = snap.val() || {};
      const rooms = [];
      for (const roomId of Object.keys(allChats)) {
        const room = allChats[roomId];
        if (!room.userIds || !room.userIds.includes(userId)) continue;
        const otherId = room.userIds.find(id => id !== userId);
        const targetUser = await getUser(otherId);
        const messages = room.messages ? Object.values(room.messages) : [];
        const readAt = room.readAt || {};
        rooms.push({ roomId, targetUser, messages, readAt });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });

  socket.on('chat:start_or_send', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      const target = await getUser(data.targetId);
      if (!user || !target) return cb({ success: false, message: '대상 사용자를 찾을 수 없습니다.' });
      if ((user.blockedUserIds || []).includes(target.id) || (target.blockedUserIds || []).includes(user.id)) {
        return cb({ success: false, message: '차단된 상대와는 대화할 수 없습니다.' });
      }
      const roomId = roomIdFor(user.id, target.id);
      let room = await getRoom(roomId);
      const isNew = !room;
      if (isNew) {
        if (user.points < 50) return cb({ success: false, needPoints: true });
        user.points -= 50;
        await saveUser(user);
        await saveRoomMeta(roomId, { roomId, userIds: [user.id, target.id] });
        await addMessage(roomId, { senderId: 'system', text: '대화가 시작되었습니다. (쌀 50개 차감)', timestamp: Date.now() });
      }
      const msg = { senderId: user.id, text: data.text, timestamp: Date.now() };
      await addMessage(roomId, msg);
      await setReadAt(roomId, user.id, Date.now());
      cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
      });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('chat:send_message', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return cb && cb({ success: false, message: '대화방을 찾을 수 없습니다.' });
      const msg = { senderId: userId, text: data.text, timestamp: Date.now() };
      await addMessage(data.roomId, msg);
      await setReadAt(data.roomId, userId, msg.timestamp);
      const sender = await getUser(userId);
      cb && cb({ success: true, message: msg });
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      });
    } catch (e) { console.error(e); cb && cb({ success: false, message: '메시지 전송 중 오류가 발생했습니다.' }); }
  });

  socket.on('chat:send_image', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return cb && cb({ success: false, message: '대화방을 찾을 수 없습니다.' });
      if (!data.image) return cb && cb({ success: false, message: '이미지 데이터가 비어 있습니다.' });
      const msg = { senderId: userId, type: 'image', data: data.image, timestamp: Date.now() };
      await addMessage(data.roomId, msg);
      await setReadAt(data.roomId, userId, msg.timestamp);
      const sender = await getUser(userId);
      cb && cb({ success: true, message: msg });
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      });
    } catch (e) { console.error(e); cb && cb({ success: false, message: '사진 전송 중 오류가 발생했습니다. (용량이 너무 클 수 있어요)' }); }
  });

  // 채팅방에 실제로 들어와서 메시지를 읽었을 때만 호출됨 (알림 확인만으로는 호출 안 됨)
  socket.on('chat:mark_read', async (roomId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(roomId);
      if (!room || !room.userIds.includes(userId)) return cb && cb({ success: false });
      const ts = Date.now();
      await setReadAt(roomId, userId, ts);
      cb && cb({ success: true, readAt: ts });
      const otherId = room.userIds.find(id => id !== userId);
      const sId = userToSocket[otherId];
      if (sId) io.to(sId).emit('chat:read_update', { roomId, readerId: userId, readAt: ts });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('chat:end', async (roomId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(roomId);
      if (room) {
        const otherId = room.userIds.find(id => id !== userId);
        const sId = userToSocket[otherId];
        if (sId) io.to(sId).emit('chat:ended_notify', { roomId });
        await deleteRoom(roomId);
      }
      if (cb) cb({ success: true });
    } catch (e) { console.error(e); if (cb) cb({ success: false }); }
  });

  socket.on('user:block', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb && cb({ success: false });
      if (!user.blockedUserIds) user.blockedUserIds = [];
      if (!user.blockedUserIds.includes(targetId)) user.blockedUserIds.push(targetId);
      await saveUser(user);
      const roomId = roomIdFor(userId, targetId);
      const room = await getRoom(roomId);
      if (room) {
        const sId = userToSocket[targetId];
        if (sId) io.to(sId).emit('chat:blocked_notify', { roomId });
        await deleteRoom(roomId);
      }
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('user:report', (data, cb) => {
    console.log('[신고 접수]', new Date().toISOString(), data);
    cb && cb({ success: true });
  });

  socket.on('disconnect', async () => {
    try {
      const userId = socketToUser[socket.id];
      if (userId) {
        const user = await getUser(userId);
        if (user) {
          user.isOnline = false;
          user.lastSeen = Date.now();
          await saveUser(user);
          broadcastUsers();
        }
      }
      delete socketToUser[socket.id];
    } catch (e) { console.error(e); }
  });
});

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => console.log(`말벗 서버 실행 중 (Firebase 연동): http://localhost:${PORT}`));