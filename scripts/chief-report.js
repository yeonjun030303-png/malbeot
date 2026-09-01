// 3단계: 총괄실장봇 - 팀장취합(team-summaries.json) + 결정위원회(committee-result.json) 결과를
// 최종취합해서 GitHub 이슈등록 + 이메일발송용 리포트 파일(chief-result.md)로 정리
const fs = require('fs');

function loadJson(path, fallback) {
  try {
    return JSON.parse(fs.readFileSync(path, 'utf-8'));
  } catch (e) {
    console.log(`${path} 읽기 실패 - 기본값 사용: ${e.message}`);
    return fallback;
  }
}

function main() {
  const teamSummaries = loadJson('team-summaries.json', {});
  const committeeResult = loadJson('committee-result.json', { agendaCount: 0, teams: {} });

  const teamNames = Object.keys(teamSummaries);
  const agendaTeams = teamNames.filter(t => (teamSummaries[t].issueCount || 0) > 0);
  const totalIssues = teamNames.reduce((s, t) => s + (teamSummaries[t].issueCount || 0), 0);

  const risk = { '위험': [], '주의': [], '안정': [] };
  let urgentCount = 0;

  for (const team of agendaTeams) {
    const c = committeeResult.teams && committeeResult.teams[team];
    if (!c) {
      risk['안정'].push(team);
      continue;
    }
    if (c.opposeCount > c.approveCount) {
      risk['위험'].push(team);
      urgentCount++;
    } else if (c.opposeCount === c.approveCount) {
      risk['주의'].push(team);
    } else {
      risk['안정'].push(team);
    }
  }

  const lines = [];
  lines.push('## 📋 총괄실장 주간 보고');
  lines.push('');
  lines.push(`- 전체 이슈 총 개수: ${totalIssues}건`);
  lines.push(`- 위원회 안건 상정 팀 수: ${agendaTeams.length}개`);
  lines.push(`- 즉시처리 필요(위원회 반대 다수) 건수: ${urgentCount}건`);
  lines.push('');
  lines.push('### 위험등급별 항목');
  lines.push(`- 🔴 위험(위원회 반대 다수): ${risk['위험'].join(', ') || '없음'}`);
  lines.push(`- 🟡 주의(찬반 동수): ${risk['주의'].join(', ') || '없음'}`);
  lines.push(`- 🟢 안정(찬성 다수 또는 안건 없음): ${risk['안정'].join(', ') || '없음'}`);
  lines.push('');

  if (agendaTeams.length === 0) {
    lines.push('이번 주 이슈가 등록된 팀이 없어 위원회 안건도 없습니다.');
  } else {
    lines.push('### 팀별 상세');
    for (const team of agendaTeams) {
      const t = teamSummaries[team];
      lines.push('');
      lines.push(`#### ${team} (이슈 ${t.issueCount}건)`);
      lines.push(t.summary || '(팀장 코멘트 없음)');
      const c = committeeResult.teams && committeeResult.teams[team];
      if (c) {
        lines.push('');
        lines.push(`- 위원회 표결: 찬성 ${c.approveCount} : 반대 ${c.opposeCount}`);
        lines.push(`- 위원회 권고: ${c.recommendation}`);
        lines.push('- 위원별 의견:');
        for (const o of c.opinions) {
          lines.push(`  - ${o.persona}: ${o.verdict} - ${o.reason}`);
        }
      } else {
        lines.push('');
        lines.push('- 위원회 표결 결과 없음(위원회 단계 오류 또는 응답 실패로 추정)');
      }
    }
  }

  fs.writeFileSync('chief-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main();
