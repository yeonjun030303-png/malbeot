// reports.js
// -----------------------------------------------------------
// server.js에 아래 두 줄을 추가하세요 (firebase-admin 초기화 코드보다 아래에):
//
//   const reportsRouter = require('./reports');
//   app.use('/api/reports', reportsRouter);
// -----------------------------------------------------------

const express = require('express');
const admin = require('firebase-admin'); // server.js에서 이미 초기화되어 있어야 합니다
const router = express.Router();

// ⚠️ 임시 관리자 인증입니다. .env에 ADMIN_SECRET_KEY=아무렇게나긴랜덤문자열 을 추가하고
// 이 키를 아는 사람만 관리자 API를 호출할 수 있게 했습니다.
// 나중에 여러분의 실제 로그인/세션 시스템이 있다면 그걸로 교체하는 게 더 안전합니다.
function requireAdmin(req, res, next) {
  const adminKey = req.headers['x-admin-key'];
  if (!process.env.ADMIN_SECRET_KEY || adminKey !== process.env.ADMIN_SECRET_KEY) {
    return res.status(403).json({ error: '관리자 권한이 필요합니다.' });
  }
  next();
}

// 1) 신고 접수 - 클라이언트(사용자)가 호출
router.post('/', async (req, res) => {
  try {
    const { chatRoomId, messageId, reporterUid, reason, messageContent } = req.body;

    if (!chatRoomId || !reporterUid || !reason) {
      return res.status(400).json({ error: '필수 항목이 누락되었습니다.' });
    }

    const db = admin.database();
    const newReportRef = db.ref('reports').push();
    await newReportRef.set({
      chatRoomId,
      messageId: messageId || null,
      reporterUid,
      reason,
      messageContent: messageContent || null,
      status: 'pending', // pending | deleted | dismissed
      createdAt: admin.database.ServerValue.TIMESTAMP
    });

    res.json({ success: true, reportId: newReportRef.key });
  } catch (err) {
    console.error('[신고 접수 오류]', err);
    res.status(500).json({ error: '신고 접수 중 오류가 발생했습니다.' });
  }
});

// 2) 신고 목록 조회 - 관리자만
router.get('/admin/list', requireAdmin, async (req, res) => {
  try {
    const db = admin.database();
    const snapshot = await db.ref('reports')
      .orderByChild('status')
      .equalTo('pending')
      .once('value');

    const reports = [];
    snapshot.forEach((child) => {
      reports.push({ id: child.key, ...child.val() });
    });

    res.json({ reports });
  } catch (err) {
    console.error('[신고 목록 조회 오류]', err);
    res.status(500).json({ error: '조회 중 오류가 발생했습니다.' });
  }
});

// 3) 신고 처리 (메시지 삭제 또는 기각) - 관리자만
router.post('/admin/resolve/:reportId', requireAdmin, async (req, res) => {
  try {
    const { reportId } = req.params;
    const { action } = req.body; // 'delete' | 'dismiss'

    const db = admin.database();
    const reportRef = db.ref('reports/' + reportId);
    const snapshot = await reportRef.once('value');
    const report = snapshot.val();

    if (!report) {
      return res.status(404).json({ error: '신고 내역을 찾을 수 없습니다.' });
    }

    if (action === 'delete' && report.chatRoomId && report.messageId) {
      // 실제 DB 최상위 노드명이 'chats'로 확인되어 반영했습니다.
      // ⚠️ 다만 chats 아래의 세부 구조(messages 단계가 있는지 등)는 아직 미확인이라
      // 'chats' 하위 구조를 펼쳐서 확인해주시면 정확한 경로로 다시 수정해드릴게요.
      await db.ref(`chats/${report.chatRoomId}/messages/${report.messageId}`).remove();
    }

    await reportRef.update({ status: action === 'delete' ? 'deleted' : 'dismissed' });

    res.json({ success: true });
  } catch (err) {
    console.error('[신고 처리 오류]', err);
    res.status(500).json({ error: '처리 중 오류가 발생했습니다.' });
  }
});

module.exports = router;