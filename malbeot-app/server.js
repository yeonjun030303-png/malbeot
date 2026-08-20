require('dotenv').config();
const express = require('express');
const http = require('http');
const path = require('path');
const { Server } = require('socket.io');
const admin = require('firebase-admin');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { checkImageNsfw, containsBannedWord, loadNsfwModel } = require('./moderation');
const webpush = require('web-push');

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: process.env.FIREBASE_DB_URL
});
const db = admin.database();

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

const app = express();
const server = http.createServer(app);
// CORS: .env에 ALLOWED_ORIGIN(예: https://본인도메인)을 설정하면 그 주소에서만 접속을 허용함.
// 설정 안 하면 개발 편의를 위해 전체 허용('*')으로 동작하되 경고를 남김 - 배포 전에 반드시 설정 권장.
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '*';
if (!process.env.ALLOWED_ORIGIN) {
  console.warn('[경고] ALLOWED_ORIGIN이 .env에 설정되어 있지 않아 모든 출처(*)를 허용합니다. 배포 시 실제 도메인으로 제한하는 것을 권장합니다.');
}
const io = new Server(server, { cors: { origin: ALLOWED_ORIGIN }, maxHttpBufferSize: 1.5e7 });
app.use(express.json()); // /api/reports 같은 REST 라우트가 req.body를 읽으려면 필요함 (신고 시스템 추가하며 필요해짐)
app.use(express.static(path.join(__dirname, 'public'), { dotfiles: 'allow' }));

// 신고 시스템 (메시지 신고 접수 + 관리자 조회/처리)
const reportsRouter = require('./reports');
app.use('/api/reports', reportsRouter);

// 상시 구동 확인용 헬스체크 엔드포인트 (UptimeRobot 등 외부 핑 서비스로 주기적으로 호출하면
// 호스팅 서비스가 무접속 상태에서 슬립 모드로 전환되는 것을 막는 데 사용할 수 있음)
app.get('/health', (req, res) => res.status(200).send('ok'));

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
});

