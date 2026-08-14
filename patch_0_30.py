# 0-30: 신고 처리 결과를 신고자에게 알림

path_server = "server.js"
with open(path_server, "r", encoding="utf-8") as f:
    s = f.read()

old = '''      await db.ref(`reports/${reportId}`).update({ status: 'resolved', resolveAction: action, resolvedAt: Date.now() });
      cb && cb({ success: true });
    } catch (e) { console.error(e); cb && cb({ success: false }); }
  });

  // 전체 채팅방 목록(서비스 내 모든 방) - 관리자만'''
assert old in s, "admin:reports:resolve 마무리부를 찾을 수 없습니다"

new = '''      await db.ref(`reports/${reportId}`).update({ status: 'resolved', resolveAction: action, resolvedAt: Date.now() });

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

  // 전체 채팅방 목록(서비스 내 모든 방) - 관리자만'''

s = s.replace(old, new)

with open(path_server, "w", encoding="utf-8") as f:
    f.write(s)

print("✅ [1/2] server.js — 신고 처리 결과를 신고자에게 알림 발송하도록 추가 완료")

# 클라이언트: 결과 알림 수신 시 미니알림 표시
path_html = "public/index.html"
with open(path_html, "r", encoding="utf-8") as f:
    h = f.read()

old_client = '''socket.on('account:warned', (data)=>{
  if (!currentUser) return;
  showWarningModal(data && data.message);
});'''
assert old_client in h, "account:warned 리스너를 찾을 수 없습니다"

new_client = '''socket.on('account:warned', (data)=>{
  if (!currentUser) return;
  showWarningModal(data && data.message);
});
// 0-30: 내가 넣은 신고가 처리되면 결과를 미니알림으로 알려줌
socket.on('report:resolved_notify', (data)=>{
  if (!currentUser) return;
  showMiniAlert((data && data.message) || '신고하신 내용의 처리가 완료되었습니다.', [{label:'확인', primary:true}]);
});'''

h = h.replace(old_client, new_client)

with open(path_html, "w", encoding="utf-8") as f:
    f.write(h)

print("✅ [2/2] public/index.html — 신고 처리 결과 미니알림 수신 처리 추가 완료")
print("0-30 패치 전체 완료")