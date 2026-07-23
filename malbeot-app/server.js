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
const io = new Server(server, { cors: { origin: '*' } });
app.use(express.static(path.join(__dirname, 'public')));

let socketToUser = {};
let userToSocket = {};

const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000;
const genId = (p) => `${p}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
const roomIdFor = (a, b) => [a, b].sort().join('_room_');

async function getAllUsers() {
  const snap = await db.ref('users').once('value');
  return snap.val() || {};
}
async function getUser(id) {
  const snap = await db.ref(`users/${id}`).once('value');
  return snap.val();
}
async function saveUser(user) {
  await db.ref(`users/${user.id}`).set(user);
}
async function getAllPosts() {
  const snap = await db.ref('posts').once('value');
  const val = snap.val() || {};
  return Object.values(val).map(p => ({
    ...p,
    likedBy: p.likedBy || [],
    comments: p.comments ? Object.values(p.comments) : []
  }));
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

function broadcastUsers() { io.emit('users:updated'); }
function broadcastPosts() { io.emit('posts:updated'); }

io.on('connection', (socket) => {

  socket.on('auth:login', async (data, cb) => {
    try {
      const users = await getAllUsers();
      let user = Object.values(users).find(u => u.phone === data.phone);
      if (!user) {
        user = {
          id: genId('u'), phone: data.phone, nickname: data.nickname,
          region: data.region, gender: data.gender, age: parseInt(data.age, 10),
          bio: data.bio || '반갑습니다!', photos: data.photos || [], points: 100,
          isOnline: true, lastSeen: Date.now(), blockedUserIds: [],
          lastPostDate: null, adWatchCountToday: 0, lastAdChargeDate: null
        };
      } else {
        user.isOnline = true;
        user.lastSeen = Date.now();
      }
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      cb({ success: true, user });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('profile:update', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });
      Object.assign(user, data);
      await saveUser(user);
      cb({ success: true, user });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('users:get_list', async (filters, cb) => {
    try {
      const users = await getAllUsers();
      let list = Object.values(users);
      if (filters.region && filters.region !== '전체') list = list.filter(u => u.region === filters.region);
      if (filters.gender && filters.gender !== '전체') list = list.filter(u => u.gender === filters.gender);
      list = list.filter(u => u.age >= filters.ageMin && u.age <= filters.ageMax);
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  socket.on('posts:get_list', async (filters, cb) => {
    try {
      const now = Date.now();
      let list = (await getAllPosts()).filter(p => (now - (p.updatedAt || p.createdAt)) < THIRTY_DAYS);
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
        id: genId('p'), authorId: user.id, authorNickname: user.nickname,
        authorRegion: user.region, authorGender: user.gender, authorAge: user.age,
        authorPhoto: (user.photos && user.photos[0]) || '',
        content: data.content, photo: data.photo || '',
        createdAt: Date.now(), updatedAt: Date.now(), likes: 0, likedBy: [], comments: {}
      };
      await savePost(post);
      cb({ success: true, post, earned, points: user.points });
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
      cb({ success: true, post });
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
      if (i !== -1) { post.likedBy.splice(i, 1); post.likes = Math.max(0, (post.likes || 1) - 1); }
      else { post.likedBy.push(userId); post.likes = (post.likes || 0) + 1; }
      await savePost(post);
      cb({ success: true, likes: post.likes, liked: i === -1 });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:add', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      const post = await getPost(data.postId);
      if (!post || !user) return cb({ success: false });
      const commentId = genId('c');
      const comment = {
        id: commentId, authorId: user.id, authorNickname: user.nickname,
        content: data.content, parentId: data.parentId || null,
        createdAt: Date.now(), updatedAt: Date.now()
      };
      if (!post.comments) post.comments = {};
      post.comments[commentId] = comment;
      await savePost(post);
      cb({ success: true, comment });
      broadcastPosts();
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
        rooms.push({ roomId, targetUser, messages });
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
      cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg });
      });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('chat:send_message', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return;
      const msg = { senderId: userId, text: data.text, timestamp: Date.now() };
      await addMessage(data.roomId, msg);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg });
      });
    } catch (e) { console.error(e); }
  });

  socket.on('chat:send_image', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return;
      const msg = { senderId: userId, type: 'image', data: data.image, timestamp: Date.now() };
      await addMessage(data.roomId, msg);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg });
      });
    } catch (e) { console.error(e); }
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