// 단체채팅방 초대링크 (카카오 오픈채팅처럼 실제 URL로 들어오면 앱 내 페이지로 바로 진입)
// 지금은 웹뷰만 있어서 index.html을 그대로 내려주고, 클라이언트가 경로(/join/코드)를 그대로 읽어 로그인 후 자동 입장시킴.
// 주의: 절대 여기서 redirect하지 말 것 - 클라이언트가 location.pathname에서 '/join/코드' 패턴을 직접 파싱하기 때문에,
//       경로가 바뀌면(redirect로 '/?joinCode=...' 등으로) 클라이언트가 코드를 못 읽어 자동입장이 깨짐.
// TODO: 나중에 네이티브 앱이 생기면 여기서 User-Agent를 보고 앱 미설치 기기는 스토어로 리다이렉트하도록 확장할 것.
app.get('/join/:code', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

let socketToUser = {};
let userToSocket = {};

/* =====================================================================
   RevenueCat 웹훅 (구글 플레이/애플 앱스토어 인앱결제 완료 알림 수신)
   - RevenueCat 대시보드 > Project Settings > Integrations > Webhooks 에서
     이 서버의 주소(예: https://본인도메인/api/revenuecat-webhook)를 등록하고,
     "Authorization header value"에 아래 REVENUECAT_WEBHOOK_SECRET과 같은 값을 넣어야 함.
   - app_user_id는 클라이언트(iap-client.js)에서 Purchases.logIn(유저id)로 반드시
     연결되어 있어야, 여기서 어느 유저에게 쌀을 지급할지 알 수 있음.
   - 상품 ID(product_id)는 Play Console/App Store Connect에 등록한 ID와
     정확히 같아야 하며, points.html 등에서 쓰던 것과 동일하게 맞춰둠.
===================================================================== */
const POINTS_BY_PRODUCT = {
  points_1000: 1100, // 1000 + 10% 보너스
  points_3000: 3600, // 3000 + 20% 보너스
  points_5000: 6750  // 5000 + 35% 보너스
};

// 0-20: 유료 구독제(골드/플래티넘) 상품 - 자동결제(정기구독)가 아닌 14일권/1년권 "1회성 구매" 상품임.
// 상품ID/일수/등급/보너스쌀 값은 실제 Play 콘솔·App Store Connect·RevenueCat 대시보드에 등록한 상품과
// 정확히 같아야 함(실제 상품 등록/가격 확정은 코드 범위 밖 - 기존 쌀 상품과 동일하게 사용자가 직접 진행).
// 가격은 참고용 placeholder(1년권 = 14일권 26회분의 70%로 계산)이며 실제 판매가는 스토어 콘솔에서 확정함.
const SUBSCRIPTION_PRODUCTS = {
  sub_gold_14d:      { tier: 'gold',     days: 14,  points: 1000 },
  sub_platinum_14d:  { tier: 'platinum', days: 14,  points: 3000 },
  sub_gold_365d:     { tier: 'gold',     days: 365, points: 1000 },
  sub_platinum_365d: { tier: 'platinum', days: 365, points: 3000 }
};

app.post('/api/revenuecat-webhook', async (req, res) => {
  try {
    const authHeader = req.headers['authorization'] || '';
    if (!process.env.REVENUECAT_WEBHOOK_SECRET || authHeader !== `Bearer ${process.env.REVENUECAT_WEBHOOK_SECRET}`) {
      console.warn('[RevenueCat 웹훅] 인증 실패 - REVENUECAT_WEBHOOK_SECRET 설정을 확인하세요.');
      return res.status(403).send('forbidden');
    }
    const event = req.body && req.body.event;
    if (!event) return res.status(400).send('no event');

    // 구매/갱신 이벤트만 포인트 지급 대상. 환불(CANCELLATION 등)은 별도 처리하지 않고 로그만 남김
    // (환불정책상 이미 지급된 쌀 회수는 관리자가 수동 확인하도록 남겨둠)
    if (event.type !== 'INITIAL_PURCHASE' && event.type !== 'NON_RENEWING_PURCHASE' && event.type !== 'RENEWAL') {
      console.log('[RevenueCat 웹훅] 처리 대상 아닌 이벤트:', event.type);
      return res.status(200).send('ignored');
    }

    // 이벤트 중복 처리 방지 (RevenueCat이 같은 이벤트를 재전송할 수 있음)
    const eventId = event.id;
    if (eventId) {
      const already = await db.ref(`processedPurchaseEvents/${eventId}`).once('value');
      if (already.exists()) {
        console.log('[RevenueCat 웹훅] 이미 처리된 이벤트:', eventId);
        return res.status(200).send('duplicate');
      }
    }

    const userId = event.app_user_id;
    const productId = event.product_id;
    const subProduct = SUBSCRIPTION_PRODUCTS[productId];
    const grantPoints = subProduct ? subProduct.points : POINTS_BY_PRODUCT[productId];

    if (!userId || !grantPoints) {
      console.warn('[RevenueCat 웹훅] 알 수 없는 유저 또는 상품:', userId, productId);
      return res.status(200).send('unknown product or user');
    }

    const user = await getUser(userId);
    if (!user) {
      console.warn('[RevenueCat 웹훅] 유저를 찾을 수 없음:', userId);
      return res.status(200).send('user not found');
    }

    // 0-54: 1년권(365일 이상)은 쌀을 한번에 다 주지 않고 매달 1일 자동으로 나눠 지급함(재구매 유도).
    // 14일권 등 그 외 상품은 기존처럼 즉시 전액 지급.
    const isMonthlyPayout = subProduct && subProduct.days >= 365;
    if (!isMonthlyPayout) {
      user.points = (user.points || 0) + grantPoints;
    }

    // 0-20: 구독 상품이면 등급+만료일도 함께 갱신. 이미 활성 구독 중이면 남은 기간에 새로 산 기간을 이어붙임(연장).
    // 등급이 다르면(예: 골드 구독 중 플래티넘 구매) 더 높은 등급으로 올리고 남은 기간은 그대로 이어붙임.
    if (subProduct) {
      const now = Date.now();
      const prevSub = getActiveSubscription(user);
      const base = prevSub ? prevSub.expiresAt : now;
      const newTier = (prevSub && (SUBSCRIPTION_TIER_RANK[prevSub.tier] || 0) > (SUBSCRIPTION_TIER_RANK[subProduct.tier] || 0))
        ? prevSub.tier : subProduct.tier;
      user.subscription = {
        tier: newTier,
        expiresAt: base + subProduct.days * 24 * 60 * 60 * 1000,
        logoColorOn: (user.subscription && typeof user.subscription.logoColorOn === 'boolean') ? user.subscription.logoColorOn : true,
        badgeOn: (user.subscription && typeof user.subscription.badgeOn === 'boolean') ? user.subscription.badgeOn : true
      };
      // 0-54: 1년권 매월 지급 - lastGrantedMonth를 null로 둬서 grantMonthlySubscriptionBonusIfNeeded()가
      // 다음 체크(최대 1시간 이내)에 이번 달 몫을 바로 지급하게 함. 이후 매월 1일 자동 지급.
      if (isMonthlyPayout) {
        user.subscription.monthlyBonus = { amount: subProduct.points, lastGrantedMonth: null };
      } else if (user.subscription) {
        delete user.subscription.monthlyBonus;
      }
    }

    await saveUser(user);
    if (eventId) await db.ref(`processedPurchaseEvents/${eventId}`).set({ userId, productId, grantPoints, at: Date.now() });
    // 0-33: 유저가 나중에 "결제 내역" 화면에서 조회할 수 있도록 기록해둠(관리자가 테스트로 지급한 구독은 여기 안 남음 - 실제 결제 건만)
    // 0-54: 1년권은 이 시점엔 아직 포인트를 지급 안 했으므로(매달 나눠 지급) points를 0으로 기록함.
    // 실제 매월 지급분은 grantMonthlySubscriptionBonusIfNeeded()에서 별도로 purchaseHistory에 기록함.
    await db.ref(`purchaseHistory/${userId}`).push({
      productId,
      points: isMonthlyPayout ? 0 : grantPoints,
      subscriptionTier: subProduct ? subProduct.tier : null,
      subscriptionDays: subProduct ? subProduct.days : null,
      at: Date.now()
    });

    console.log(`[RevenueCat 웹훅] ${userId} 유저에게 ${isMonthlyPayout ? `구독(${subProduct.tier}, ${subProduct.days}일, 매달 ${grantPoints}개 지급 시작)` : `쌀 ${grantPoints}개 지급 완료${subProduct ? ` + 구독(${subProduct.tier}, ${subProduct.days}일)` : ''}`} (상품: ${productId})`);

    // 지금 접속 중인 유저라면 실시간으로 잔액+구독 상태를 갱신해줌 (접속 중이 아니면 다음 로그인 시 서버 데이터로 자동 반영됨)
    const sId = userToSocket[userId];
    if (sId) io.to(sId).emit('points:updated', { points: user.points, subscription: user.subscription || null });
    broadcastUsers();

    res.status(200).send('ok');
  } catch (e) {
    console.error('[RevenueCat 웹훅 오류]', e);
    res.status(500).send('error');
  }
});

// 회원가입 / 카카오 추가정보 입력 공통 검증: 닉네임 미입력, 나이가 숫자가 아니거나 비정상 범위(14~120)면 거부.
// (기존에는 나이를 검증 없이 parseInt만 해서, 이상한 값을 넣으면 NaN이 그대로 DB에 저장되는 문제가 있었음)
function validateProfileInput(data) {
  if (!data.nickname || !String(data.nickname).trim().length) return '닉네임을 입력해주세요.';
  const age = parseInt(data.age, 10);
  if (isNaN(age) || age < 14 || age > 120) return '나이를 올바르게 입력해주세요.';
  return null;
}

const THIRTY_DAYS = 30 * 24 * 60 * 60 * 1000;
const ONE_DAY = 24 * 60 * 60 * 1000;
const VOTE_MAX_OPTIONS = 6; // 투표(구 핫토픽/밸런스게임 통합) 항목 최대 개수
const WARNING_MESSAGE = '다른 사용자와의 대화(게시물, 댓글) 등 신고를 접수받아 검토한 결과, 부적절한 단어나 상대방이 불쾌할 수 있는 언행을 하여 경고했습니다. 다음에는 주의해 주세요.';
// 0-25: 관리자가 신고 처리 화면에서 수동으로 강제탈퇴시킬 때 쓰는 메시지(자동 임계값 처리는 하지 않음 - 관리자 판단으로만 실행)
const FORCE_WITHDRAW_MESSAGE = '신고 접수 내용을 검토한 결과, 이용약관 위반으로 계정이 강제 탈퇴 처리되었습니다. 재가입은 가능하나, 반복될 경우 재가입이 제한될 수 있습니다.';
const genId = (p) => `${p}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
const roomIdFor = (a, b) => [a, b].sort().join('_room_');

/* =====================================================================
   로그인 세션 (전화번호+비밀번호 / 카카오)
   - SESSION_SECRET: .env에 반드시 설정해야 함 (예: 아무 랜덤 문자열 32자 이상)
     설정 안 하면 서버가 매번 다른 임시 비밀키를 써서, 서버 재시작할 때마다
     기존에 로그인해있던 사람들이 전부 세션이 끊겨 재로그인하게 되니 주의.
   - SESSION_MAX_AGE: 세션(로그인 유지) 유효기간. "7일 이상 미접속 시 재로그인"
     요구사항에 맞춰 7일로 설정. 접속할 때마다 새 토큰을 발급(연장)하므로,
     7일 안에 한 번이라도 들어오면 계속 로그인 상태가 유지됨.
===================================================================== */
const SESSION_SECRET = process.env.SESSION_SECRET || 'dev_only_insecure_secret_please_set_env';
if (!process.env.SESSION_SECRET) {
  console.warn('[경고] SESSION_SECRET이 .env에 설정되어 있지 않습니다. 반드시 설정해주세요 (안 하면 서버 재시작마다 전체 로그아웃됨).');
}
const SESSION_MAX_AGE = '7d';

function issueSessionToken(userId) {
  return jwt.sign({ uid: userId }, SESSION_SECRET, { expiresIn: SESSION_MAX_AGE });
}
function verifySessionToken(token) {
  try { return jwt.verify(token, SESSION_SECRET); } catch (e) { return null; }
}
async function hashPassword(plain) {
  return bcrypt.hash(plain, 10);
}
async function comparePassword(plain, hash) {
  if (!hash) return false;
  return bcrypt.compare(plain, hash);
}

async function getAllUsers() {
  const snap = await db.ref('users').once('value');
  return snap.val() || {};
}
async function findUserByPhone(phone) {
  const users = await getAllUsers();
  return Object.values(users).find(u => u.phone === phone);
}
async function findUserByKakaoId(kakaoId) {
  const users = await getAllUsers();
  return Object.values(users).find(u => u.kakaoId === kakaoId);
}
async function getUser(id) {
  const snap = await db.ref(`users/${id}`).once('value');
  return snap.val();
}
async function saveUser(user) {
  await db.ref(`users/${user.id}`).set(user);
}
// 0-20: 유료 구독(골드/플래티넘) 헬퍼 - expiresAt이 지나지 않았을 때만 "활성 구독"으로 인정함
const SUBSCRIPTION_TIER_RANK = { gold: 1, platinum: 2 };
function getActiveSubscription(user) {
  const sub = user && user.subscription;
  if (!sub || !sub.tier || !sub.expiresAt || sub.expiresAt <= Date.now()) return null;
  return sub;
}
function hasTierAtLeast(user, minTier) {
  const sub = getActiveSubscription(user);
  if (!sub) return false;
  return (SUBSCRIPTION_TIER_RANK[sub.tier] || 0) >= (SUBSCRIPTION_TIER_RANK[minTier] || 0);
}
// 0-28: 방문자/좋아요 잠금화면(0-24)이 CSS 블러만으로 실제 데이터를 가려서, 개발자도구로 블러를 끄거나
// 네트워크 응답만 봐도 닉네임/사진 원본이 그대로 노출되는 문제가 있었음 - locked 상태일 때는 서버에서부터
// 닉네임은 마스킹하고 사진 원본 URL은 아예 내려보내지 않도록 함(클라이언트는 기본 실루엣 아이콘으로 대체)
function maskUserForLockedTeaser(u) {
  const nick = (u && u.nickname) || '';
  const masked = nick.length <= 1 ? '○' : nick[0] + '○'.repeat(Math.min(nick.length - 1, 2));
  return { id: u.id, nickname: masked, region: u.region, gender: u.gender, age: u.age };
}
// 요청의 실제 접속 IP를 추출 (Render 등 프록시 뒤에서는 x-forwarded-for 헤더 우선)
function getClientIp(socket) {
  const xff = socket.handshake.headers['x-forwarded-for'];
  if (xff) return String(xff).split(',')[0].trim();
  return socket.handshake.address || '';
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
  msg.id = ref.key;
  await ref.set(msg);
  return msg;
}
async function deleteRoom(roomId) {
  await db.ref(`chats/${roomId}`).remove();
}

// ===== 단체채팅방(오픈채팅 스타일) DB 헬퍼 =====
function generateInviteCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
  let code = '';
  for (let i = 0; i < 8; i++) code += chars[Math.floor(Math.random() * chars.length)];
  return code;
}
async function getGroupRoom(roomId) {
  const snap = await db.ref(`groupChats/${roomId}`).once('value');
  return snap.val();
}
async function addGroupMessage(roomId, msg) {
  const ref = db.ref(`groupChats/${roomId}/messages`).push();
  msg.id = ref.key;
  await ref.set(msg);
  return msg;
}
async function deleteGroupRoomDb(roomId) {
  await db.ref(`groupChats/${roomId}`).remove();
}
function emitToGroupMembers(memberIds, event, payload) {
  (memberIds || []).forEach(uid => {
    const sId = userToSocket[uid];
    if (sId) io.to(sId).emit(event, payload);
  });
}

// 신고(report)의 실제 대상(피신고자) 유저 ID를 유형별로 계산. 관리자 경고 기능에서 공용으로 사용.
async function getAccusedUserId(report) {
  if (!report) return null;
  if (report.type === 'post') {
    const p = await getPost(report.targetId);
    return p ? p.authorId : null;
  } else if (report.type === 'user') {
    return report.targetId;
  } else if (report.type === 'chat') {
    const room = await getRoom(report.targetId);
    return room && room.userIds ? room.userIds.find(uid => uid !== report.reporterUid) : null;
  } else if (report.type === 'comment') {
    const [postId, commentId] = (report.targetId || '').split('::');
    const p = postId ? await getPost(postId) : null;
    const c = p && p.comments && p.comments[commentId];
    return c ? c.authorId : null;
  }
  return null;
}
// 관리자에게 경고받은 내용을 다음 로그인 시 딱 1회만 강제 알림창으로 보여주기 위해 대기시켜둔 알림을 꺼내는 함수.
// (접속 중이었다면 admin:reports:resolve 처리 시점에 즉시 account:warned 소켓 이벤트로 보여주고 notified:true로 표시해둠)
async function popPendingWarningNotify(user) {
  if (user.pendingWarningNotify && !user.pendingWarningNotify.notified) {
    const info = { message: WARNING_MESSAGE };
    user.pendingWarningNotify.notified = true;
    await saveUser(user);
    return info;
  }
  return null;
}
// 대표사진이 아닌 다른 사진이 좋아요를 더 많이 받으면 "대표사진을 바꿔보세요"를 딱 1회(평생)만 알려주기 위해
// 대기시켜둔 알림을 꺼내는 함수. popPendingWarningNotify와 완전히 동일한 패턴(접속 중이면 즉시 소켓으로 보여주고
// notified:true 처리, 오프라인이면 다음 로그인 응답에 실어서 전달).
async function popPendingRepPhotoSuggest(user) {
  if (user.pendingRepPhotoSuggest && !user.pendingRepPhotoSuggest.notified) {
    const info = { photoIndex: user.pendingRepPhotoSuggest.photoIndex };
    user.pendingRepPhotoSuggest.notified = true;
    await saveUser(user);
    return info;
  }
  return null;
}

// data URL의 mime 타입을 보고 이미지/동영상을 구분 (video/* 이면 동영상)
function detectMediaType(dataUrl) {
  if (!dataUrl) return null;
  return /^data:video\//.test(dataUrl) ? 'video' : 'image';
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
      return {
        ...c,
        authorNickname: cu.nicknameFiltered ? '삭제된 닉네임입니다' : (cu.nickname || '(탈퇴한 사용자)'),
        authorPhoto: (cu.photos && cu.photos[0]) || '',
        authorGender: cu.gender || 'female',
        authorPhotoPosition: cu.photoPosition || null
      };
    });
    // viewedBy(조회자별 마지막 조회 시각)는 조회수 집계용 내부 데이터라 클라이언트로는 내려주지 않음
    const { viewedBy, ...postRest } = p;
    return {
      ...postRest,
      authorNickname: author.nicknameFiltered ? '삭제된 닉네임입니다' : (author.nickname || '(탈퇴한 사용자)'),
      authorRegion: author.region || '',
      authorGender: author.gender || 'female',
      authorAge: author.age || 0,
      authorPhoto: (author.photos && author.photos[0]) || '',
      authorPhotoPosition: author.photoPosition || null,
      mediaType: p.photo ? detectMediaType(p.photo) : null,
      viewCount: p.viewCount || 0,
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
  // 소켓 미접속(=앱이 꺼져있음) 상태일 때만 웹 푸시로 대신 알림 (앱 켜져있을 땐 인앱 알림으로 충분)
  else sendWebPush(userId, { title: payload.title || '말벗', body: payload.body || payload.text || '', type: payload.type || null, postId: payload.postId || null, userId: payload.userId || null });
}

// 내가 팔로우하는 사람이 새 글/스토리를 올리면 팔로워 전원에게 알림
// action: '작성' (새 글) 또는 '수정' (기존 글 수정)
async function notifyFollowersNewPost(author, post, action) {
  try {
    const followerIds = author.followerIds || [];
    if (!followerIds.length) return;
    const name = author.nickname || '누군가';
    const body = action === '수정' ? '게시글을 수정하였습니다' : '새로운 글을 작성하였습니다';
    followerIds.forEach(fid => {
      notifyUser(fid, { type: 'follow_post', postId: post.id, title: name, body });
    });
  } catch (e) { console.error('[팔로우 알림 오류]', e); }
}

// 각 유저가 등록해둔 키워드(notifyKeywords)가 게시글 내용에 포함되면 해당 유저에게 알림
// action: '등록' 또는 '수정'
async function notifyKeywordMatches(post, authorId, action) {
  try {
    const author = await getUser(authorId);
    const authorName = (author && author.nickname) || '누군가';
    const users = await getAllUsers();
    const content = post.content || '';
    Object.values(users).forEach(u => {
      if (!u || u.id === authorId) return;
      const keywords = u.notifyKeywords || [];
      const matched = keywords.find(k => k && content.includes(k));
      if (matched) {
        notifyUser(u.id, { type: 'keyword', postId: post.id, title: authorName, body: `'${matched}' 키워드가 포함된 글이 ${action}되었습니다` });
      }
    });
  } catch (e) { console.error('[키워드 알림 오류]', e); }
}

// ===== 정렬 카테고리 (기본순 / 인기순 / 거리순 / 조회수순) =====
// 게시글(커뮤니티) 정렬. list는 이미 최신순(기본순)으로 정렬된 상태로 들어온다고 가정.
function sortPostsByType(list, sortType, myRegion) {
  switch (sortType) {
    case 'popular': // 인기순: 좋아요 많은 순
      return [...list].sort((a, b) => (b.likes || 0) - (a.likes || 0));
    case 'distance': // 거리순: 같은 지역 우선, 그 안에서는 최신순
      if (!myRegion) return list;
      return [...list].sort((a, b) => {
        const aSame = a.authorRegion === myRegion ? 1 : 0;
        const bSame = b.authorRegion === myRegion ? 1 : 0;
        if (aSame !== bSame) return bSame - aSame;
        return (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt);
      });
    case 'views': // 조회수순
      return [...list].sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0));
    default: // 기본순
      return list;
  }
}

// 유저(홈) 정렬
function sortUsersByType(list, sortType, myRegion) {
  switch (sortType) {
    case 'popular': // 인기순: 팔로워 수 + 프로필 공감 수 합산
      return [...list].sort((a, b) => {
        const aScore = (a.followerIds ? a.followerIds.length : 0) + (a.profileLikedBy ? a.profileLikedBy.length : 0);
        const bScore = (b.followerIds ? b.followerIds.length : 0) + (b.profileLikedBy ? b.profileLikedBy.length : 0);
        return bScore - aScore;
      });
    case 'distance': // 거리순: 같은 지역 우선
      if (!myRegion) return list;
      return [...list].sort((a, b) => {
        const aSame = a.region === myRegion ? 1 : 0;
        const bSame = b.region === myRegion ? 1 : 0;
        if (aSame !== bSame) return bSame - aSame;
        return (b.profileUpdatedAt || b.lastSeen || 0) - (a.profileUpdatedAt || a.lastSeen || 0);
      });
    case 'views': // 유저 프로필 자체 조회수 데이터는 없어 인기순과 동일 기준으로 처리
      return sortUsersByType(list, 'popular', myRegion);
    default:
      return list;
  }
}

// ===== 말벗스토리 랜덤 알고리즘 =====
// 조회수가 높을수록 노출 가중치가 높아지되, 내가 이미 본 스토리는 가중치를 크게 낮추고
// 매 호출마다 랜덤값을 곱해 순서를 섞음 -> 아래/좌로 넘겨서 다시 호출할 때마다 다른 순서로 나옴
function weightedShuffleStories(stories, userId) {
  const withWeight = stories.map(s => {
    const viewed = userId && s.viewedBy && s.viewedBy[userId];
    const viewCount = s.viewCount || 0;
    let weight = viewCount + 1;
    if (viewed) weight = weight * 0.15; // 이미 본 스토리는 다시 뜰 확률을 크게 낮춤
    return { post: s, weight: weight * (0.5 + Math.random()) };
  });
  withWeight.sort((a, b) => b.weight - a.weight);
  return withWeight.map(w => w.post);
}

// ===== AI 말벗도우미 (매일 1회 자동 게시글 업로드) =====
const AI_BOT_ID = 'ai_malbeot_bot';

// 실제 유행곡/챌린지명을 그대로 언급하면 저작권 문제가 될 수 있어,
// 20~30대가 공감할 만한 순화된 일상 문구로 구성함 (필요하면 이 배열만 계속 늘려서 다양화 가능)
const AI_BOT_POST_TEMPLATES = [
  '오늘 날씨 완전 산책하기 좋은 날이네요! 다들 오늘 뭐하고 계신가요? 🍃',
  '요즘 다들 어떤 챌린지 하고 계세요? 저도 하나 배워보고 싶어요 😊',
  '점심시간! 오늘은 뭐 드셨나요? 저는 든든하게 챙겨 먹었어요 🍚',
  '주말에 다들 뭐 하실 계획이세요? 저는 재밌는 영상 찾아볼 예정이에요 🎬',
  '요즘 노래 뭐 듣고 계세요? 플레이리스트 추천 받아요 🎧',
  '오늘 하루도 다들 힘내세요! 소소한 행복 찾으면서 지내요 ✨',
  '커피 한 잔의 여유, 다들 즐기고 계신가요? ☕',
  '요즘 다들 취미 뭐 있으세요? 저도 새로운 취미 만들어보려고요!'
];

const AI_BOT_PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAMAAACahl6sAAAAYFBMVEX///+2wvONnO6Imu6Hl+yDleyBk+t/kup8kut8j+l7jul6jeh4i+h2ied0iOZzh+ZxhuVvg+RugeRrgONpf+JnfeFle+FkeuBieN9hd99fdt5ddN1actxYb9wAAP8AAACA6NMXAAAJhklEQVR42t3diXKbOhQAUCGwg9nBWxzb5f//8olVVws2WrClp860nTae6ORqvQhA7SYlBCWaym63i3bRNt+wRdYJOGRLBMtuLG5DkhDzigUHKfudoxDcl/WOvkSOQQKMtRxdCZ2BJBgbOH5ISVyAYGzs6MqXIQG25PiJf74IwdiaoyuH5DuQ0LbjcPiJPw/B2L6jK8lnIXgrh4EE2WBYdCRJ+inIxg5S8k9A8PaONE03hySfcaRpsS0Ef8qRptmGkOSDDlLyrSD4s44sy7aBfN6RZbF9SPgNR5YXtiH4K44sz1K7kG85umIT8k3Hasl7CPquI89jOxD8bUe+rssjDxxFbg5xwlEUpSnEEUdRVGYQZxxlWZpAQoccbyXIj3iQUulCQsccVakHSVxzVFWtBXHPUVWNBsRFBynKEEcdVawIcdXxIiTInf3gCkdd10oQhx2LEuSbY0mCvHPU8UpI4rhjISTom3lRPUfdrIJ44GhOKyCJB46mid9DvHA09VuIH46mOWpAnHQc49cQbxzH5iUk9MZByiuIT45XEK8cvAR94FzGNg6umyBvHafTWojrjtNZDvHOwYYEbXaObHvH6SiDhP45mJAgeUD8cEAJsn7O8pMOCcRPx/n8EuKRQ4CEnjqoBAkB8cvBQRJvHbMEcQHxzrEA8c9xvgFI4rFjCgmCAfHRcbmIED8dlzMP8dRxuc4Qvx2X65OBeOu4XC8Q4rHjeh0hie+Ovm2hPiB+O/q21UM8d/Rtq4N47xgh/juutw6C/Xd0IREhHjp+fyUQLx0SiJ+O3wuB/B8cJCSo/V84CGQTB0agBFJHDL7A3MFC7MUj4CCSeHAQM8ftBiH2HDFiSiRrVyzE1HG7oS36R8hCAln/YCDmDgqx2c8DDpLLzouC/7fgmCE2HVzLQmgvGa9EiJHjD20w7oY8BEvGXQFi5hgjYnf+CHhIUIjzBw8xc4wQu45kglDQQZwHOYih469vWpbn87llBbMEi/M5CzF2/KHI+rpkrn40/y0Q1yUMxNxBImL9/tq5+qDXp8L6CkIsOEhEbK8Td3T6yOi4JawTpRB9Bwuxst4NwIQO2pZwnloCMXAwECsO2rJwUdBVcM6v2yUQEweE2Nl/0ApmRRHzbat+ATFyAIilfRQGLavMaWX5fZQAMXPc51HLkiMLmOk8YNoW3A/yEEPHHBFb+1pav6ibzTFsW8y+loMYOu53ZHl/Drp3B4lB22L35yzE2DFC7OUZ4GReMm2r5M7pQ4i5Y4DYc4BhalgnUkjE5ksgxIKjh1jM+2Cmi5D+HbK5EpovkUO0HXe0s5q/ogEohnWi2EmaFxB9B4mITQeo9rjeBZ1kz+ThZBADxx3tbeYTQ9BFxjVJsJCHk0BMHHfUWnSAlnWYFonhQh5OhBg5AMRCfjdD4mqXrlLQAeavBIiZ4zFDbOSpQ25pxbUtDPNXPMTMcW8niJV8eyDZSNWYzygeZRBDx4NA9tYcIA/0Q/8PZLkykPdhIaaODtJau/4hJOaERB3I+zAQY8d9gFi6jhO8g8C8D4QYO4aI7C058rcQlNN8SSaF6DqefUQsXVeL3zoQpvkSKUTX8RiOOVm6Pvg+IDQVd5JCtB0sxNCxomWRTcmcZ5BA9B0MxPR67YqWNbWtkxRi4LgPkMTKdWe8BkLzDALEwEH6+nDK1IYDDL4Bl2eoQaOrp/15wUFMHI92hpifAwAtK+LPAYBgRdP+nIMYOWZIsjc/zwAqm/PnGWSbKBZi5pghrbmDaVn8uQywAkaNDGLmeLYyiOb5EvBDx8L5kgZAIgnE0AEgrfE5mRDun4RzMqHYtgSIvkMG0XWUspZF91GZkI078xADRwIgO8NzSxlayl/1ixLYttJhP8hBDBxP5vY9w/NXodhFmHMZgbAfZCEmDhayN3LABWMuO0fGZnq7CbCEECPHP/ZeXaPzcLnQsrhzMhVYpmRnHmLkeHI3Hccm5/qEliWc9wEhw8sQHQcPaU3OJ4Jq7gdHefip4TmAkN+ii5DqkF61HQASK6/bg7FEFR4ikR66DpKmRT8FRgvnAFJMPoNrYV1CPpKrOx7iMx9U4xHTJNYAKfseEvdJhgHS4IAW3DvC+chN3jGmL8AzRM0hiUirsd7tqvASAneN/bgboulTpNqXyzmgzWuAaDqY56Ikav0j7nce4QghP9RyqCQHgRE5d50+6js7HibCYPrI9beHqDoeMoj6OhFAusQ1/eEHFNLA/lHM+8Gqnz86SP/7CFF1POXPDjoojVcUUnMRmfZQHITU/9gtKjvHEBEeUqo67nJIqjTu0j5SD32k6vPU8z/zkKlF0T5ylUIUHM+l52spzR901KKQscH3EyAHGXM+9HxdfpVCVBz3JUihMg/SeQRAplzJOI8wnX2kxMM8Mtyv1kF+IUTF8Vx+dJva/QY7MEt0M/pc5RFyOjLDryQP10GuPeT31kVPzfEC0irdNwFTWVhYt5NN7RGP/WGMCJwfez0P0XYsQFbe/xHONYLX1YouJAHdnVf0CgifVcV0HuEhKxwvIa3S85CnO/opZNh7BA0xZiIknNhjzzlc5pmdg6g6REiscD8O5q5GDc/r6+p2AOtEABn6RwVW7vNa68ZAlB2Sh7Iq3FeEwZi0hw6ye+oImAtAdOEgzP4DQNY43kLa9fdHYWEfVeNgPIEd5OyYNXSJfryaIew+ikI0HDJIvPo+LxiRoNtHDWuufPyz5AepaBh3Jwi3H5whqxwrIG2y9n415krC1M9xQ/pHHLw4BzBC+H3tBNFyyB/una+87w5OiMNVtV0x7QePcb50DoBMJ5Fkf07GwKu2Y+G58Z+7f1B53a4GSbxzLL2SwDvH4ksiCs8cy6/tcNihBmn9cryAxF45Xr1sKPbJ8fL1T7lHjtcv5KoK5xz/9F6R5pzjqfvSusoXx9vXCPrieP9ix9IPx4pXbZauOB6mLz/1IR7r3uJa1c7HY+V7dY/Ox2Ptm46TytV5UPkl2m6uS3TeBu64Q+H97HXjskMB0ubfcTxa25A2dmV/bgoh47CzDkVIe3TVoQqhlE84VOqlDGlPTjo0IH1Qtnc8FCulA2mL7R3KddKCkPblmkMXMlG2cejURxvSUzZx6NXGANI+N3DcdStjAiH7FMuOh35VzCCkXKw5Hk+TehhD2taSw7AWFiCks5g6Hv+M62AFQsoflejd/+EKpLNo3x/lGKQr01Nr193P+bT4nS1DunKbGIuO/tkGlssGkL48usdyCoxH92ubb/gfT86Axsci5ZwAAAAASUVORK5CYII=";

async function ensureAiBotUser() {
  let bot = await getUser(AI_BOT_ID);
  if (!bot) {
    bot = {
      id: AI_BOT_ID, phone: '', nickname: 'AI 말벗도우미',
      region: '전체', gender: 'female', age: 99,
      bio: '매일 소소한 이야기를 전해드리는 AI 말벗도우미예요 :)',
      photos: [AI_BOT_PHOTO], points: 999999, isOnline: true, lastSeen: Date.now(),
      blockedUserIds: [], lastPostDate: null, adWatchCountToday: 0,
      lastAdChargeDate: null, profileUpdatedAt: Date.now(),
      followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []
    };
    await saveUser(bot);
  } else if (!bot.photos || !bot.photos.length) {
    bot.photos = [AI_BOT_PHOTO];
    await saveUser(bot);
  }
  return bot;
}

// 핫토픽/밸런스게임을 "투표"로 통합하면서 두 템플릿 풀을 하나로 합침
const AI_BOT_VOTE_TEMPLATES = [
  { content: '요즘 제일 핫한 챌린지, 뭐가 제일 재밌어요? 🔥', options: ['댄스 챌린지', '먹방 챌린지', '운동 챌린지', '기타'] },
  { content: '스트레스 풀리는 방법 뭐가 제일 좋아요? 😌', options: ['운동하기', '맛있는거 먹기', '잠자기', '친구랑 수다떨기'] },
  { content: '주말에 제일 하고싶은 거 골라주세요! ✨', options: ['집에서 넷플릭스', '밖에서 나들이', '친구 만나기', '푹 자기'] },
  { content: '치킨 vs 피자, 오늘 저녁 뭐 먹을까요? 🍗🍕', options: ['치킨', '피자'] },
  { content: '여름 vs 겨울, 더 좋아하는 계절은? ☀️❄️', options: ['여름', '겨울'] },
  { content: '아침형 인간 vs 밤형 인간, 나는 어느 쪽? 🌅🌙', options: ['아침형', '밤형'] },
  { content: '국내여행 vs 해외여행, 다음 휴가는? ✈️', options: ['국내여행', '해외여행'] },
];

async function postAsAiBotIfNeeded() {
  try {
    const bot = await ensureAiBotUser();
    const todayStr = new Date().toISOString().slice(0, 10);
    if (bot.lastPostDate === todayStr) return; // 오늘 이미 게시함

    const roll = Math.random();
    let content, category = 'normal', pollOptions = null, pollVotes = null;
    if (roll < 0.4) {
      const t = AI_BOT_VOTE_TEMPLATES[Math.floor(Math.random() * AI_BOT_VOTE_TEMPLATES.length)];
      content = t.content; category = 'vote';
      pollOptions = t.options.map((text, i) => ({ id: 'o' + i, text })); pollVotes = {};
    } else {
      content = AI_BOT_POST_TEMPLATES[Math.floor(Math.random() * AI_BOT_POST_TEMPLATES.length)];
    }

    const post = {
      id: genId('p'), authorId: bot.id, content, photo: '', logType: 'story',
      category, pollOptions, pollVotes,
      createdAt: Date.now(), updatedAt: Date.now(), likes: 0, likedBy: [], comments: {},
      viewCount: 0, viewedBy: {}
    };
    await savePost(post);
    bot.lastPostDate = todayStr;
    await saveUser(bot);
    broadcastPosts();
    notifyFollowersNewPost(bot, post, '작성');
    notifyKeywordMatches(post, bot.id, '등록');
    console.log('[AI 말벗도우미] 오늘의 이야기 게시 완료:', content);
  } catch (e) { console.error('[AI 말벗도우미 게시 오류]', e); }
}

// 서버 시작 시 1회 체크 + 이후 1시간마다 날짜가 바뀌었는지 체크
// (무료 호스팅 환경의 sleep을 고려해 별도 cron 라이브러리 없이 setInterval로 처리)
ensureAiBotUser().then(() => postAsAiBotIfNeeded());
setInterval(postAsAiBotIfNeeded, 60 * 60 * 1000);

// 필터링/삭제된 게시글·댓글 자동 정리: 각각의 시점으로부터 3일이 지나면 완전 삭제
async function purgeExpiredFilteredPosts() {
  try {
    const posts = await getRawPosts();
    const now = Date.now();
    const THREE_DAYS = 3 * 24 * 60 * 60 * 1000;
    let purgedAny = false;
    for (const p of posts) {
      if (p.filtered && p.filteredAt && (now - p.filteredAt) > THREE_DAYS) {
        await deletePostDb(p.id);
        purgedAny = true;
        continue;
      }
      if (p.deleted && p.deletedAt && (now - p.deletedAt) > THREE_DAYS) {
        await deletePostDb(p.id);
        purgedAny = true;
        continue;
      }
      if (p.comments) {
        let commentsChanged = false;
        Object.keys(p.comments).forEach(cid => {
          const c = p.comments[cid];
          if (c.deleted && c.deletedAt && (now - c.deletedAt) > THREE_DAYS) {
            delete p.comments[cid];
            commentsChanged = true;
          }
        });
        if (commentsChanged) { savePost(p); purgedAny = true; }
      }
    }
    if (purgedAny) broadcastPosts();

    const chatsSnap = await db.ref('chats').once('value');
    const allChats = chatsSnap.val() || {};
    for (const roomId of Object.keys(allChats)) {
      const room = allChats[roomId];
      if (room.withdrawnAt && (now - room.withdrawnAt) > THREE_DAYS) {
        await deleteRoom(roomId);
      }
    }
  } catch (e) { console.error('[필터링/삭제 게시글 자동정리 오류]', e); }
}
setInterval(purgeExpiredFilteredPosts, 60 * 60 * 1000);

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
setInterval(notifySubscriptionsExpiringSoon, 60 * 60 * 1000);

/* =====================================================================
   오늘의 인기 투표 자동 선정 + 포인트 100 지급
   - 매일 00시(KST) 기준으로, "어제" 하루 동안 올라온 투표(category:'vote', 구 hottopic/balance 포함)
     게시글 중 공감(likes)이 가장 많은 글의 작성자 1명에게 포인트 100개를 지급함
   - 동률이면 댓글 많은 순, 그마저 동률이면 이전에 인기투표로 당첨된 횟수가 적은 사람 순으로 결정
   - 무료 호스팅 환경 특성상 정확한 cron 대신, meta/voteReward/lastAwardDate(마지막으로 처리한 "어제" 날짜)를
     Firebase에 저장해두고 10분마다 날짜가 바뀌었는지 체크하는 방식으로 처리함(서버 재시작에도 안전)
===================================================================== */
function kstDateStr(d) {
  return new Date(d.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}
function kstMonthStr(d) { return kstDateStr(d).slice(0, 7); }

/* =====================================================================
   0-54: 구독 1년권 매월 자동 지급
   - 1년권(365일 이상) 구매/지급 시 쌀을 한번에 몰아주지 않고, 매달(KST 기준 달이 바뀔 때마다)
     구독이 유효한 동안 자동으로 나눠 지급함. 구매 직후에는 lastGrantedMonth가 null이라
     이 함수가 처음 도는 시점(최대 1시간 이내)에 이번 달 몫이 바로 지급됨.
   - 무료 호스팅 환경 특성상 정확한 cron 대신 다른 일일 작업들과 동일하게 1시간마다 체크.
===================================================================== */
async function grantMonthlySubscriptionBonusIfNeeded() {
  try {
    const now = Date.now();
    const thisMonth = kstMonthStr(new Date());
    const allUsers = await getAllUsers();
    for (const user of Object.values(allUsers)) {
      const sub = user.subscription;
      const mb = sub && sub.monthlyBonus;
      if (!mb || !mb.amount) continue;
      if (!sub.expiresAt || sub.expiresAt <= now) continue; // 구독 만료되면 더 이상 지급 안 함
      if (mb.lastGrantedMonth === thisMonth) continue; // 이번 달 몫은 이미 지급함
      user.points = (user.points || 0) + mb.amount;
      user.subscription.monthlyBonus.lastGrantedMonth = thisMonth;
      await saveUser(user);
      await db.ref(`purchaseHistory/${user.id}`).push({
        productId: `monthly_bonus_${sub.tier}`,
        points: mb.amount,
        subscriptionTier: sub.tier,
        subscriptionDays: null,
        at: now
      });
      const tierLabel = sub.tier === 'platinum' ? '플래티넘' : '골드';
      const msg = `${tierLabel} 구독 매월 지급 쌀 ${mb.amount.toLocaleString()}개가 지급되었습니다.`;
      const sId = userToSocket[user.id];
      if (sId) io.to(sId).emit('points:updated', { points: user.points, subscription: user.subscription });
      else sendWebPush(user.id, { title: '구독 매월 쌀 지급', body: msg, type: 'subscription_monthly_bonus' });
      console.log(`[구독 매월지급] ${user.id} 유저에게 ${tierLabel} 쌀 ${mb.amount}개 지급 (${thisMonth})`);
    }
  } catch (e) { console.error('[구독 매월지급 오류]', e); }
}
setInterval(grantMonthlySubscriptionBonusIfNeeded, 60 * 60 * 1000);
// 일일 접속 보상: 하루(KST 기준) 최초 로그인/세션복구 시 쌀 50개 자동 지급 (스위치 없이 항상 지급).
// user 객체를 직접 변형만 하고 저장은 호출부의 saveUser(user)가 한 번에 처리함.
function grantDailyLoginRewardIfNeeded(user) {
  const today = kstDateStr(new Date());
  if (user.lastDailyRewardDate === today) return null;
  user.points = (user.points || 0) + 50;
  user.lastDailyRewardDate = today;
  return 50;
}
// 지급된 포인트를 다음 로그인 시 딱 1회만 안내창으로 보여주기 위해 대기시켜둔 알림을 꺼내는 함수.
// (접속 중이었다면 즉시 reward:vote_winner 소켓 이벤트로 보여주고 notified:true로 표시해둠)
async function popPendingRewardNotify(user) {
  if (user.pendingRewardNotify && !user.pendingRewardNotify.notified) {
    const info = { amount: user.pendingRewardNotify.amount };
    user.pendingRewardNotify.notified = true;
    await saveUser(user);
    return info;
  }
  return null;
}
async function awardDailyVoteWinnerIfNeeded() {
  try {
    const metaSnap = await db.ref('meta/voteReward').once('value');
    const meta = metaSnap.val() || {};
    const yesterdayKst = kstDateStr(new Date(Date.now() - ONE_DAY));
    if (meta.lastAwardDate === yesterdayKst) return; // 이미 처리된 날짜

    // yesterdayKst(예: '2026-08-03') 하루치(KST 00:00~24:00)의 UTC 타임스탬프 범위
    const startUtc = new Date(yesterdayKst + 'T00:00:00+09:00').getTime();
    const endUtc = startUtc + ONE_DAY;

    const posts = await getRawPosts();
    const candidates = posts.filter(p =>
      ['vote', 'hottopic', 'balance'].includes(p.category) &&
      !p.deleted && !p.filtered &&
      p.pollOptions && p.pollOptions.length &&
      p.createdAt >= startUtc && p.createdAt < endUtc
    );

    if (candidates.length) {
      const users = await getAllUsers();
      const scored = candidates.map(p => ({
        post: p,
        likes: p.likes || 0,
        commentCount: p.comments ? Object.keys(p.comments).length : 0,
        winCount: (users[p.authorId] && users[p.authorId].voteWinCount) || 0
      }));
      // 공감 많은 순 -> 댓글 많은 순 -> 인기투표 당첨 적게 된 순
      scored.sort((a, b) => (b.likes - a.likes) || (b.commentCount - a.commentCount) || (a.winCount - b.winCount));
      const winner = scored[0];
      const author = users[winner.post.authorId];
      if (author) {
        author.points = (author.points || 0) + 100;
        author.voteWinCount = (author.voteWinCount || 0) + 1;
        const sId = userToSocket[author.id];
        if (sId) {
          io.to(sId).emit('reward:vote_winner', { amount: 100, points: author.points });
          author.pendingRewardNotify = { amount: 100, awardedAt: Date.now(), notified: true };
        } else {
          author.pendingRewardNotify = { amount: 100, awardedAt: Date.now(), notified: false };
        }
        await saveUser(author);
        winner.post.dailyWinner = true;
        winner.post.dailyWinnerDate = yesterdayKst;
        await savePost(winner.post);
        broadcastUsers();
        broadcastPosts();
        console.log('[인기 투표 포인트 지급]', author.nickname, yesterdayKst);
      }
    }

    await db.ref('meta/voteReward').update({ lastAwardDate: yesterdayKst });
  } catch (e) { console.error('[인기 투표 포인트 지급 오류]', e); }
}
awardDailyVoteWinnerIfNeeded();
setInterval(awardDailyVoteWinnerIfNeeded, 10 * 60 * 1000);

// 관리자 전화번호 목록. Render/​.env의 ADMIN_PHONES에 "01012345678,01099998888"처럼
// 콤마로 구분해서 등록해두면, 그 번호로 로그인한 사람은 커뮤니티 글/댓글을 누구 것이든
// 삭제할 수 있게 됨 (신고 시스템과 별개로 즉시 삭제 가능한 권한).
const ADMIN_PHONES = (process.env.ADMIN_PHONES || '').split(',').map(s => s.trim()).filter(Boolean);
function isAdminPhone(phone) { return !!phone && ADMIN_PHONES.includes(phone); }
const ADMIN_KAKAO_IDS = (process.env.ADMIN_KAKAO_IDS || "").split(",").map(s => s.trim()).filter(Boolean); function isAdminKakao(kakaoId) { return !!kakaoId && ADMIN_KAKAO_IDS.includes(String(kakaoId)); } function isAdmin(user) { return !!user && (isAdminPhone(user.phone) || isAdminKakao(user.kakaoId)); }

/* =====================================================================
   카카오 로그인
   - Kakao Developers(https://developers.kakao.com)에서 앱을 만들고,
     .env에 KAKAO_REST_API_KEY 를 등록해야 동작함.
   - "플랫폼 > Web" 에 실제 배포 도메인을 등록하고,
     "카카오 로그인 > Redirect URI" 에 "https://본인도메인/" (index.html이 뜨는 주소)를
     정확히 등록해야 함. 로컬 테스트 시엔 http://localhost:8080/ 도 추가로 등록.
   - KAKAO_CLIENT_SECRET: 카카오 디벨로퍼스 REST API 키의 "클라이언트 시크릿"이
     활성화(ON) 상태인 경우 반드시 .env에 설정해야 함. 활성화된 상태에서 이 값을
     안 보내면 토큰 발급이 실패함.
===================================================================== */
const KAKAO_REST_API_KEY = process.env.KAKAO_REST_API_KEY || '';
const KAKAO_CLIENT_SECRET = process.env.KAKAO_CLIENT_SECRET || '';

async function exchangeKakaoCode(code, redirectUri) {
  const params = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: KAKAO_REST_API_KEY,
    client_secret: KAKAO_CLIENT_SECRET,
    redirect_uri: redirectUri,
    code
  });
  const tokenRes = await fetch('https://kauth.kakao.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
    body: params.toString()
  });
  const tokenData = await tokenRes.json();
  if (!tokenData.access_token) throw new Error('카카오 토큰 발급 실패: ' + JSON.stringify(tokenData));

  const profileRes = await fetch('https://kapi.kakao.com/v2/user/me', {
    headers: { Authorization: `Bearer ${tokenData.access_token}` }
  });
  const profileData = await profileRes.json();
  return { kakaoId: String(profileData.id) };
}

io.on('connection', (socket) => {

  // 전화번호+비밀번호 로그인
  // - 기존(비밀번호 없이 가입한) 회원은 그대로 전화번호만으로 로그인 가능(마이그레이션 배려)
  // - 비밀번호를 설정한 회원(신규 가입자)은 반드시 비밀번호까지 일치해야 로그인됨
  socket.on('auth:login', async (data, cb) => {
    try {
      const user = await findUserByPhone(data.phone);
      if (!user) return cb({ success: false, notFound: true, wrongField: 'phone' });
      if (user.isBanned) return cb({ success: false, banned: true, message: '이용이 제한된 계정입니다.' });
      if (user.passwordHash) {
        const ok = await comparePassword(data.password || '', user.passwordHash);
        if (!ok) return cb({ success: false, wrongField: 'password' });
      }
      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      const repPhotoSuggestNotify = await popPendingRepPhotoSuggest(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, repPhotoSuggestNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 세션 토큰으로 자동 로그인 (브라우저 재접속/소켓 재연결 시 사용).
  // 토큰이 유효하면(7일 이내 발급/갱신) 비밀번호 재입력 없이 자동 로그인되고,
  // 이때 토큰을 다시 새로 발급(연장)해서 계속 접속하는 한 로그인이 유지되게 함.
  // 토큰이 없거나 7일이 지나 만료됐으면 실패 응답을 보내 재로그인(비밀번호 재입력)을 요구함.
  socket.on('auth:session_resume', async (data, cb) => {
    try {
      const payload = verifySessionToken(data && data.token);
      if (!payload) return cb({ success: false, expired: true });
      const user = await getUser(payload.uid);
      if (!user) return cb({ success: false });
      if (user.isBanned) return cb({ success: false, banned: true, message: '이용이 제한된 계정입니다.' });
      user.isOnline = true;
      user.lastSeen = Date.now();
      const dailyRewardAmount = grantDailyLoginRewardIfNeeded(user);
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id); // 갱신(연장)
      const rewardNotify = await popPendingRewardNotify(user);
      const warningNotify = await popPendingWarningNotify(user);
      const repPhotoSuggestNotify = await popPendingRepPhotoSuggest(user);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token, rewardNotify, warningNotify, repPhotoSuggestNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 회원가입 (이미 등록된 번호면 거부). 비밀번호는 형식 제한 없이 받되, 반드시 입력해야 함(대소문자 구분은
  // bcrypt 해시 비교 특성상 자동으로 지켜짐 - 원문 그대로 비교하므로 대/소문자가 다르면 다른 비밀번호로 처리됨).
  socket.on('auth:signup', async (data, cb) => {
    try {
      if (!/^01[0-9]{9}$/.test(data.phone || '')) return cb({ success: false, message: '휴대폰 번호를 정확히 입력해주세요. (예: 010-0000-0000)' });
      if (!data.password || !String(data.password).length) return cb({ success: false, message: '비밀번호를 입력해주세요.' });
      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      if (containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      const existing = await findUserByPhone(data.phone);
      if (existing) return cb({ success: false, alreadyExists: true });
      const passwordHash = await hashPassword(String(data.password));
      const user = {
        id: genId('u'), phone: data.phone, passwordHash, nickname: data.nickname,
        nicknameFiltered: containsBannedWord(data.nickname),
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),
        bio: data.bio || '반갑습니다!', photos: data.photos || [], points: 100,
        isOnline: true, lastSeen: Date.now(), blockedUserIds: [],
        lastPostDate: null, adWatchCountToday: 0, lastAdChargeDate: null,
        profileUpdatedAt: Date.now(), joinedAt: Date.now(), onboardingSeen: false,
        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []
      };
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      cb({ success: true, user: { ...user, isAdmin: isAdmin(user) }, token });
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

  // 카카오 로그인: 인가 코드를 받아 카카오 사용자 고유 ID를 확인.
  // - 이미 이 kakaoId로 가입된 계정이 있으면 바로 로그인 처리
  // - 처음 로그인하는 카카오 계정이면, 추가 프로필(닉네임/지역/성별/나이) 입력이 필요하다는 뜻으로
  //   pendingToken(10분간 유효한 임시 토큰)을 발급해서 돌려줌 -> 클라이언트는 추가 정보 입력 화면을 띄우고
  //   auth:kakao_complete_profile 이벤트로 pendingToken과 함께 나머지 정보를 제출함
  socket.on('auth:kakao_login', async (data, cb) => {
    try {
      if (!KAKAO_REST_API_KEY) return cb({ success: false, message: '카카오 로그인이 아직 설정되지 않았습니다. (KAKAO_REST_API_KEY 미설정)' });
      const { kakaoId } = await exchangeKakaoCode(data.code, data.redirectUri); console.log('[KAKAO_ID]', kakaoId);
      const existing = await findUserByKakaoId(kakaoId);
      if (existing) {
        if (existing.isBanned) return cb({ success: false, banned: true, message: '이용이 제한된 계정입니다. 문의: kickoff030303@gmail.com' });
        existing.isOnline = true;
        existing.lastSeen = Date.now();
        existing.lastIp = getClientIp(socket);
        if (!existing.deviceId && data.deviceId) existing.deviceId = data.deviceId; // 이 기능 추가 전 가입한 계정에 최초 1회만 채움
        const dailyRewardAmount = grantDailyLoginRewardIfNeeded(existing);
        await saveUser(existing);
        socketToUser[socket.id] = existing.id;
        userToSocket[existing.id] = socket.id;
        const token = issueSessionToken(existing.id);
        const rewardNotify = await popPendingRewardNotify(existing);
        const warningNotify = await popPendingWarningNotify(existing);
        const repPhotoSuggestNotify = await popPendingRepPhotoSuggest(existing);
        cb({ success: true, user: { ...existing, isAdmin: isAdmin(existing) }, token, rewardNotify, warningNotify, repPhotoSuggestNotify, dailyRewardNotify: dailyRewardAmount ? { amount: dailyRewardAmount } : null });
        broadcastUsers();
        return;
      }
      const pendingToken = jwt.sign({ kakaoId, purpose: 'kakao_signup' }, SESSION_SECRET, { expiresIn: '10m' });
      cb({ success: false, needProfile: true, pendingToken });
    } catch (e) { console.error('[카카오 로그인 오류]', e); cb({ success: false, message: '카카오 로그인 중 오류가 발생했습니다.' }); }
  });

  // 카카오 신규 가입자의 추가 정보(닉네임/지역/성별/나이) 제출 -> 계정 생성
  // 카카오로 가입한 계정은 phone이 없고 passwordHash도 없어서(전화번호 로그인 대상이 아니므로) 관리자 권한 대상은 아님.
  socket.on('auth:kakao_complete_profile', async (data, cb) => {
    try {
      let payload;
      try { payload = jwt.verify(data.pendingToken, SESSION_SECRET); } catch (e) { payload = null; }
      if (!payload || payload.purpose !== 'kakao_signup') return cb({ success: false, message: '인증이 만료되었습니다. 카카오 로그인을 다시 시도해주세요.' });
      const already = await findUserByKakaoId(payload.kakaoId);
      if (already) return cb({ success: false, alreadyExists: true });
      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      if (containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      // 같은 기기(deviceId)로 이미 가입된 계정이 있으면 경고만 하고(차단X) 그대로 진행 허용 - 관리자 대시보드 어뷰징 의심 목록에서 조회 가능
      let deviceDupUsers = null;
      if (data.deviceId) {
        const allUsersForDeviceCheck = await getAllUsers();
        deviceDupUsers = Object.values(allUsersForDeviceCheck).filter(u => u.deviceId === data.deviceId);
        if (deviceDupUsers.length && data.deviceConfirmed !== true) {
          return cb({ success: false, needsDeviceConfirm: true });
        }
      }
      if (data.photos && data.photos[0]) {
        const nsfwResult = await checkImageNsfw(data.photos[0]);
        if (nsfwResult.isNsfw) return cb({ success: false, message: '부적절한 프로필 사진으로 감지되어 가입할 수 없습니다. 다른 사진을 등록해주세요.' });
      }
      const user = {
        id: genId('u'), phone: '', kakaoId: payload.kakaoId, nickname: data.nickname,
        nicknameFiltered: containsBannedWord(data.nickname),
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),
        bio: data.bio || '반갑습니다!', photos: data.photos || [], points: 100,
        isOnline: true, lastSeen: Date.now(), blockedUserIds: [],
        lastPostDate: null, adWatchCountToday: 0, lastAdChargeDate: null,
        profileUpdatedAt: Date.now(), joinedAt: Date.now(), onboardingSeen: false,
        deviceId: data.deviceId || null, lastIp: getClientIp(socket),
        followingIds: [], followerIds: [], profileLikedBy: [], notifyKeywords: []
      };
      await saveUser(user);
      socketToUser[socket.id] = user.id;
      userToSocket[user.id] = socket.id;
      const token = issueSessionToken(user.id);
      cb({ success: true, user: { ...user, isAdmin: false }, token });
      broadcastUsers();
      // 경고를 보고도 가입을 강행해 실제로 중복계정이 생긴 경우에만 관리자에게 실시간 알림
      if (deviceDupUsers && deviceDupUsers.length) {
        const allUsersForAdminNotify = await getAllUsers();
        Object.values(allUsersForAdminNotify).filter(isAdmin).forEach(admin => {
          notifyUser(admin.id, { type: 'abuse_alert', title: '중복계정 의심', body: `"${user.nickname}" 님이 이미 가입된 기기로 새 계정을 만들었어요.` });
        });
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('profile:update', async (data, cb) => {
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
  });
  // 프로필 사진별 개별 좋아요 토글 (본인 사진은 좋아요 불가)
  socket.on('photo:like', async (data, cb) => {
    try {
      const myId = socketToUser[socket.id];
      const targetId = data && data.targetUserId;
      const photoIndex = data && typeof data.photoIndex === 'number' ? data.photoIndex : null;
      if (!myId || !targetId || photoIndex === null || myId === targetId) return cb && cb({ success: false });
      const target = await getUser(targetId);
      if (!target || !target.photos || !target.photos[photoIndex]) return cb && cb({ success: false });
      if (!target.photoLikes) target.photoLikes = {};
      if (!target.photoLikes[photoIndex]) target.photoLikes[photoIndex] = {};
      const alreadyLiked = !!target.photoLikes[photoIndex][myId];
      if (alreadyLiked) delete target.photoLikes[photoIndex][myId];
      else target.photoLikes[photoIndex][myId] = true;

      // 대표사진(0번)이 아닌 사진이 새로 좋아요를 받아 대표사진보다 많아지면, 평생 1회만 대표사진 변경을 제안함
      if (!alreadyLiked && photoIndex !== 0 && !target.repPhotoSuggestShown) {
        const repCount = Object.keys(target.photoLikes[0] || {}).length;
        const thisCount = Object.keys(target.photoLikes[photoIndex] || {}).length;
        if (thisCount > repCount) {
          target.repPhotoSuggestShown = true;
          target.pendingRepPhotoSuggest = { photoIndex, at: Date.now(), notified: false };
          const sId = userToSocket[targetId];
          if (sId) {
            io.to(sId).emit('account:rep_photo_suggest', { photoIndex });
            target.pendingRepPhotoSuggest.notified = true;
          }
        }
      }

      await saveUser(target);
      cb && cb({ success: true, liked: !alreadyLiked, likeCount: Object.keys(target.photoLikes[photoIndex] || {}).length });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 0-33: 본인의 결제 내역(쌀 충전/구독) 조회
  socket.on('points:get_purchase_history', async (data, cb) => {
    try {
      const myId = socketToUser[socket.id];
      if (!myId) return cb && cb({ success: false, history: [] });
      const snap = await db.ref(`purchaseHistory/${myId}`).once('value');
      const all = snap.val() || {};
      const history = Object.values(all).sort((a, b) => (b.at || 0) - (a.at || 0)).slice(0, 100);
      cb && cb({ success: true, history });
    } catch (e) { console.error(e); cb && cb({ success: false, history: [] }); }
  });

  // 0-20: 특정 사진에 좋아요 누른 사람 "목록" 조회 - 골드 이상 구독 중인 사람만 실제 목록 열람 가능
  // (하트 개수 자체는 기존처럼 누구나 항상 전체 공개 - 이 핸들러와 무관하게 photoLikes 데이터로 이미 계산됨)
  socket.on('photo:get_likers', async (data, cb) => {
    try {
      const myId = socketToUser[socket.id];
      const targetId = data && data.targetUserId;
      const photoIndex = data && typeof data.photoIndex === 'number' ? data.photoIndex : null;
      if (!myId || !targetId || photoIndex === null) return cb && cb({ success: false, count: 0, likers: [] });
      const target = await getUser(targetId);
      if (!target) return cb && cb({ success: false, count: 0, likers: [] });
      const likerIds = Object.keys((target.photoLikes && target.photoLikes[photoIndex]) || {});
      const me = await getUser(myId);
      const users = await getAllUsers();
      const rawLikers = likerIds.map(id => users[id]).filter(Boolean);
      const locked = !hasTierAtLeast(me, 'gold');
      // 0-28: locked이면 실제 닉네임/사진 대신 마스킹된 정보만 내려보냄(브라우저에서 실제 데이터 노출 방지)
      const likers = locked ? rawLikers.map(maskUserForLockedTeaser) : rawLikers;
      cb && cb({ success: true, locked, count: likerIds.length, likers });
    } catch (e) { console.error(e); cb && cb({ success: false, count: 0, likers: [] }); }
  });
// 회원탈퇴: 게시글/스토리/릴스 전부 삭제, 채팅방은 남기되 시스템 메시지로 탈퇴 안내, 계정 삭제
  // 0-25: 관리자 강제탈퇴용 - account:withdraw와 동일한 삭제 로직(게시글 삭제, 채팅방 탈퇴 표시, 계정 제거)을 재사용
  async function forceWithdrawUserAccount(userId, systemMessageText) {
    const postsSnap = await db.ref('posts').once('value');
    const allPosts = postsSnap.val() || {};
    for (const pid of Object.keys(allPosts)) {
      if (allPosts[pid].authorId === userId) await deletePostDb(pid);
    }
    const chatsSnap = await db.ref('chats').once('value');
    const allChats = chatsSnap.val() || {};
    for (const roomId of Object.keys(allChats)) {
      const room = allChats[roomId];
      if (room.userIds && room.userIds.includes(userId)) {
        await addMessage(roomId, { senderId: 'system', text: systemMessageText, timestamp: Date.now() });
        await saveRoomMeta(roomId, { withdrawnAt: Date.now() });
        const otherId = room.userIds.find(id => id !== userId);
        const sId = userToSocket[otherId];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: { senderId: 'system', text: systemMessageText, timestamp: Date.now() } });
      }
    }
    // 0-51: 탈퇴한 유저의 흔적(팔로우/팔로워/프로필좋아요)이 다른 유저들의 배열에 그대로 남아
    // "밖에서 보이는 팔로잉 숫자"와 "실제 목록에 뜨는 인원수"가 어긋나는 버그가 있었음 -> 탈퇴 시 전체 유저를 훑어 정리
    const usersSnap = await db.ref('users').once('value');
    const allUsers = usersSnap.val() || {};
    for (const uid of Object.keys(allUsers)) {
      if (uid === userId) continue;
      const u = allUsers[uid];
      const updates = {};
      if (Array.isArray(u.followingIds) && u.followingIds.includes(userId)) updates.followingIds = u.followingIds.filter(id => id !== userId);
      if (Array.isArray(u.followerIds) && u.followerIds.includes(userId)) updates.followerIds = u.followerIds.filter(id => id !== userId);
      if (Array.isArray(u.profileLikedBy) && u.profileLikedBy.includes(userId)) updates.profileLikedBy = u.profileLikedBy.filter(id => id !== userId);
      if (Object.keys(updates).length) await db.ref(`users/${uid}`).update(updates);
    }
    await db.ref(`users/${userId}`).remove();
  }

  socket.on('account:withdraw', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      await forceWithdrawUserAccount(userId, '탈퇴한 사용자입니다.');
      delete socketToUser[socket.id];
      delete userToSocket[userId];
      cb({ success: true });
      broadcastUsers();
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });
  // 홈 리스트: 나 자신 포함, filters.sort로 기본순/popular/distance/views 정렬 선택 가능
  // 단일 유저 프로필 조회 (채팅 상단 헤더, 단체채팅방 참여자 목록 등에서 목록 필터에 상관없이 특정 유저 1명을 정확히 조회할 때 사용)
  socket.on('users:get_one', async (data, cb) => {
    try {
      const user = await getUser(data.userId);
      if (!user) return cb({ success: false });
      const result = user.nicknameFiltered ? { ...user, nickname: "삭제된 닉네임입니다" } : user;
      cb({ success: true, user: result });
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 단일 유저 프로필 조회 (채팅 상단 헤더 등에서 목록 필터에 상관없이 특정 유저 1명을 정확히 조회할 때 사용)
  socket.on('users:get_one', async (data, cb) => {
    try {
      const user = await getUser(data.userId);
      if (!user) return cb({ success: false });
      const result = user.nicknameFiltered ? { ...user, nickname: "삭제된 닉네임입니다" } : user;
      cb({ success: true, user: result });
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('users:get_list', async (filters, cb) => {
    try {
      const users = await getAllUsers();
      let list = Object.values(users);
      if (filters.region && filters.region !== '전체') list = list.filter(u => u.region === filters.region);
      if (filters.gender && filters.gender !== '전체') list = list.filter(u => u.gender === filters.gender);
      list = list.filter(u => u.age >= filters.ageMin && u.age <= filters.ageMax);
      list.sort((a, b) => (b.profileUpdatedAt || b.lastSeen || 0) - (a.profileUpdatedAt || a.lastSeen || 0));
      const myUserId = socketToUser[socket.id];
      const myUser = myUserId ? await getUser(myUserId) : null;
      list = sortUsersByType(list, filters.sort, myUser && myUser.region);
      list = list.map(u => u.nicknameFiltered ? { ...u, nickname: "삭제된 닉네임입니다" } : u);
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  // 커뮤니티 리스트: filters.sort로 기본순/popular/distance/views 정렬 선택 가능
  socket.on('posts:get_list', async (filters, cb) => {
    try {
      const now = Date.now();
      let list = await enrichPosts(await getRawPosts());
      list = list.filter(p => (now - (p.updatedAt || p.createdAt)) < THIRTY_DAYS);
      if (filters.region && filters.region !== '전체') list = list.filter(p => p.authorRegion === filters.region);
      if (filters.gender && filters.gender !== '전체') list = list.filter(p => p.authorGender === filters.gender);
      list = list.filter(p => p.authorAge >= filters.ageMin && p.authorAge <= filters.ageMax);
      list.sort((a, b) => (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt));
      const myUserId = socketToUser[socket.id];
      const myUser = myUserId ? await getUser(myUserId) : null;
      if (myUser && myUser.blockedUserIds && myUser.blockedUserIds.length) {
        list = list.filter(p => !myUser.blockedUserIds.includes(p.authorId));
      }
      list = sortPostsByType(list, filters.sort, myUser && myUser.region);
      cb({ success: true, posts: list });
    } catch (e) { console.error(e); cb({ success: false, posts: [] }); }
  });

  // 말벗스토리 피드: 조회수 기반 가중치 + 이미 본 스토리 감점 + 랜덤 셔플
  // 클라이언트에서 아래/좌로 넘길 때마다 이 이벤트를 다시 호출하면 매번 새로운 랜덤 순서를 받게 됨
  socket.on('stories:get_feed', async (filters, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const now = Date.now();
      let raw = await getRawPosts();
      raw = raw.filter(p => p.logType === 'log' && !p.deleted && !p.filtered && (now - (p.updatedAt || p.createdAt)) < THIRTY_DAYS);
      const shuffled = weightedShuffleStories(raw, userId);
      const enriched = await enrichPosts(shuffled);
      cb({ success: true, stories: enriched });
    } catch (e) { console.error(e); cb({ success: false, stories: [] }); }
  });

  // 별명 검색 (홈 화면, 포인트 좌측의 작은 검색창에서 사용) - 부분 문자열 일치, 대소문자/자모 구분 없이 매칭
  socket.on('users:search', async (data, cb) => {
    try {
      const q = ((data && data.query) || '').trim().toLowerCase();
      if (!q) return cb({ success: true, users: [] });
      const users = await getAllUsers();
      const list = Object.values(users).filter(u => (u.nickname || '').toLowerCase().includes(q));
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  // 커뮤니티 검색: 게시글 본문 + 댓글 내용에서 검색어를 찾음.
  // matchedCommentIds에 담긴 댓글 id들을 클라이언트에서 최대 3줄까지 파란 강조 박스로 렌더링하면 됨
  socket.on('posts:search', async (data, cb) => {
    try {
      const q = ((data && data.query) || '').trim().toLowerCase();
      if (!q) return cb({ success: true, results: [] });
      const list = await enrichPosts(await getRawPosts());
      const results = [];
      list.forEach(p => {
        const contentMatch = (p.content || '').toLowerCase().includes(q);
        const matchedComments = (p.comments || []).filter(c => (c.content || '').toLowerCase().includes(q));
        if (contentMatch || matchedComments.length) {
          results.push({
            ...p,
            matchedCommentIds: matchedComments.map(c => c.id).slice(0, 3)
          });
        }
      });
      results.sort((a, b) => (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt));
      cb({ success: true, results, query: data.query });
    } catch (e) { console.error(e); cb({ success: false, results: [] }); }
  });

  socket.on('posts:create', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false });

      // 게시글 도배 방지: 마지막 작성 후 5분 이내면 새 글 작성 차단 (수정은 이 제한과 무관하게 항상 가능)
      const POST_COOLDOWN_MS = 5 * 60 * 1000;
      if (user.lastPostCreatedAt && (Date.now() - user.lastPostCreatedAt) < POST_COOLDOWN_MS) {
        const waitSec = Math.ceil((POST_COOLDOWN_MS - (Date.now() - user.lastPostCreatedAt)) / 1000);
        return cb({ success: false, cooldown: true, waitSec, message: `글은 5분에 한 번만 작성할 수 있어요. ${Math.ceil(waitSec/60)}분 후 다시 시도해주세요.` });
      }

      // 투표 항목 텍스트도 게시글 본문과 동일하게 금칙어 검사 대상에 포함시키기 위해
      // pollOptions 파싱을 먼저 수행한 뒤 content + 옵션 전체를 합쳐서 한 번에 필터링함.
      const category = data.category === 'vote' ? 'vote' : 'normal';
      let rawOptions = [];
      if (category !== 'normal') {
        rawOptions = Array.isArray(data.pollOptions) ? data.pollOptions.map(t => (t || '').trim()).filter(Boolean) : [];
        const min = 2, max = VOTE_MAX_OPTIONS;
        if (rawOptions.length < min || rawOptions.length > max) return cb({ success: false, message: '투표 항목 개수를 확인해주세요.' });
      }
      const bannedWord = containsBannedWord(data.content) || rawOptions.some(t => containsBannedWord(t));
      if (bannedWord && data.confirmed !== true) return cb({ success: false, needsConfirm: true });
      let imageBlocked = false;
      if (data.photo) {
        const nsfwResult = await checkImageNsfw(data.photo);
        imageBlocked = nsfwResult.isNsfw;
      }
      const isFiltered = bannedWord || imageBlocked;

      const todayStr = new Date().toISOString().slice(0, 10);
      let earned = false;
      if (user.lastPostDate !== todayStr) { user.points += 50; user.lastPostDate = todayStr; earned = true; }
      await saveUser(user);
      let pollOptions = null, pollVotes = null;
      if (category !== 'normal') {
        pollOptions = rawOptions.slice(0, VOTE_MAX_OPTIONS).map((text, i) => ({ id: 'o' + i, text: text.slice(0, 30) }));
        pollVotes = {};
      }
      const post = {
        id: genId('p'), authorId: user.id,
        content: (data.content || '').slice(0, 100), photo: imageBlocked ? '' : (data.photo || ''), logType: data.logType || 'story',
        category, pollOptions, pollVotes,
        createdAt: Date.now(), updatedAt: Date.now(), likes: 0, likedBy: [], comments: {},
        viewCount: 0, viewedBy: {},
        filtered: isFiltered, filteredAt: isFiltered ? Date.now() : null
      };
      await savePost(post);
      user.lastPostCreatedAt = Date.now();
      await saveUser(user);
      cb({ success: true, earned, points: user.points, filtered: isFiltered });
      broadcastPosts();
      if (!isFiltered) {
        // 팔로워에게 새 글/스토리 알림 + 키워드 알림 등록 유저에게 알림 (필터링된 글은 알림 생략)
        notifyFollowersNewPost(user, post, '작성');
        notifyKeywordMatches(post, user.id, '등록');
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:update', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post || post.authorId !== userId) return cb({ success: false });

      const bannedWord = containsBannedWord(data.content);
      if (bannedWord && data.confirmed !== true) return cb({ success: false, needsConfirm: true });
      let imageBlocked = false;
      if (data.photo) {
        const nsfwResult = await checkImageNsfw(data.photo);
        imageBlocked = nsfwResult.isNsfw;
      }
      const isFiltered = bannedWord || imageBlocked;
      const wasFiltered = !!post.filtered;

      post.content = (data.content || '').slice(0, 100);
      post.photo = imageBlocked ? '' : (data.photo || '');
      post.logType = data.logType || post.logType || 'story';
      post.updatedAt = Date.now();
      post.filtered = isFiltered;
      // 원래 정상이었다가 이번에 새로 걸린 경우에만 3일 타이머 시작.
      // 이미 필터링돼있던 글이면 기존 filteredAt(마감시한)을 그대로 유지함.
      if (isFiltered && !wasFiltered) post.filteredAt = Date.now();
      if (!isFiltered) post.filteredAt = null;

      await savePost(post);
      cb({ success: true, filtered: isFiltered });
      broadcastPosts();
      if (!isFiltered) {
        // 수정된 글도 키워드 알림 대상 + 팔로워 알림 대상에 포함 (필터링된 글은 알림 생략)
        const author = await getUser(userId);
        if (author) notifyFollowersNewPost(author, post, '수정');
        notifyKeywordMatches(post, userId, '수정');
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('posts:delete', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.id);
      if (!post) return cb({ success: false });
      const requester = await getUser(userId);
      const admin = requester && isAdmin(requester);
      if (post.authorId !== userId && !admin) return cb({ success: false });
      post.deleted = true;
      post.deletedAt = Date.now();
      post.deletedByAdmin = !!(admin && post.authorId !== userId);
      await savePost(post);
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
        notifyUser(post.authorId, { type: 'like', postId: post.id, title: name, body: '게시글에 공감하였습니다' });
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 말벗스토리(및 게시글) 조회수 등록: 화면 진입/재진입 시점마다 호출되지만,
  // 같은 사람이 이미 24시간 이내에 조회한 적이 있으면 무시(카운트 증가 안 함) — 24시간당 1인 1회 제한
  socket.on('posts:view', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false });
      const post = await getPost(data.postId);
      if (!post) return cb && cb({ success: false });
      if (!post.viewedBy) post.viewedBy = {};
      const last = post.viewedBy[userId] || 0;
      const now = Date.now();
      if (now - last >= ONE_DAY) {
        post.viewedBy[userId] = now;
        post.viewCount = (post.viewCount || 0) + 1;
        await savePost(post);
      }
      cb && cb({ success: true, viewCount: post.viewCount || 0 });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('posts:vote', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb({ success: false });
      const post = await getPost(data.postId);
      if (!post || post.deleted || post.filtered) return cb({ success: false });
      if (!post.pollOptions || !post.pollOptions.length) return cb({ success: false });
      const optionId = data.optionId;
      if (!post.pollOptions.find(o => o.id === optionId)) return cb({ success: false });
      if (!post.pollVotes) post.pollVotes = {};
      post.pollVotes[userId] = optionId;
      await savePost(post);
      cb({ success: true, pollVotes: post.pollVotes });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 투표 취소: 내 투표 기록만 지워서 다시 "투표 안 한 사람" 상태로 되돌림 (다시 투표 가능해짐)
  socket.on('posts:vote_cancel', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb({ success: false });
      const post = await getPost(data.postId);
      if (!post || post.deleted || post.filtered) return cb({ success: false });
      if (!post.pollVotes) post.pollVotes = {};
      delete post.pollVotes[userId];
      await savePost(post);
      cb({ success: true, pollVotes: post.pollVotes });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  // 투표 항목별 투표자 목록 조회 (결과 화면에서 인원수 클릭 시 펼치는 목록용)
  socket.on('posts:get_voters', async (data, cb) => {
    try {
      const post = await getPost(data.postId);
      if (!post || !post.pollVotes) return cb && cb({ success: true, users: [] });
      const ids = Object.keys(post.pollVotes).filter(uid => post.pollVotes[uid] === data.optionId);
      const users = await getAllUsers();
      let list = ids.map(id => users[id]).filter(Boolean);
      list = list.map(u => u.nicknameFiltered ? { ...u, nickname: "삭제된 닉네임입니다" } : u);
      cb && cb({ success: true, users: list });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  socket.on('comments:add', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      if (!post) return cb({ success: false });
      if (post.deleted || post.filtered) return cb({ success: false, message: '삭제된 게시글에는 댓글을 작성할 수 없습니다.' });

      const isFiltered = containsBannedWord(data.content);

      const commentId = genId('c');
      const comment = {
        id: commentId, authorId: userId,
        content: data.content, parentId: data.parentId || null,
        createdAt: Date.now(), updatedAt: Date.now(),
        filtered: isFiltered
      };
      if (!post.comments) post.comments = {};
      const parentComment = data.parentId ? post.comments[data.parentId] : null;
      post.comments[commentId] = comment;
      await savePost(post);
      cb({ success: true, filtered: isFiltered });
      broadcastPosts();

      if (!isFiltered) {
        const commenter = await getUser(userId);
        const name = (commenter && commenter.nickname) || '누군가';
        if (parentComment) {
          if (parentComment.authorId && parentComment.authorId !== userId) {
            notifyUser(parentComment.authorId, { type: 'reply', postId: post.id, title: name, body: '내 댓글에 답글을 달았습니다' });
          }
        } else if (post.authorId && post.authorId !== userId) {
          notifyUser(post.authorId, { type: 'comment', postId: post.id, title: name, body: '게시글에 댓글을 달았습니다' });
        }
      }
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:like', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      const c = post && post.comments && post.comments[data.commentId];
      if (!c) return cb && cb({ success: false });
      if (!c.likedBy) c.likedBy = [];
      const i = c.likedBy.indexOf(userId);
      let liked = false;
      if (i !== -1) { c.likedBy.splice(i, 1); c.likes = Math.max(0, (c.likes || 1) - 1); }
      else { c.likedBy.push(userId); c.likes = (c.likes || 0) + 1; liked = true; }
      await savePost(post);
      cb && cb({ success: true });
      broadcastPosts();
      if (liked && c.authorId && c.authorId !== userId) {
        const liker = await getUser(userId);
        const name = (liker && liker.nickname) || '누군가';
        notifyUser(c.authorId, { type: 'like', postId: post.id, title: name, body: '댓글에 공감하였습니다' });
      }
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('comments:edit', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      const c = post && post.comments && post.comments[data.commentId];
      if (!c || c.authorId !== userId) return cb({ success: false });
      c.content = data.content;
      c.filtered = containsBannedWord(data.content);
      c.updatedAt = Date.now();
      await savePost(post);
      cb({ success: true, filtered: c.filtered });
      broadcastPosts();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('comments:delete', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const post = await getPost(data.postId);
      if (!post || !post.comments) return cb({ success: false });
      const c = post.comments[data.commentId];
      if (!c) return cb({ success: false });
      const requester = await getUser(userId);
      const admin = requester && isAdmin(requester);
      if (c.authorId !== userId && !admin) return cb({ success: false });
      c.deleted = true;
      c.deletedAt = Date.now();
      c.deletedByAdmin = !!(admin && c.authorId !== userId);
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
        const messages = (room.messages ? Object.values(room.messages) : []).filter(m => !(m.deletedFor || []).includes(userId));
        const unreadCount = messages.filter(m => m.senderId !== userId && m.senderId !== 'system' && !m.read).length;
        const muted = !!(room.muted && room.muted[userId]);
        rooms.push({ roomId, targetUser, messages, unreadCount, lastReadAt: room.lastReadAt || {}, muted });
      }
      cb({ success: true, rooms });
    } catch (e) { console.error(e); cb({ success: false, rooms: [] }); }
  });

  // 1:1 채팅 알림끄기(mute) 토글 - 기존에는 단체채팅에만 있던 기능을 1:1에도 동일하게 추가
  socket.on('chat:toggle_mute', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false });
      const snap = await db.ref(`chats/${data.roomId}/muted/${userId}`).once('value');
      const nowMuted = !snap.val();
      await db.ref(`chats/${data.roomId}/muted/${userId}`).set(nowMuted);
      cb && cb({ success: true, muted: nowMuted });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
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
      const msg = await addMessage(roomId, { senderId: user.id, text: data.text, timestamp: Date.now(), read: false });
      cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
        else if (uid !== user.id) sendWebPush(uid, { title: user.nickname || '말벗', body: msg.type === 'image' ? '사진을 보냈습니다' : (msg.text || ''), type: 'chat', roomId });
      });
      broadcastUsers();
    } catch (e) { console.error(e); cb({ success: false }); }
  });

  socket.on('chat:send_message', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds.includes(userId)) return;
      const msgPayload = { senderId: userId, text: data.text, timestamp: Date.now(), read: false };
      if (data.replyTo && data.replyTo.preview) msgPayload.replyTo = { id: data.replyTo.id || null, preview: String(data.replyTo.preview).slice(0, 60) };
      const msg = await addMessage(data.roomId, msgPayload);
      const sender = await getUser(userId);
      room.userIds.forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
        else if (uid !== userId) sendWebPush(uid, { title: (sender && sender.nickname) || '말벗', body: msg.text || '', type: 'chat', roomId: data.roomId });
      });
    } catch (e) { console.error(e); }
  });

  socket.on('chat:send_image', async (data, cb) => {
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
  });

  // 채팅 메시지 삭제: mode='everyone'(내 메시지, 30분 이내에만, 양쪽 다 삭제표시) / mode='me'(나에게만, 내 화면에서만 숨김)
  socket.on('chat:delete_message', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds || !room.userIds.includes(userId)) return cb && cb({ success: false });
      const msg = (room.messages || {})[data.messageId];
      if (!msg) return cb && cb({ success: false });
      if (data.mode === 'everyone') {
        if (msg.senderId !== userId) return cb && cb({ success: false, message: '본인 메시지만 모두에게 삭제할 수 있습니다.' });
        if (Date.now() - (msg.timestamp || 0) > 30 * 60 * 1000) return cb && cb({ success: false, message: '보낸 지 30분이 지나 모두에게 삭제할 수 없습니다.' });
        await db.ref(`chats/${data.roomId}/messages/${data.messageId}`).update({ deletedForEveryone: true, text: '', data: null });
        room.userIds.forEach(uid => {
          const sId = userToSocket[uid];
          if (sId) io.to(sId).emit('chat:message_deleted', { roomId: data.roomId, messageId: data.messageId, mode: 'everyone' });
        });
        return cb && cb({ success: true });
      } else {
        const deletedFor = msg.deletedFor || [];
        if (!deletedFor.includes(userId)) deletedFor.push(userId);
        await db.ref(`chats/${data.roomId}/messages/${data.messageId}/deletedFor`).set(deletedFor);
        return cb && cb({ success: true });
      }
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 메시지 전달: 다른 1:1 채팅방(없으면 새로 시작)으로 텍스트/이미지 메시지를 그대로 복사 전송
  socket.on('chat:forward_message', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const srcRoom = await getRoom(data.fromRoomId);
      if (!srcRoom || !srcRoom.userIds || !srcRoom.userIds.includes(userId)) return cb && cb({ success: false });
      const srcMsg = (srcRoom.messages || {})[data.messageId];
      if (!srcMsg || srcMsg.deletedForEveryone) return cb && cb({ success: false });
      const user = await getUser(userId);
      const target = await getUser(data.targetUserId);
      if (!user || !target) return cb && cb({ success: false, message: '대상 사용자를 찾을 수 없습니다.' });
      if ((user.blockedUserIds || []).includes(target.id) || (target.blockedUserIds || []).includes(user.id)) {
        return cb && cb({ success: false, message: '차단된 상대와는 대화할 수 없습니다.' });
      }
      const roomId = roomIdFor(user.id, target.id);
      let room = await getRoom(roomId);
      if (!room) {
        if (user.points < 50) return cb && cb({ success: false, needPoints: true });
        user.points -= 50;
        await saveUser(user);
        await saveRoomMeta(roomId, { roomId, userIds: [user.id, target.id] });
        await addMessage(roomId, { senderId: 'system', text: '대화가 시작되었습니다. (쌀 50개 차감)', timestamp: Date.now() });
      }
      const newMsgBase = srcMsg.type === 'image'
        ? { senderId: userId, type: 'image', data: srcMsg.data, timestamp: Date.now(), read: false, forwarded: true }
        : { senderId: userId, text: srcMsg.text, timestamp: Date.now(), read: false, forwarded: true };
      const msg = await addMessage(roomId, newMsgBase);
      cb && cb({ success: true, roomId, points: user.points });
      [user.id, target.id].forEach(uid => {
        const sId = userToSocket[uid];
        if (sId) io.to(sId).emit('chat:new_message', { roomId, message: msg, senderNickname: user.nickname });
        else if (uid !== user.id) sendWebPush(uid, { title: user.nickname || '말벗', body: msg.type === 'image' ? '사진을 보냈습니다' : (msg.text || ''), type: 'chat', roomId });
      });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 채팅방을 열람하면(=내 채팅창에 들어오면) 상대가 보낸 안읽은 메시지를 모두 읽음 처리
  // 0-21: upToTimestamp가 오면(=실제로 화면에 보인 마지막 메시지 시각) 그 시점까지 온 메시지만 읽음 처리.
  // 값이 없으면 기존 방식대로 현재 시점 기준 전체 읽음 처리(하위호환용 폴백).
  socket.on('chat:mark_read', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getRoom(data.roomId);
      if (!room || !room.userIds || !room.userIds.includes(userId)) return;
      const upToTimestamp = data && data.upToTimestamp;
      const messages = room.messages || {};
      const updates = {};
      Object.keys(messages).forEach(mid => {
        const m = messages[mid];
        if (!m || m.senderId === userId || m.senderId === 'system' || m.read) return;
        if (upToTimestamp && m.timestamp > upToTimestamp) return;
        updates[`chats/${data.roomId}/messages/${mid}/read`] = true;
      });
      const prevLastReadAt = (room.lastReadAt && room.lastReadAt[userId]) || 0;
      const now = Date.now();
      const newLastReadAt = upToTimestamp ? Math.max(prevLastReadAt, upToTimestamp) : now;
      updates[`chats/${data.roomId}/lastReadAt/${userId}`] = newLastReadAt;
      await db.ref().update(updates);
      const otherId = room.userIds.find(id => id !== userId);
      const sId = userToSocket[otherId];
      if (sId) io.to(sId).emit('chat:read_receipt', { roomId: data.roomId, userId, lastReadAt: newLastReadAt });
    } catch (e) { console.error(e); }
  });

  // ================= 단체채팅방(오픈채팅 스타일) =================
  // 방 생성: 방 이름 최대 15자, 나=방장으로 시작, 초대코드 자동 발급
  socket.on('group:create', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const title = String((data && data.title) || '').trim().slice(0, 15);
      if (!title) return cb && cb({ success: false, message: '채팅방 이름을 입력해주세요.' });
      const intro = String((data && data.intro) || '').trim().slice(0, 60);
      const roomRef = db.ref('groupChats').push();
      const roomId = roomRef.key;
      let inviteCode;
      do { inviteCode = generateInviteCode(); } while ((await db.ref(`groupInviteCodes/${inviteCode}`).once('value')).exists());
      const meta = { roomId, title, intro, ownerId: userId, subOwnerIds: [], memberIds: [userId], inviteCode, createdAt: Date.now() };
      await db.ref(`groupChats/${roomId}/meta`).set(meta);
      await db.ref(`groupInviteCodes/${inviteCode}`).set(roomId);
      await db.ref(`userGroupChats/${userId}/${roomId}`).set(true);
      cb && cb({ success: true, roomId, inviteCode });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 초대코드로 입장: 강퇴(재입장금지)/정원(50명) 체크
  socket.on('group:join', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const inviteCode = data && data.inviteCode;
      const roomIdSnap = await db.ref(`groupInviteCodes/${inviteCode}`).once('value');
      const roomId = roomIdSnap.val();
      if (!roomId) return cb && cb({ success: false, message: '유효하지 않은 초대링크입니다.' });
      const room = await getGroupRoom(roomId);
      if (!room || !room.meta) return cb && cb({ success: false, message: '존재하지 않는 채팅방입니다.' });
      const meta = room.meta;
      if (room.kickedUserIds && room.kickedUserIds[userId]) return cb && cb({ success: false, message: '재입장이 제한된 채팅방입니다.' });
      if ((meta.memberIds || []).includes(userId)) return cb && cb({ success: true, roomId });
      if ((meta.memberIds || []).length >= 50) return cb && cb({ success: false, message: '채팅방 인원이 가득 찼습니다.' });
      const memberIds = [...(meta.memberIds || []), userId];
      await db.ref(`groupChats/${roomId}/meta/memberIds`).set(memberIds);
      await db.ref(`userGroupChats/${userId}/${roomId}`).set(true);
      const user = await getUser(userId);
      const sysMsg = await addGroupMessage(roomId, { senderId: 'system', text: `${user ? user.nickname : '알 수 없음'}님이 입장했습니다.`, timestamp: Date.now() });
      emitToGroupMembers(memberIds, 'group:new_message', { roomId, message: sysMsg });
      emitToGroupMembers(memberIds, 'group:member_joined', { roomId, userId, memberIds });
      cb && cb({ success: true, roomId });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 방 정보(사진/참여자/내 권한/알림설정) 조회 - 방 정보화면(≡ 버튼)에서 사용
  socket.on('group:info', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return cb && cb({ success: false });
      const meta = room.meta;
      const members = [];
      for (const uid of (meta.memberIds || [])) {
        const u = await getUser(uid);
        if (u) {
          members.push({
            id: u.id, nickname: u.nickname, photo: (u.photos || [])[0] || null, gender: u.gender,
            role: uid === meta.ownerId ? 'owner' : (meta.subOwnerIds || []).includes(uid) ? 'subowner' : 'member'
          });
        }
      }
      const allMessages = room.messages ? Object.values(room.messages) : [];
      const gallery = allMessages.filter(m => m.type === 'image' || m.type === 'video').sort((a, b) => b.timestamp - a.timestamp).slice(0, 60);
      const myRole = userId === meta.ownerId ? 'owner' : (meta.subOwnerIds || []).includes(userId) ? 'subowner' : 'member';
      const muted = !!(room.muted && room.muted[userId]);
      const blockedUserIds = Object.keys((room.blockedUsers && room.blockedUsers[userId]) || {});
      cb && cb({ success: true, meta, members, gallery, myRole, muted, blockedUserIds });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 방 나가기: 방장이 나가면 부방장(먼저 임명된 사람 우선) 자동 승계, 부방장도 없으면 가장 오래 있던 멤버 승계, 아무도 없으면 방 삭제
  socket.on('group:leave', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return cb && cb({ success: false });
      const meta = room.meta;
      const memberIds = (meta.memberIds || []).filter(id => id !== userId);
      const subOwnerIds = (meta.subOwnerIds || []).filter(id => id !== userId);
      let ownerId = meta.ownerId;
      await db.ref(`userGroupChats/${userId}/${data.roomId}`).remove();
      if (userId === meta.ownerId) {
        if (subOwnerIds.length) {
          ownerId = subOwnerIds.shift();
        } else if (memberIds.length) {
          ownerId = memberIds[0];
        } else {
          await deleteGroupRoomDb(data.roomId);
          await db.ref(`groupInviteCodes/${meta.inviteCode}`).remove();
          return cb && cb({ success: true, roomDeleted: true });
        }
      }
      await db.ref(`groupChats/${data.roomId}/meta`).update({ memberIds, subOwnerIds, ownerId });
      const user = await getUser(userId);
      const sysMsg = await addGroupMessage(data.roomId, { senderId: 'system', text: `${user ? user.nickname : '알 수 없음'}님이 나갔습니다.`, timestamp: Date.now() });
      emitToGroupMembers(memberIds, 'group:new_message', { roomId: data.roomId, message: sysMsg });
      emitToGroupMembers(memberIds, 'group:member_left', { roomId: data.roomId, userId, memberIds, ownerId });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 강퇴 (방장 전용): banRejoin=true면 초대링크로도 재입장 불가
  socket.on('group:kick', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || room.meta.ownerId !== userId) return cb && cb({ success: false, message: '방장만 강퇴할 수 있습니다.' });
      const meta = room.meta;
      const targetId = data.targetId;
      if (targetId === userId) return cb && cb({ success: false });
      const memberIds = (meta.memberIds || []).filter(id => id !== targetId);
      const subOwnerIds = (meta.subOwnerIds || []).filter(id => id !== targetId);
      await db.ref(`groupChats/${data.roomId}/meta`).update({ memberIds, subOwnerIds });
      await db.ref(`userGroupChats/${targetId}/${data.roomId}`).remove();
      if (data.banRejoin) await db.ref(`groupChats/${data.roomId}/kickedUserIds/${targetId}`).set(true);
      const targetSocket = userToSocket[targetId];
      if (targetSocket) io.to(targetSocket).emit('group:kicked', { roomId: data.roomId });
      const target = await getUser(targetId);
      const sysMsg = await addGroupMessage(data.roomId, { senderId: 'system', text: `${target ? target.nickname : '알 수 없음'}님이 내보내졌습니다.`, timestamp: Date.now() });
      emitToGroupMembers(memberIds, 'group:new_message', { roomId: data.roomId, message: sysMsg });
      emitToGroupMembers(memberIds, 'group:member_left', { roomId: data.roomId, userId: targetId, memberIds });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 부방장 임명/해제 (방장 전용, 최대 2명)
  socket.on('group:appoint_subowner', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || room.meta.ownerId !== userId) return cb && cb({ success: false, message: '방장만 임명할 수 있습니다.' });
      const meta = room.meta;
      if (!(meta.memberIds || []).includes(data.targetId)) return cb && cb({ success: false });
      let subOwnerIds = meta.subOwnerIds || [];
      if (subOwnerIds.includes(data.targetId)) return cb && cb({ success: true, subOwnerIds });
      if (subOwnerIds.length >= 2) return cb && cb({ success: false, message: '부방장은 최대 2명까지 임명할 수 있습니다.' });
      subOwnerIds = [...subOwnerIds, data.targetId];
      await db.ref(`groupChats/${data.roomId}/meta/subOwnerIds`).set(subOwnerIds);
      emitToGroupMembers(meta.memberIds, 'group:subowner_changed', { roomId: data.roomId, subOwnerIds });
      cb && cb({ success: true, subOwnerIds });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  socket.on('group:revoke_subowner', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || room.meta.ownerId !== userId) return cb && cb({ success: false, message: '방장만 해제할 수 있습니다.' });
      const meta = room.meta;
      const subOwnerIds = (meta.subOwnerIds || []).filter(id => id !== data.targetId);
      await db.ref(`groupChats/${data.roomId}/meta/subOwnerIds`).set(subOwnerIds);
      emitToGroupMembers(meta.memberIds, 'group:subowner_changed', { roomId: data.roomId, subOwnerIds });
      cb && cb({ success: true, subOwnerIds });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 방별 알림 온/오프 토글
  socket.on('group:toggle_mute', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const snap = await db.ref(`groupChats/${data.roomId}/muted/${userId}`).once('value');
      const nowMuted = !snap.val();
      await db.ref(`groupChats/${data.roomId}/muted/${userId}`).set(nowMuted);
      cb && cb({ success: true, muted: nowMuted });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 방별 특정 유저 차단/해제 (개인 설정 - 나에게만 적용, 상대에겐 통보 안 됨). 차단하면 그 사람 메시지가 "차단한 상대방의 메시지입니다"로 대체 표시됨
  socket.on('group:toggle_block', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return cb && cb({ success: false });
      const targetId = data.targetId;
      if (!targetId || targetId === userId) return cb && cb({ success: false });
      const snap = await db.ref(`groupChats/${data.roomId}/blockedUsers/${userId}/${targetId}`).once('value');
      const nowBlocked = !snap.val();
      if (nowBlocked) await db.ref(`groupChats/${data.roomId}/blockedUsers/${userId}/${targetId}`).set(true);
      else await db.ref(`groupChats/${data.roomId}/blockedUsers/${userId}/${targetId}`).remove();
      cb && cb({ success: true, blocked: nowBlocked });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 메시지/사진 전송 (전체 멤버에게 브로드캐스트)
  socket.on('group:send_message', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return cb && cb({ success: false });
      const msgPayload = { senderId: userId, text: data.text, timestamp: Date.now() };
      if (data.replyTo && data.replyTo.preview) msgPayload.replyTo = { id: data.replyTo.id || null, preview: String(data.replyTo.preview).slice(0, 60) };
      const msg = await addGroupMessage(data.roomId, msgPayload);
      const sender = await getUser(userId);
      emitToGroupMembers(room.meta.memberIds, 'group:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  socket.on('group:send_image', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return cb && cb({ success: false });
      const nsfwResult = await checkImageNsfw(data.image);
      if (nsfwResult.isNsfw) return cb && cb({ success: false, blocked: true, message: '부적절한 사진으로 감지되어 전송할 수 없습니다.' });
      const msg = await addGroupMessage(data.roomId, { senderId: userId, type: 'image', data: data.image, timestamp: Date.now() });
      const sender = await getUser(userId);
      emitToGroupMembers(room.meta.memberIds, 'group:new_message', { roomId: data.roomId, message: msg, senderNickname: sender && sender.nickname });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 그룹 메시지 삭제: 1:1 chat:delete_message와 동일한 규칙(모두에게 삭제는 본인 메시지+30분 이내만)
  socket.on('group:delete_message', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return cb && cb({ success: false });
      const msg = (room.messages || {})[data.messageId];
      if (!msg) return cb && cb({ success: false });
      if (data.mode === 'everyone') {
        if (msg.senderId !== userId) return cb && cb({ success: false, message: '본인 메시지만 모두에게 삭제할 수 있습니다.' });
        if (Date.now() - (msg.timestamp || 0) > 30 * 60 * 1000) return cb && cb({ success: false, message: '보낸 지 30분이 지나 모두에게 삭제할 수 없습니다.' });
        await db.ref(`groupChats/${data.roomId}/messages/${data.messageId}`).update({ deletedForEveryone: true, text: '', data: null });
        emitToGroupMembers(room.meta.memberIds, 'group:message_deleted', { roomId: data.roomId, messageId: data.messageId, mode: 'everyone' });
        return cb && cb({ success: true });
      } else {
        const deletedFor = msg.deletedFor || [];
        if (!deletedFor.includes(userId)) deletedFor.push(userId);
        await db.ref(`groupChats/${data.roomId}/messages/${data.messageId}/deletedFor`).set(deletedFor);
        return cb && cb({ success: true });
      }
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 읽음 처리: lastReadAt 갱신 후 다른 멤버들에게 실시간 전파 (말풍선 옆 "안읽은 인원 수" 계산용)
  // 0-21: upToTimestamp가 오면(=실제로 화면에 보인 마지막 메시지 시각) 그 시점까지만 읽은 것으로 기록.
  // 값이 없으면 기존 방식대로 현재 시점 기준 전체 읽음 처리(하위호환용 폴백).
  socket.on('group:mark_read', async (data) => {
    try {
      const userId = socketToUser[socket.id];
      const room = await getGroupRoom(data.roomId);
      if (!room || !room.meta || !(room.meta.memberIds || []).includes(userId)) return;
      const upToTimestamp = data && data.upToTimestamp;
      const prevLastReadAt = (room.lastReadAt && room.lastReadAt[userId]) || 0;
      const now = Date.now();
      const newLastReadAt = upToTimestamp ? Math.max(prevLastReadAt, upToTimestamp) : now;
      await db.ref(`groupChats/${data.roomId}/lastReadAt/${userId}`).set(newLastReadAt);
      emitToGroupMembers((room.meta.memberIds || []).filter(id => id !== userId), 'group:read_receipt', { roomId: data.roomId, userId, lastReadAt: newLastReadAt });
    } catch (e) { console.error(e); }
  });

  // 공개 디렉토리 검색: 제목 기준 (카카오 오픈채팅처럼 미참여 방도 검색해서 바로 입장 가능)
  socket.on('group:search', async (data, cb) => {
    try {
      const q = String((data && data.query) || '').trim().toLowerCase();
      if (!q) return cb && cb({ success: true, rooms: [] });
      const snap = await db.ref('groupChats').once('value');
      const all = snap.val() || {};
      const results = Object.keys(all)
        .map(roomId => all[roomId].meta)
        .filter(meta => meta && meta.title && meta.title.toLowerCase().includes(q))
        .map(meta => ({ roomId: meta.roomId, title: meta.title, intro: meta.intro, memberCount: (meta.memberIds || []).length, inviteCode: meta.inviteCode, createdAt: meta.createdAt || 0 }))
        .slice(0, 30);
      cb && cb({ success: true, rooms: results });
    } catch (e) { console.error(e); cb && cb({ success: false, rooms: [] }); }
  });

  // 내 단체채팅방 목록 (채팅목록 화면용, 안읽음 숫자는 lastReadAt 이후 메시지 개수로 계산)
  socket.on('group:get_list', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      const idxSnap = await db.ref(`userGroupChats/${userId}`).once('value');
      const roomIds = Object.keys(idxSnap.val() || {});
      const rooms = [];
      for (const roomId of roomIds) {
        const room = await getGroupRoom(roomId);
        if (!room || !room.meta) continue;
        const messages = (room.messages ? Object.values(room.messages) : []).filter(m => !(m.deletedFor || []).includes(userId));
        const myLastReadAt = (room.lastReadAt && room.lastReadAt[userId]) || 0;
        const unreadCount = messages.filter(m => m.senderId !== userId && m.senderId !== 'system' && m.timestamp > myLastReadAt).length;
        rooms.push({ roomId, meta: room.meta, messages, unreadCount, lastReadAt: room.lastReadAt || {}, muted: !!(room.muted && room.muted[userId]) });
      }
      cb && cb({ success: true, rooms });
    } catch (e) { console.error(e); cb && cb({ success: false, rooms: [] }); }
  });


  // 팔로우 / 언팔로우 토글 (알림은 발생시키지 않음)
  socket.on('user:follow', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      const target = await getUser(targetId);
      if (!user || !target || userId === targetId) return cb && cb({ success: false });
      user.followingIds = user.followingIds || [];
      target.followerIds = target.followerIds || [];
      const isFollowing = user.followingIds.includes(targetId);
      if (isFollowing) {
        user.followingIds = user.followingIds.filter(id => id !== targetId);
        target.followerIds = target.followerIds.filter(id => id !== userId);
      } else {
        user.followingIds.push(targetId);
        target.followerIds.push(userId);
      }
      await saveUser(user);
      await saveUser(target);
      if (!isFollowing) {
        const followerName = user.nickname || '누군가';
        notifyUser(targetId, { type: 'follow', userId: user.id, title: followerName, body: '나를 팔로우하였습니다' });
      }
      cb && cb({ success: true, following: !isFollowing });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 특정 유저를 팔로우하는 사람 목록 (제3자도 조회 가능)
  socket.on('user:get_followers', async (targetId, cb) => {
    try {
      const target = await getUser(targetId);
      const ids = (target && target.followerIds) || [];
      const users = await getAllUsers();
      let list = ids.map(id => users[id]).filter(Boolean);
      list = list.map(u => u.nicknameFiltered ? { ...u, nickname: "삭제된 닉네임입니다" } : u);
      cb && cb({ success: true, users: list });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 특정 유저가 팔로우하는 사람 목록 (제3자도 조회 가능) - 팔로잉 목록 모달용
  socket.on('user:get_following', async (targetId, cb) => {
    try {
      const target = await getUser(targetId);
      const ids = (target && target.followingIds) || [];
      const users = await getAllUsers();
      let list = ids.map(id => users[id]).filter(Boolean);
      list = list.map(u => u.nicknameFiltered ? { ...u, nickname: "삭제된 닉네임입니다" } : u);
      cb && cb({ success: true, users: list });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 프로필 공감 토글 (알림은 발생시키지 않음, 제3자도 공감자 목록 조회 가능)
  socket.on('profile:like', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = await getUser(targetId);
      if (!target || userId === targetId) return cb && cb({ success: false });
      target.profileLikedBy = target.profileLikedBy || [];
      const i = target.profileLikedBy.indexOf(userId);
      let liked = false;
      if (i !== -1) target.profileLikedBy.splice(i, 1);
      else { target.profileLikedBy.push(userId); liked = true; }
      await saveUser(target);
      cb && cb({ success: true, liked, count: target.profileLikedBy.length });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  socket.on('user:get_profile_likers', async (targetId, cb) => {
    try {
      const target = await getUser(targetId);
      const ids = (target && target.profileLikedBy) || [];
      const users = await getAllUsers();
      const list = ids.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, users: list });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 차단한 회원 목록 조회 (프로필 목록처럼 그대로 재사용할 수 있게 유저 객체 배열로 반환)
  socket.on('user:get_blocked_list', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb({ success: false, users: [] });
      const ids = user.blockedUserIds || [];
      const users = await getAllUsers();
      const list = ids.map(id => users[id]).filter(Boolean);
      cb({ success: true, users: list });
    } catch (e) { console.error(e); cb({ success: false, users: [] }); }
  });

  // 프로필 방문 기록 (KST 날짜별로 저장 - 날짜가 바뀌면 자연히 새 목록이 되어 "일일 초기화" 효과)
  // 본인 프로필을 본인이 보는 경우는 기록하지 않음
  socket.on('profile:record_visit', async (data, cb) => {
    try {
      const visitorId = socketToUser[socket.id];
      const targetId = data && data.targetUserId;
      if (!visitorId || !targetId || visitorId === targetId) return cb && cb({ success: true });
      const today = kstDateStr(new Date());
      await db.ref(`profileVisits/${targetId}/${today}/${visitorId}`).set(Date.now());
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 오늘(KST) 내 프로필 방문자 수 + 목록 조회 (본인만 조회 가능 - 로그인한 본인 소켓 기준으로 본인 것만 조회)
  socket.on('profile:get_today_visitors', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false, count: 0, visitors: [] });
      const today = kstDateStr(new Date());
      const snap = await db.ref(`profileVisits/${userId}/${today}`).once('value');
      const raw = snap.val() || {};
      const visitorIds = Object.keys(raw).sort((a, b) => raw[b] - raw[a]);
      const users = await getAllUsers();
      const visitors = visitorIds.map(id => users[id]).filter(Boolean);
      cb && cb({ success: true, count: visitorIds.length, visitors });
    } catch (e) { console.error(e); cb && cb({ success: false, count: 0, visitors: [] }); }
  });

  // 0-20: 방문자 "전체 기간" 조회 - 골드 이상 구독 중인 본인만 실제 목록 열람 가능(오늘 방문자는 위 핸들러로 계속 무료 열람)
  socket.on('profile:get_all_visitors', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false, count: 0, visitors: [] });
      const snap = await db.ref(`profileVisits/${userId}`).once('value');
      const byDate = snap.val() || {};
      const latestByVisitor = {};
      Object.keys(byDate).forEach(date => {
        const dayMap = byDate[date] || {};
        Object.keys(dayMap).forEach(vId => {
          const ts = dayMap[vId];
          if (!latestByVisitor[vId] || ts > latestByVisitor[vId]) latestByVisitor[vId] = ts;
        });
      });
      const visitorIds = Object.keys(latestByVisitor).sort((a, b) => latestByVisitor[b] - latestByVisitor[a]);
      const me = await getUser(userId);
      const users = await getAllUsers();
      const rawVisitors = visitorIds.map(id => users[id]).filter(Boolean);
      const locked = !hasTierAtLeast(me, 'gold');
      // 0-28: locked이면 실제 닉네임/사진 대신 마스킹된 정보만 내려보냄(브라우저에서 실제 데이터 노출 방지)
      const visitors = locked ? rawVisitors.map(maskUserForLockedTeaser) : rawVisitors;
      cb && cb({ success: true, locked, count: visitorIds.length, visitors });
    } catch (e) { console.error(e); cb && cb({ success: false, count: 0, visitors: [] }); }
  });

  // 차단 해제
  socket.on('user:unblock', async (targetId, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb && cb({ success: false });
      user.blockedUserIds = (user.blockedUserIds || []).filter(id => id !== targetId);
      await saveUser(user);
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 본인이 받은 경고 이력 조회 (설정화면 경고 이력 메뉴)
  socket.on('user:get_warnings', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const user = await getUser(userId);
      if (!user) return cb && cb({ success: false, warnings: [] });
      cb && cb({ success: true, warnings: user.warnings || [] });
    } catch (e) { console.error(e); cb && cb({ success: false, warnings: [] }); }
  });

  // 명시적 로그아웃 (연결은 유지한 채 온라인 상태만 즉시 내려줌)
  socket.on('auth:logout', async (cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (userId) {
        const user = await getUser(userId);
        if (user) { user.isOnline = false; user.lastSeen = Date.now(); await saveUser(user); }
        delete userToSocket[userId];
        delete socketToUser[socket.id];
        broadcastUsers();
      }
      cb && cb({ success: true });
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

  // 신고 접수: 프론트가 보내는 {category, targetContext:{type,id}} 형태를 그대로 받아 reports 노드에 저장함
  // targetContext.type은 'post'(게시글) | 'user'(프로필) | 'chat'(채팅방) 중 하나
  socket.on('user:report', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const { category, targetContext } = data || {};
      if (!category || !targetContext || !targetContext.type || !targetContext.id) {
        return cb && cb({ success: false });
      }
      const ref = db.ref('reports').push();
      const report = {
        id: ref.key,
        type: targetContext.type,
        targetId: targetContext.id,
        reporterUid: userId || null,
        category,
        status: 'pending',
        createdAt: Date.now()
      };
      // 0-37: 채팅 메시지 롱프레스 신고는 messageId를 함께 보내 메시지 단위로 특정함
      if (targetContext.messageId) {
        report.messageId = targetContext.messageId;
        if (targetContext.messagePreview) report.messagePreview = targetContext.messagePreview;
      }
      await ref.set(report);
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // ===================== 관리자 대시보드 =====================
  // 같은 대상(type+targetId)에 대해 미처리 신고가 이 횟수 이상 누적되면 관리자 목록 최상단에 강조 노출함
  const URGENT_REPORT_THRESHOLD = 3;
  // 신고 목록 조회(게시글/프로필/채팅 전체) + 종류별 미처리(pending) 개수 집계
  socket.on('admin:reports:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const snap = await db.ref('reports').once('value');
      const all = snap.val() || {};
      // 0-29: 같은 대상(type::targetId)에 미처리 신고가 몇 건 쌓였는지 집계 - 신고 "건수"가 아니라
      // 서로 다른 "신고자 수"로 세야 함(같은 사람이 여러 번 신고해서 3회를 채우는 방식으로
      // 긴급 표시를 악용/조작하는 것을 막기 위함)
      const pendingReportersByTarget = {};
      Object.values(all).forEach(r => {
        if (r.status !== 'pending') return;
        const key = `${r.type}::${r.targetId}`;
        if (!pendingReportersByTarget[key]) pendingReportersByTarget[key] = new Set();
        pendingReportersByTarget[key].add(r.reporterUid || r.id);
      });
      const pendingCountByTarget = {};
      Object.keys(pendingReportersByTarget).forEach(key => {
        pendingCountByTarget[key] = pendingReportersByTarget[key].size;
      });
      // 누적 신고 많은 대상(내림차순) 우선, 그다음 최신순 정렬
      const list = Object.values(all).sort((a, b) => {
        const ac = pendingCountByTarget[`${a.type}::${a.targetId}`] || 0;
        const bc = pendingCountByTarget[`${b.type}::${b.targetId}`] || 0;
        if (bc !== ac) return bc - ac;
        return (b.createdAt || 0) - (a.createdAt || 0);
      });
      const users = await getAllUsers();
      const enriched = await Promise.all(list.map(async r => {
        let targetLabel = '';
        let accusedNickname = '(알 수 없음)';
        if (r.type === 'post') {
          const p = await getPost(r.targetId);
          targetLabel = p ? (p.content || '').slice(0, 40) : '(삭제된 게시글)';
          accusedNickname = p && users[p.authorId] ? users[p.authorId].nickname : '(탈퇴한 사용자)';
        } else if (r.type === 'user') {
          const u = users[r.targetId];
          targetLabel = u ? u.nickname : '(탈퇴한 사용자)';
          accusedNickname = targetLabel;
        } else if (r.type === 'chat') {
          const room = await getRoom(r.targetId);
          const otherId = room && room.userIds ? room.userIds.find(uid => uid !== r.reporterUid) : null;
          accusedNickname = otherId && users[otherId] ? users[otherId].nickname : '(알 수 없음)';
          if (r.messageId) {
            // 0-37: 메시지 단위 신고는 방 이름 대신 신고된 메시지 내용을 미리보기로 보여줌
            const msg = room && room.messages && room.messages[r.messageId];
            targetLabel = msg
              ? (msg.deletedForEveryone ? '(이미 삭제된 메시지)' : (msg.type === 'image' ? '(이미지)' : (msg.text || '').slice(0, 40)))
              : (r.messagePreview || '(삭제된 메시지)');
          } else {
            targetLabel = `채팅방 ${r.targetId}`;
          }
        } else if (r.type === 'comment') {
          const [postId, commentId] = (r.targetId || '').split('::');
          const p = postId ? await getPost(postId) : null;
          const c = p && p.comments && p.comments[commentId];
          targetLabel = c ? (c.content || '').slice(0, 40) : '(삭제된 댓글)';
          accusedNickname = c && users[c.authorId] ? users[c.authorId].nickname : '(탈퇴한 사용자)';
        }
        const reporter = users[r.reporterUid];
        const sameTargetPendingCount = pendingCountByTarget[`${r.type}::${r.targetId}`] || 0;
        return { ...r, targetLabel, accusedNickname, reporterNickname: reporter ? reporter.nickname : '(알 수 없음)', sameTargetPendingCount, isUrgent: sameTargetPendingCount >= URGENT_REPORT_THRESHOLD };
      }));
      const counts = { post: 0, user: 0, chat: 0, comment: 0 };
      enriched.forEach(r => { if (r.status === 'pending' && counts[r.type] !== undefined) counts[r.type]++; });
      cb && cb({ success: true, reports: enriched, counts });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 신고 처리: action은 'delete_post'|'ban_user'|'delete_room'|'delete_message'|'complete_only' 중 하나
  // 0-37: 채팅 메시지 1개 단위 삭제 구현 완료(messageId가 있는 신고는 방 전체가 아니라 해당 메시지만 삭제 가능)
  socket.on('admin:reports:resolve', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const { reportId, action } = data || {};
      const snap = await db.ref(`reports/${reportId}`).once('value');
      const report = snap.val();
      if (!report) return cb && cb({ success: false });

      if (action === 'delete_post' && report.type === 'post') {
        const post = await getPost(report.targetId);
        if (post) {
          post.deleted = true;
          post.deletedAt = Date.now();
          post.deletedByAdmin = true;
          await savePost(post);
          broadcastPosts();
        }
      } else if (action === 'ban_user' && report.type === 'user') {
        const target = await getUser(report.targetId);
        if (target) {
          target.isBanned = true;
          target.bannedAt = Date.now();
          await saveUser(target);
          const sId = userToSocket[target.id];
          if (sId) { io.to(sId).emit('account:banned'); delete userToSocket[target.id]; }
          broadcastUsers();
        }
      } else if (action === 'delete_room' && report.type === 'chat') {
        await deleteRoom(report.targetId);
      } else if (action === 'delete_message' && report.type === 'chat' && report.messageId) {
        // 0-37: 방 전체가 아니라 신고된 메시지 1개만 삭제(기존 '나에게만/모두에게 삭제'와 동일한 소프트 삭제 방식 재사용)
        await db.ref(`chats/${report.targetId}/messages/${report.messageId}`).update({ deletedForEveryone: true, text: '', data: null });
        const msgRoom = await getRoom(report.targetId);
        if (msgRoom && msgRoom.userIds) {
          msgRoom.userIds.forEach(uid => {
            const sId = userToSocket[uid];
            if (sId) io.to(sId).emit('chat:message_deleted', { roomId: report.targetId, messageId: report.messageId, mode: 'everyone' });
          });
        }
      } else if (action === 'delete_comment' && report.type === 'comment') {
        const [postId, commentId] = (report.targetId || '').split('::');
        const post = postId ? await getPost(postId) : null;
        const c = post && post.comments && post.comments[commentId];
        if (c) {
          c.deleted = true;
          c.deletedAt = Date.now();
          c.deletedByAdmin = true;
          await savePost(post);
          broadcastPosts();
        }
      } else if (action === 'warn_user') {
        const accusedId = await getAccusedUserId(report);
        const target = accusedId ? await getUser(accusedId) : null;
        if (target) {
          target.warnings = target.warnings || [];
          target.warnings.push({ reason: report.category || '', at: Date.now() });
          target.pendingWarningNotify = { at: Date.now(), notified: false };
          const sId = userToSocket[target.id];
          if (sId) { io.to(sId).emit('account:warned', { message: WARNING_MESSAGE }); target.pendingWarningNotify.notified = true; }
          // 앱을 꺼놨거나 로그아웃 상태여도 확실히 알 수 있도록 웹푸시도 함께 발송(문자X, 인앱 알림창 성격의 푸시)
          else sendWebPush(target.id, { title: '경고 안내', body: WARNING_MESSAGE, type: 'warning' });
          await saveUser(target);
        }
      } else if (action === 'force_withdraw_user') {
        // 0-25: 경고 누적 자동처리는 하지 않고, 관리자가 신고 화면에서 수동으로 강제탈퇴시킬 때만 실행됨
        const accusedId = await getAccusedUserId(report);
        if (accusedId) {
          const sId = userToSocket[accusedId];
          if (sId) { io.to(sId).emit('account:force_withdrawn', { message: FORCE_WITHDRAW_MESSAGE }); delete userToSocket[accusedId]; }
          else sendWebPush(accusedId, { title: '계정 탈퇴 안내', body: FORCE_WITHDRAW_MESSAGE, type: 'force_withdrawn' });
          await forceWithdrawUserAccount(accusedId, '이용약관 위반으로 강제 탈퇴 처리된 사용자입니다.');
          broadcastUsers();
          broadcastPosts();
        }
      }

      await db.ref(`reports/${reportId}`).update({ status: 'resolved', resolveAction: action, resolvedAt: Date.now() });

      // 0-30: 신고 처리 결과를 신고자에게 알려줌(실제 조치가 있었는지 여부만 구분, 상대방 신상정보는 노출 안 함)
      if (report.reporterUid) {
        const tookAction = action !== 'complete_only';
        const resultMessage = tookAction
          ? '신고해주신 내용을 확인해 조치를 완료했습니다. 소중한 제보 감사해요.'
          : '신고해주신 내용을 검토했지만, 이번 건은 별도 조치 없이 종료됐어요.';
        const sId = userToSocket[report.reporterUid];
        if (sId) io.to(sId).emit('report:resolved_notify', { message: resultMessage });
        else sendWebPush(report.reporterUid, { title: '신고 처리 결과', body: resultMessage, type: 'report_resolved' });
      }

      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 전체 채팅방 목록(서비스 내 모든 방) - 관리자만
  socket.on('admin:chatrooms:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const snap = await db.ref('chats').once('value');
      const allChats = snap.val() || {};
      const users = await getAllUsers();
      const rooms = Object.keys(allChats).map(roomId => {
        const room = allChats[roomId];
        const messages = room.messages ? Object.values(room.messages) : [];
        const participants = (room.userIds || []).map(uid => (users[uid] && users[uid].nickname) || '(탈퇴한 사용자)');
        const lastMsg = messages[messages.length - 1] || {};
        return {
          roomId,
          participants,
          userIds: room.userIds || [],
          messageCount: messages.length,
          lastMessagePreview: lastMsg.type === 'image' ? '(사진)' : (lastMsg.text || ''),
          lastMessageAt: lastMsg.timestamp || 0
        };
      }).sort((a, b) => b.lastMessageAt - a.lastMessageAt);
      cb && cb({ success: true, rooms });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 특정 채팅방의 메시지 전체(관리자 열람용) - 관리자만
  socket.on('admin:chatroom:get_messages', async (roomId, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const room = await getRoom(roomId);
      if (!room) return cb && cb({ success: false });
      const users = await getAllUsers();
      const messages = room.messages ? Object.values(room.messages) : [];
      cb && cb({ success: true, messages, users: (room.userIds || []).map(uid => ({ id: uid, nickname: (users[uid] && users[uid].nickname) || '(탈퇴한 사용자)' })) });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 0-20: 구독 등급 표시 옵션(로고 색상 적용 / 상대방에게 등급뱃지 노출) 온오프 - 활성 구독 중일 때만 저장 가능
  socket.on('account:set_subscription_prefs', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = userId ? await getUser(userId) : null;
      if (!target) return cb && cb({ success: false });
      if (!hasTierAtLeast(target, 'gold')) return cb && cb({ success: false, message: '구독 중일 때만 설정할 수 있습니다.' });
      target.subscription = target.subscription || {};
      if (typeof (data && data.logoColorOn) === 'boolean') target.subscription.logoColorOn = data.logoColorOn;
      if (typeof (data && data.badgeOn) === 'boolean') target.subscription.badgeOn = data.badgeOn;
      await saveUser(target);
      cb && cb({ success: true, subscription: target.subscription });
      broadcastUsers();
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // ===================== 개인 전화번호 등록/변경 =====================
  // 카카오 가입 후 최초 1회만 본인 전화번호를 직접 입력받아 저장(카카오 실제번호 대조는 카카오 비즈앱 심사 필요해 이번 범위 아님).
  // 이미 번호가 등록돼 있으면 phoneChangeApproved(관리자 승인)가 true일 때만 재등록 가능하고, 성공하면 승인 플래그는 소모됨.
  socket.on('account:set_phone', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = userId ? await getUser(userId) : null;
      if (!target) return cb && cb({ success: false });
      if (target.phone && !target.phoneChangeApproved) return cb && cb({ success: false, message: '이미 등록된 전화번호가 있습니다. 변경은 고객센터로 문의해주세요.' });
      if (!/^01[0-9]{9}$/.test((data && data.phone) || '')) return cb && cb({ success: false, message: '휴대폰 번호를 정확히 입력해주세요. (예: 010-0000-0000)' });
      target.phone = data.phone;
      if (target.phoneChangeApproved) delete target.phoneChangeApproved;
      await saveUser(target);
      cb && cb({ success: true, phone: target.phone });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  // 번호 변경 요청 접수(고객센터) - 관리자가 승인해야만 실제 변경(account:set_phone) 가능해짐
  socket.on('account:request_phone_change', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      const target = userId ? await getUser(userId) : null;
      if (!target) return cb && cb({ success: false });
      const ref = db.ref('phoneChangeRequests').push();
      const request = { id: ref.key, userId: target.id, currentPhone: target.phone || '', status: 'pending', requestedAt: Date.now() };
      await ref.set(request);
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  // 관리자: 번호 변경 요청 목록 조회
  socket.on('admin:phone_requests:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const snap = await db.ref('phoneChangeRequests').once('value');
      const all = snap.val() || {};
      const users = await getAllUsers();
      const list = Object.values(all)
        .map(r => ({ ...r, nickname: (users[r.userId] && users[r.userId].nickname) || '(탈퇴한 사용자)' }))
        .sort((a, b) => (a.status === 'pending' ? 0 : 1) - (b.status === 'pending' ? 0 : 1) || (b.requestedAt || 0) - (a.requestedAt || 0));
      cb && cb({ success: true, requests: list });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  // 관리자: 번호 변경 요청 승인 -> 해당 유저가 새 번호를 1회 입력할 수 있게 열어줌
  socket.on('admin:phone_requests:approve', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const reqSnap = await db.ref(`phoneChangeRequests/${data && data.requestId}`).once('value');
      const request = reqSnap.val();
      if (!request) return cb && cb({ success: false });
      const target = await getUser(request.userId);
      if (target) {
        target.phoneChangeApproved = true;
        await saveUser(target);
        const sId = userToSocket[target.id];
        if (sId) io.to(sId).emit('account:phone_change_approved', {});
        else sendWebPush(target.id, { title: '전화번호 변경 승인', body: '요청하신 전화번호 변경이 승인되었습니다. 앱에서 새 번호를 입력해주세요.', type: 'phone_change_approved' });
      }
      await db.ref(`phoneChangeRequests/${request.id}`).update({ status: 'approved', resolvedAt: Date.now() });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 0-22: 관리자 - 구독 등급(골드/플래티넘) 수동 지급/회수 (테스트·CS 대응용, 결제 없이 즉시 반영)
  socket.on('admin:subscription:grant', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const targetId = data && data.userId;
      const tier = data && data.tier;
      const days = Number(data && data.days);
      if (!targetId || !SUBSCRIPTION_TIER_RANK[tier] || !days || days <= 0) {
        return cb && cb({ success: false, message: '잘못된 요청입니다.' });
      }
      const target = await getUser(targetId);
      if (!target) return cb && cb({ success: false, message: '유저를 찾을 수 없습니다.' });
      target.subscription = {
        tier,
        expiresAt: Date.now() + days * 24 * 60 * 60 * 1000,
        logoColorOn: (target.subscription && typeof target.subscription.logoColorOn === 'boolean') ? target.subscription.logoColorOn : true,
        badgeOn: (target.subscription && typeof target.subscription.badgeOn === 'boolean') ? target.subscription.badgeOn : true
      };
      // 0-54: 실구매와 동일한 흐름 - 365일(1년권) 관리자 지급은 매달 1일 자동 지급(monthlyBonus)으로 처리,
      // 그 외(14일권 등) 관리자 지급은 기존처럼 즉시 전액 지급
      const bonusPoints = tier === 'platinum' ? 3000 : 1000;
      if (days >= 365) {
        target.subscription.monthlyBonus = { amount: bonusPoints, lastGrantedMonth: null };
      } else {
        target.points = (target.points || 0) + bonusPoints;
      }
      await saveUser(target);
      console.log(`[관리자 구독 지급] ${requester.nickname}(이)가 ${target.nickname}에게 ${tier}(${days}일) + 쌀 ${bonusPoints} 수동 지급`);
      const sId = userToSocket[target.id];
      if (sId) io.to(sId).emit('points:updated', { points: target.points, subscription: target.subscription });
      broadcastUsers();
      cb && cb({ success: true, subscription: target.subscription, points: target.points });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });
  // 0-22: 관리자 - 구독 강제 해제
  socket.on('admin:subscription:revoke', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const targetId = data && data.userId;
      if (!targetId) return cb && cb({ success: false });
      const target = await getUser(targetId);
      if (!target) return cb && cb({ success: false, message: '유저를 찾을 수 없습니다.' });
      target.subscription = null;
      await saveUser(target);
      console.log(`[관리자 구독 해제] ${requester.nickname}(이)가 ${target.nickname}의 구독을 해제`);
      const sId = userToSocket[target.id];
      if (sId) io.to(sId).emit('points:updated', { points: target.points, subscription: null });
      broadcastUsers();
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 0-38: 관리자 구독관리 - 검색 없이도 우선순위 목록을 바로 보여줌
  // 우선순위: 1) 구독 중인데 곧 만료되는 유저(임박순) 2) 최근 접속한 유저 순
  socket.on('admin:subscription:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const allUsers = Object.values(await getAllUsers());
      const now = Date.now();
      const activeSubUsers = allUsers
        .filter(u => u.subscription && u.subscription.tier && u.subscription.expiresAt && u.subscription.expiresAt > now)
        .sort((a, b) => a.subscription.expiresAt - b.subscription.expiresAt);
      const activeIds = new Set(activeSubUsers.map(u => u.id));
      const recentUsers = allUsers
        .filter(u => !activeIds.has(u.id))
        .sort((a, b) => (b.lastSeen || 0) - (a.lastSeen || 0))
        .slice(0, 30);
      cb && cb({ success: true, users: [...activeSubUsers, ...recentUsers] });
    } catch (e) { console.error(e); cb && cb({ success: false, users: [] }); }
  });

  // 어뷰징 의심(동일 기기로 계정 2개 이상) 그룹 목록 - 관리자만
  socket.on('admin:abuse:list', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const allUsers = await getAllUsers();
      const byDevice = {};
      Object.values(allUsers).forEach(u => {
        if (!u.deviceId) return;
        if (!byDevice[u.deviceId]) byDevice[u.deviceId] = [];
        byDevice[u.deviceId].push(u);
      });
      const groups = Object.entries(byDevice)
        .filter(([, list]) => list.length >= 2)
        .map(([deviceId, list]) => ({
          deviceId,
          users: list
            .map(u => ({ id: u.id, nickname: u.nickname, createdAt: u.profileUpdatedAt || 0, isBanned: !!u.isBanned }))
            .sort((a, b) => a.createdAt - b.createdAt)
        }))
        .sort((a, b) => b.users.length - a.users.length);
      cb && cb({ success: true, groups });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 어뷰징 의심 목록에서 계정 정지 - 관리자만
  socket.on('admin:abuse:ban_user', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const target = await getUser(data && data.userId);
      if (!target) return cb && cb({ success: false });
      target.isBanned = true;
      target.bannedAt = Date.now();
      await saveUser(target);
      const sId = userToSocket[target.id];
      if (sId) { io.to(sId).emit('account:banned'); delete userToSocket[target.id]; }
      broadcastUsers();
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 0-57: 관리자 통계 대시보드 - 가입자/결제/신고처리율 요약
  socket.on('admin:stats:get', async (data, cb) => {
    try {
      const requester = await getUser(socketToUser[socket.id]);
      if (!requester || !isAdmin(requester)) return cb && cb({ success: false });
      const allUsers = await getAllUsers();
      const userList = Object.values(allUsers);
      const totalUsers = userList.length;
      const kstDateStr = (d) => new Date(d).toLocaleDateString('sv-SE', { timeZone: 'Asia/Seoul' });
      const todayStr = kstDateStr(Date.now());
      const dayBuckets = {};
      for (let i = 6; i >= 0; i--) {
        const d = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
        dayBuckets[kstDateStr(d)] = 0;
      }
      let todaySignups = 0;
      userList.forEach(u => {
        const joined = u.joinedAt || u.profileUpdatedAt;
        if (!joined) return;
        const dStr = kstDateStr(joined);
        if (dStr === todayStr) todaySignups++;
        if (Object.prototype.hasOwnProperty.call(dayBuckets, dStr)) dayBuckets[dStr]++;
      });
      const signupsByDay = Object.keys(dayBuckets).map(date => ({ date, count: dayBuckets[date] }));

      const purchaseSnap = await db.ref('purchaseHistory').once('value');
      const purchaseAll = purchaseSnap.val() || {};
      let totalPayments = 0, monthPayments = 0;
      const thisMonth = kstMonthStr(new Date());
      Object.values(purchaseAll).forEach(userPurchases => {
        Object.values(userPurchases || {}).forEach(p => {
          totalPayments++;
          if (kstMonthStr(new Date(p.at || 0)) === thisMonth) monthPayments++;
        });
      });

      const reportsSnap = await db.ref('reports').once('value');
      const reportsAll = Object.values(reportsSnap.val() || {});
      const totalReports = reportsAll.length;
      const resolvedReports = reportsAll.filter(r => r.status === 'resolved').length;
      const resolveRate = totalReports ? Math.round((resolvedReports / totalReports) * 100) : 0;

      cb && cb({
        success: true,
        totalUsers, todaySignups, signupsByDay,
        totalPayments, monthPayments,
        totalReports, resolvedReports, resolveRate
      });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 0-59: 신규가입자 온보딩 튜토리얼 - 시청/건너뛰기 모두 '봤음'으로 저장(다음 로그인부터 안 뜸)
  socket.on('user:onboarding_seen', async (data, cb) => {
    try {
      const userId = socketToUser[socket.id];
      if (!userId) return cb && cb({ success: false });
      const user = await getUser(userId);
      if (!user) return cb && cb({ success: false });
      user.onboardingSeen = true;
      await saveUser(user);
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
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

// 0-53: 0-51 이전에 탈퇴 처리된 유저들의 팔로우/팔로워/프로필좋아요 잔여참조를
// 서버 시작 시 딱 1회만 정리함(meta/staleFollowCleanupDone 플래그로 재실행 방지, 계속 남겨둬도 안전)
async function cleanupStaleFollowRefsOnce() {
  try {
    const marker = await db.ref('meta/staleFollowCleanupDone').once('value');
    if (marker.val()) return;
    const usersSnap = await db.ref('users').once('value');
    const allUsers = usersSnap.val() || {};
    const validIds = new Set(Object.keys(allUsers));
    let cleanedUserCount = 0, removedRefCount = 0;
    for (const uid of Object.keys(allUsers)) {
      const u = allUsers[uid] || {};
      const updates = {};
      ['followingIds', 'followerIds', 'profileLikedBy'].forEach(field => {
        if (Array.isArray(u[field])) {
          const filtered = u[field].filter(id => validIds.has(id));
          if (filtered.length !== u[field].length) {
            updates[field] = filtered;
            removedRefCount += (u[field].length - filtered.length);
          }
        }
      });
      if (Object.keys(updates).length) {
        await db.ref(`users/${uid}`).update(updates);
        cleanedUserCount++;
      }
    }
    await db.ref('meta/staleFollowCleanupDone').set(true);
    console.log(`✅ 0-53: 팔로우/좋아요 잔여참조 정리 완료 (유저 ${cleanedUserCount}명, 참조 ${removedRefCount}건 제거)`);
  } catch (e) {
    console.error('0-53 잔여참조 정리 실패:', e);
  }
}
cleanupStaleFollowRefsOnce();

// 0-53: 0-51 이전에 탈퇴 처리된 유저들의 팔로우/팔로워/프로필좋아요 잔여참조를
// 서버 시작 시 딱 1회만 정리함(meta/staleFollowCleanupDone 플래그로 재실행 방지, 계속 남겨둬도 안전)
async function cleanupStaleFollowRefsOnce() {
  try {
    const marker = await db.ref('meta/staleFollowCleanupDone').once('value');
    if (marker.val()) return;
    const usersSnap = await db.ref('users').once('value');
    const allUsers = usersSnap.val() || {};
    const validIds = new Set(Object.keys(allUsers));
    let cleanedUserCount = 0, removedRefCount = 0;
    for (const uid of Object.keys(allUsers)) {
      const u = allUsers[uid] || {};
      const updates = {};
      ['followingIds', 'followerIds', 'profileLikedBy'].forEach(field => {
        if (Array.isArray(u[field])) {
          const filtered = u[field].filter(id => validIds.has(id));
          if (filtered.length !== u[field].length) {
            updates[field] = filtered;
            removedRefCount += (u[field].length - filtered.length);
          }
        }
      });
      if (Object.keys(updates).length) {
        await db.ref(`users/${uid}`).update(updates);
        cleanedUserCount++;
      }
    }
    await db.ref('meta/staleFollowCleanupDone').set(true);
    console.log(`✅ 0-53: 팔로우/좋아요 잔여참조 정리 완료 (유저 ${cleanedUserCount}명, 참조 ${removedRefCount}건 제거)`);
  } catch (e) {
    console.error('0-53 잔여참조 정리 실패:', e);
  }
}
cleanupStaleFollowRefsOnce();

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => console.log(`말벗 서버 실행 중 (Firebase 연동): http://localhost:${PORT}`));
// 0-61: NSFW 모델을 서버 시작 시점에 미리 로드(예열)해둠.
// 기존엔 사용자가 사진을 처음 저장/전송하는 순간에 처음 로드되면서 그 요청이 응답 없이 오래 멈춰있는
// 것처럼 보이는 문제(프로필 저장 화면 멈춤, 채팅 사진 전송 안 됨)가 있었음 — 특히 Render 무료 플랜은
// 재시작(502 등)이 잦아 재시작 직후 첫 요청마다 이 문제가 반복됨.
loadNsfwModel()
  .then(() => console.log('✅ NSFW 이미지 검사 모델 예열 완료'))
  .catch(err => console.error('⚠️ NSFW 모델 예열 실패(사용자 요청 시점에 재시도됨):', err.message));