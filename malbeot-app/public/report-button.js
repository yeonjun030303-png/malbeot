// report-button.js
// 채팅 메시지 옆에 "신고" 버튼을 만들고 이 함수를 연결하세요.
// public 폴더에 두고 <script src="/report-button.js"></script>로 불러오면 됩니다.

async function reportMessage(chatRoomId, messageId, myUid, messageContent) {
  const reason = prompt("신고 사유를 입력해주세요 (예: 욕설, 스팸, 성희롱 등)");
  if (!reason) return;

  try {
    const res = await fetch('/api/reports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chatRoomId,
        messageId,
        reporterUid: myUid,
        reason,
        messageContent
      })
    });

    const data = await res.json();
    if (data.success) {
      alert('신고가 접수되었습니다. 확인 후 조치하겠습니다.');
    } else {
      alert('신고 접수에 실패했습니다: ' + (data.error || ''));
    }
  } catch (err) {
    console.error(err);
    alert('신고 접수 중 오류가 발생했습니다.');
  }
}

// 사용 예시 (채팅 메시지 렌더링 코드에 이런 식으로 버튼 추가):
// <button onclick="reportMessage('room123', 'msg456', currentUserUid, '메시지내용')">신고</button>