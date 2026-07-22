const express = require('express');
const http = require('http');
const path = require('path');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

app.use(express.static(path.join(__dirname, 'public')));

let users = {};
let posts = [];
let chats = {};
let socketToUser = {};
let userToSocket = {};

const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000;
const genId = (p) => `${p}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
const roomIdFor = (a, b) => [a, b].sort().join('_room_');

function broadcastUsers() { io.emit('users:updated'); }
function broadcastPosts() { io.emit('posts:updated'); }

io.on('connection', (socket) => {

  socket.on('auth:login', (data, cb) => {
    let user = Object.values(users).find(u => u.phone === data.phone);
    if (!user) {
      user = {
        id: genId('u'),
        phone: data.phone,
        nickname: data.nickname,
        region: data.region,
        gender: data.gender,
        age: parseInt(data.age, 10),
        bio: data.bio || '반갑습니다!',
        photos: data.photos || [],
        points: 100,
        isOnline: true,
        lastSeen: Date.now(),
        blockedUserIds: [],
        lastPostDate: null,
        adWatchCountToday: 0,
        lastAdChargeDate: null
      };
      users[user.id] = user;
    } else {
      user.isOnline = true;
      user.lastSeen = Date.now();
    }
    socketToUser[socket.id] = user.id;
    userToSocket[user.id] = socket.id;
    cb({ success: true, user });
    broadcastUsers();
  });

  socket.on('profile:update', (data, cb) => {
    const userId = socketToUser[socket.id];
    const user = users[userId];
    if (!user) return cb({ success: false });
    Object.assign(user, data);
    cb({ success: true, user });
    broadcastUsers();
  });

  socket.on('users:get_list', (filters, cb) => {
    let list = Object.values(users);
    if (filters.region && filters.region !== '전체') list = list.filter(u => u.region === filters.region);
    if (filters.gender && filters.gender !== '전체') list = list.filter(u => u.gender === filters.gender);
    list = list.filter(u => u.age >= filters.ageMin && u.age <= filters.ageMax);
    cb({ success: true, users: list });
  });

  socket.on('posts:get_list', (filters, cb) => {
    const now = Date.now();
    let list = posts.filter(p => (now - (p.updatedAt || p.createdAt)) < THIRTY_DAYS);
    if (filters.region && filters.region !== '전체') list = list.filter(p => p.authorRegion === filters.region);
    if (filters.gender && filters.gender !== '전체') list = list.filter(p => p.authorGender === filters.gender);
    list = list.filter(p => p.authorAge >= filters.ageMin && p.authorAge <= filters.ageMax);
    list.sort((a, b) => (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt));
    cb({ success: true, posts: list });
  });

  socket.on('posts:create', (data, cb) => {
    const userId = socketToUser[socket.id];
    const user = users[userId];
    if (!user) return cb({ success: false });
    const todayStr = new Date().toISOString().slice(0, 10);
    let earned = false;
    if (user.lastPostDate !== todayStr) { user.points += 50; user.lastPostDate = todayStr; earned = true; }
    const post = {
      id: genId('p'),
      authorId: user.id, authorNickname: user.nickname, authorRegion: user.region,
      authorGender: user.gender, authorAge: user.age, authorPhoto: (user.photos && user.photos[0]) || '',
      content: data.content, photo: data.photo || '',
      createdAt: Date.now(), updatedAt: Date.now(), likes: 0, likedBy: [], comments: []
    };
    posts.unshift(post);
    cb({ success: true, post, earned, points: user.points });
    broadcastPosts();
  });

  socket.on('posts:update', (data, cb) => {
    const userId = socketToUser[socket.id];
    const post = posts.find(p => p.id === data.id);
    if (!post || post.authorId !== userId) return cb({ success: false });
    post.content = data.content;
    post.photo = data.photo || '';
    post.updatedAt = Date.now();
    cb({ success: true, post });
    broadcastPosts();
  });

  socket.on('posts:delete', (data, cb) => {
    const userId = socketToUser[socket.id];
    const idx = posts.findIndex(p => p.id === data.id && p.authorId === userId);
    if (idx === -1) return cb({ success: false });
    posts.splice(idx, 1);
    cb({ success: true });
    broadcastPosts();
  });

  socket.on('posts:like', (data, cb) => {
    const userId = socketToUser[socket.id];
    const post = posts.find(p => p.id === data.id);
    if (!post) return cb({ success: false });
    if (!post.likedBy) post.likedBy = [];
    const i = post.likedBy.indexOf(userId);
    if (i !== -1) { post.likedBy.splice(i, 1); post.likes = Math.max(0, (post.likes || 1) - 1); }
    else { post.likedBy.push(userId); post.likes = (post.likes || 0) + 1; }
    cb({ success: true, likes: post.likes, liked: i === -1 });
    broadcastPosts();
  });

  socket.on('comments:add', (data, cb) => {
    const userId = socketToUser[socket.id];
    const user = users[userId];
    const post = posts.find(p => p.id === data.postId);
    if (!post || !user) return cb({ success: false });
    if (!post.comments) post.comments = [];
    const comment = {
      id: genId('c'), authorId: user.id, authorNickname: user.nickname,
      content: data.content, parentId: data.parentId || null,
      createdAt: Date.now(), updatedAt: Date.now()
    };
    post.comments.push(comment);
    cb({ success: true, comment });
    broadcastPosts();
  });

  socket.on('comments:edit', (data, cb) => {
    const userId = socketToUser[socket.id];
    const post = posts.find(p => p.id === data.postId);
    const c = post && (post.comments || []).find(x => x.id === data.commentId);
    if (!c || c.authorId !== userId) return cb({ success: false });
    c.content = data.content;
    c.updatedAt = Date.now();
    cb({ success: true });
    broadcastPosts();
  });

  socket.on('comments:delete', (data, cb) => {
    const userId = socketToUser[socket.id];
    const post = posts.find(p => p.id === data.postId);
    if (!post) return cb({ success: false });
    const c = (post.comments || []).find(x => x.id === data.commentId);
    if (!c || c.authorId !== userId) return cb({ success: false });
    post.comments = post.comments.filter(x => x.id !== data.commentId && x.parentId !== data.commentId);
    cb({ success: true });
    broadcastPosts();
  });

  socket.on('chat:get_list', (cb) => {
    const userId = socketToUser[socket.id];
    const list = Object.values(chats)
      .filter(r => r.userIds.includes(userId))
      .map(r => {
        const otherId = r.userIds.find(id => id !== userId);
        return { roomId: r.roomId, targetUser: users[otherId], messages: r.messages };
      });
    cb({ success: true, rooms: list });
  });

  socket.on('chat:start_or_send', (data, cb) => {
    const userId = socketToUser[socket.id];
    const user = users[userId];
    const target = users[data.targetId];
    if (!user || !target) return cb({ success: false, message: '대상 사용자를 찾을 수 없습니다.' });
    if ((user.blockedUserIds || []).includes(target.id) || (target.blockedUserIds || []).includes(user.id)) {
      return cb({ success: false, message: '차단된 상대와는 대화할 수 없습니다.' });
    }
    const roomId = roomIdFor(user.id, target.id);
    let room = chats[roomId];
    const isNew = !room;
    if (isNew) {
      if (user.points < 50) return cb({ success: false, needPoints: true });
      user.points -= 50;
      room = chats[roomId] = {
        roomId, userIds: [user.id, target.id],
        messages: [{ senderId: 'system', text: '대화가 시작되었습니다. (쌀 50개 차감)', timestamp: Date.now() }]
      };
    }
    const msg = { senderId: user.id, text: data.text, timestamp: Date.now() };
    room.messages.push(msg);
    cb({ success: true, roomId, points: user.points });
    room.userIds.forEach(uid => {
      const sId = userToSocket[uid];
      if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg });
    });
    broadcastUsers();
  });

  socket.on('chat:send_message', (data) => {
    const userId = socketToUser[socket.id];
    const room = chats[data.roomId];
    if (!room || !room.userIds.includes(userId)) return;
    const msg = { senderId: userId, text: data.text, timestamp: Date.now() };
    room.messages.push(msg);
    room.userIds.forEach(uid => {
      const sId = userToSocket[uid];
      if (sId) io.to(sId).emit('chat:new_message', { roomId: room.roomId, message: msg });
    });
  });

  socket.on('chat:send_image', (data) => {
    const userId = socketToUser[socket.id];
    const room = chats[data.roomId];
    if (!room || !room.userIds.includes(userId)) return;
    const msg = { senderId: userId, type: 'image', data: data.image, timestamp: Date.now() };
    room.messages.push(msg);
    room.userIds.forEach(uid => {
      const sId = userToSocket[uid];
      if (sId) io.to(sId).emit('chat:new_message', { roomId: room.roomId, message: msg });
    });
  });

  socket.on('chat:end', (roomId, cb) => {
    const userId = socketToUser[socket.id];
    const room = chats[roomId];
    if (room) {
      const otherId = room.userIds.find(id => id !== userId);
      const sId = userToSocket[otherId];
      if (sId) io.to(sId).emit('chat:ended_notify', { roomId });
      delete chats[roomId];
    }
    if (cb) cb({ success: true });
  });

  socket.on('user:block', (targetId, cb) => {
    const userId = socketToUser[socket.id];
    const user = users[userId];
    if (!user) return cb && cb({ success: false });
    if (!user.blockedUserIds) user.blockedUserIds = [];
    if (!user.blockedUserIds.includes(targetId)) user.blockedUserIds.push(targetId);
    const roomId = roomIdFor(userId, targetId);
    if (chats[roomId]) {
      const sId = userToSocket[targetId];
      if (sId) io.to(sId).emit('chat:blocked_notify', { roomId });
      delete chats[roomId];
    }
    cb && cb({ success: true });
  });

  socket.on('user:report', (data, cb) => {
    console.log('[신고 접수]', new Date().toISOString(), data);
    cb && cb({ success: true });
  });

  socket.on('disconnect', () => {
    const userId = socketToUser[socket.id];
    if (userId && users[userId]) {
      users[userId].isOnline = false;
      users[userId].lastSeen = Date.now();
      broadcastUsers();
    }
    delete socketToUser[socket.id];
  });
});

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => console.log(`말벗 서버 실행 중: http://localhost:${PORT}`));