const fs = require('fs');
const path = require('path');
const { callGemini } = require('./gemini-helper');

async function main() {
  const prompt = `당신은 시장 조사 전문가입니다. 데이팅/소셜 채팅, 커뮤니티, 자기계발 등 다양한 앱 카테고리에서 사람들이 최근 자주 토로하는 불편함과 미충족 니즈를 20가지 정리하세요.

참고: 실시간 웹 크롤링 없이, 일반적으로 알려진 사용자 불만 패턴과 트렌드 지식을 바탕으로 작성하세요.

각 항목마다:
1. 불편함/니즈 요약
2. 어떤 유형의 사용자가 겪는지
3. 이를 해결하면 어떤 서비스/기능 아이디어로 이어질 수 있는지

마크다운으로 "### " 항목 제목을 붙여 작성하세요.`;

  const result = await callGemini(prompt);
  const output = `# 불편함조사관 주간 리포트\n생성일: ${new Date().toISOString().slice(0, 10)}\n\n${result}`;
  fs.writeFileSync(path.join(__dirname, '..', 'pain-point-report.md'), output, 'utf8');
  console.log('pain-point-report.md 생성 완료');
}

main().catch(e => { console.error(e); process.exit(1); });
