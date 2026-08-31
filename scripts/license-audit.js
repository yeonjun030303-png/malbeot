// 라이선스·저작권 담당 봇 (행정법무팀) - 매월 1일 17:00
// npm 의존성 패키지들의 라이선스를 점검, GPL 계열 등 상업적 재배포에 주의가 필요한 라이선스를 강조 표시
// license-checker 패키지를 devDependency 없이 npx로 즉시 실행

const { execSync } = require('child_process');
const fs = require('fs');

const RISKY_LICENSE_KEYWORDS = ['GPL', 'AGPL', 'SSPL', 'CC-BY-NC'];

function isRisky(license) {
  if (!license) return false;
  return RISKY_LICENSE_KEYWORDS.some(k => license.toUpperCase().includes(k));
}

async function main() {
  let raw;
  try {
    raw = execSync('npx --yes license-checker --json', { maxBuffer: 1024 * 1024 * 20 }).toString();
  } catch (e) {
    console.error('license-checker 실행 실패:', e.message);
    fs.writeFileSync('license-result.md', '⚠️ 라이선스 점검 실패 (license-checker 실행 오류)');
    process.exit(1);
  }

  const data = JSON.parse(raw);
  const entries = Object.keys(data).map(key => ({ key, ...data[key] }));
  const risky = entries.filter(e => isRisky(e.licenses));

  const lines = [];
  lines.push('## 📄 라이선스·저작권 점검');
  lines.push('');
  lines.push(`- 전체 의존성 패키지: ${entries.length}개`);
  lines.push(`- 주의 필요 라이선스(GPL/AGPL/SSPL/CC-BY-NC 계열): ${risky.length}개`);
  lines.push('');

  if (risky.length === 0) {
    lines.push('이번 점검에서 상업적 재배포 시 주의가 필요한 라이선스는 발견되지 않았습니다.');
    console.log('주의 라이선스 없음 - 리포트 생략');
    // 이상 없을 때도 월간 점검이므로 결과 파일은 남기되, 이슈/이메일 여부는 워크플로우에서 판단
    fs.writeFileSync('license-result.md', '');
    return;
  }

  lines.push('### ⚠️ 확인이 필요한 패키지');
  risky.forEach(e => {
    lines.push(`- ${e.key}: ${e.licenses}`);
  });
  lines.push('');
  lines.push('해당 패키지들이 실제로 앱 배포/재배포 방식과 충돌하는지 라이선스 원문을 직접 확인해 주세요. (본 리포트는 참고용이며 정식 법률 자문이 아닙니다.)');

  fs.writeFileSync('license-result.md', lines.join('\n'));
  console.log(lines.join('\n'));
}

main();
