const fs = require('fs');
const path = require('path');
const { callGemini } = require('./gemini-helper');

async function main() {
  const prompt = `당신은 스타트업 블루오션 발굴 전문가입니다. "말벗"(데이팅/소셜 채팅앱)을 운영하는 C&S STUDIO 신개발팀 소속으로, 바이브코딩(AI 코딩 도구 활용)으로 실제 구현 가능하면서 시장 규모가 크고 경쟁사가 거의 없는 앱 아이디어를 20개 제안하세요.

각 아이디어마다 다음을 포함하세요:
1. 아이디어 이름과 한 줄 설명
2. 예상 시장 규모(정성 평가와 이유)
3. 경쟁 서비스 벤치마킹(있으면 이름·특징, 없으면 "없음")
4. 기존 서비스 대비 약점과 보완 방안
5. 바이브코딩으로 즉시 착수 가능한 MVP 핵심 기능 3~5개

마크다운으로, 아이디어마다 "### " 제목을 붙여 작성하세요.`;

  const result = await callGemini(prompt);
  const output = `# 블루오션기획관 주간 리포트\n생성일: ${new Date().toISOString().slice(0, 10)}\n\n${result}`;
  fs.writeFileSync(path.join(__dirname, '..', 'blue-ocean-report.md'), output, 'utf8');
  console.log('blue-ocean-report.md 생성 완료');
}

main().catch(e => { console.error(e); process.exit(1); });
