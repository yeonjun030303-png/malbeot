// 3단계: 총괄실장봇(chief-report.js)
// 1단계(team-summaries.json) + 2단계(committee-result.json)를 최종 취합해서
// chief-report-result.md 생성 -> 워크플로우에서 이슈등록 + 이메일 발송
// 0-84: 팀별 요약 표 추가
const fs = require('fs');

function main() {
  const teamSummaries = JSON.parse(fs.readFileSync('team-summaries.json', 'utf-8'));
  let committeeResult = { agendaCount: 0, teams: {}, note: null };
  if (fs.existsSync('committee-result.json')) {
    committeeResult = JSON.parse(fs.readFileSync('committee-result.json', 'utf-8'));
  }

  const lines = [];
  lines.push('## 🏢 주간 총괄 리포트 (총괄실장)');
  lines.push('');

  const teamEntries = Object.entries(teamSummaries);
  const totalIssues = teamEntries.reduce((sum, [, v]) => sum + (v.issueCount || 0), 0);
  const activeTeams = teamEntries.filter(([, v]) => v.issueCount > 0);

  const immediateTeams = [];
  const normalTeams = [];
  for (const [team, v] of Object.entries(committeeResult.teams || {})) {
    if (v.opposeCount > v.approveCount) {
      immediateTeams.push(team);
    } else {
      normalTeams.push(team);
    }
  }

  lines.push('### 📊 요약');
  lines.push(`- 전체 이슈 총 개수: ${totalIssues}건`);
  lines.push(`- 이슈가 있었던 팀 수: ${activeTeams.length}개`);
  lines.push(`- 위원회 심의 안건 수: ${committeeResult.agendaCount || 0}건`);
  lines.push(`- ⚠️ 즉시처리 필요(위원회 반대 우세) 팀 수: ${immediateTeams.length}개`);
  lines.push('');

  if (committeeResult.note) {
    lines.push(committeeResult.note);
    lines.push('');
  }

  if (activeTeams.length > 0) {
    lines.push('### 📋 팀별 요약 표');
    lines.push('| 팀 | 이슈 수 | 찬성:반대 | 등급 |');
    lines.push('|---|---|---|---|');
    for (const [team, v] of activeTeams) {
      const cv = committeeResult.teams && committeeResult.teams[team];
      const grade = !cv ? '심의없음' : (cv.opposeCount > cv.approveCount ? '🚨위험' : '✅정상');
      const votes = cv ? `${cv.approveCount}:${cv.opposeCount}` : '-';
      lines.push(`| ${team} | ${v.issueCount}건 | ${votes} | ${grade} |`);
    }
    lines.push('');
  }

  if (immediateTeams.length > 0) {
    lines.push('### 🚨 위험등급 상 - 즉시처리 필요');
    for (const team of immediateTeams) {
      const v = committeeResult.teams[team];
      lines.push(`- **${team}** (찬성 ${v.approveCount} : 반대 ${v.opposeCount}) - ${v.recommendation}`);
    }
    lines.push('');
  }

  if (normalTeams.length > 0) {
    lines.push('### ✅ 위험등급 하 - 정상 진행');
    for (const team of normalTeams) {
      const v = committeeResult.teams[team];
      lines.push(`- **${team}** (찬성 ${v.approveCount} : 반대 ${v.opposeCount}) - ${v.recommendation}`);
    }
    lines.push('');
  }

  lines.push('### 📋 팀별 상세 (이번 주 이슈 있었던 팀만)');
  for (const [team, v] of activeTeams) {
    lines.push(`#### ${team} (이슈 ${v.issueCount}건)`);
    lines.push(v.summary);
    const cv = committeeResult.teams && committeeResult.teams[team];
    if (cv) {
      lines.push('');
      lines.push(`**위원회 의견** (찬성 ${cv.approveCount} : 반대 ${cv.opposeCount})`);
      for (const op of cv.opinions) {
        lines.push(`- [${op.verdict}] ${op.persona}: ${op.reason}`);
      }
    }
    lines.push('');
  }

  fs.writeFileSync('chief-report-result.md', lines.join('\n'));
  console.log('chief-report-result.md 저장 완료');
}

main();
