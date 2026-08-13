path = "server.js"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()

old = '''      const snap = await db.ref('reports').once('value');
      const all = snap.val() || {};
      // 같은 대상(type::targetId)에 미처리 신고가 몇 건 쌓였는지 먼저 집계
      const pendingCountByTarget = {};
      Object.values(all).forEach(r => {
        if (r.status !== 'pending') return;
        const key = `${r.type}::${r.targetId}`;
        pendingCountByTarget[key] = (pendingCountByTarget[key] || 0) + 1;
      });'''
assert old in s, "admin:reports:list 집계 로직을 찾을 수 없습니다"

new = '''      const snap = await db.ref('reports').once('value');
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
      });'''

s = s.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(s)

print("✅ 0-29 패치 적용 완료: 신고 긴급표시 기준을 신고 건수 -> 서로 다른 신고자 수로 변경")