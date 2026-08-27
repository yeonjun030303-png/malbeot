const fs = require('fs');

async function main() {
  const prompt = `당신은 소셜/데이팅 성격의 채팅 앱 "말벗"의 프로덕트 매니저입니다.
앱 특징: 실시간 채팅(1:1, 오픈채팅, 단체방), 프로필 사진 다중등록, 취미기반 매칭, 구독제(골드/플래티넘, 포인트명 "쌀"), 신고기반 콘텐츠 모더레이션, 안드로이드 앱 전환 중, 아직 상용화 전 단계.

이런 유형의 앱에서 유저 리텐션과 재미를 높이는 데 효과적이었던 기능이나 UX 패턴을 3~5개 제안해주세요. 각 제안마다:
- 어떤 기능인지 한두 문장
- 왜 이 앱에 맞을지
- 구현 난이도(쉬움/보통/어려움) 대략적인 추정

과장하지 말고 실제로 채팅/소셜 앱들이 흔히 쓰는 검증된 패턴 위주로, 한국어로 작성해주세요.`;

  const apiKey = process.env.GEMINI_API_KEY;
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
    }
  );
  const data = await res.json();
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) {
    console.error('파싱 실패:', JSON.stringify(data));
    fs.writeFileSync('review-result.md', '⚠️ 이번 주 생성 실패 (API 응답 파싱 오류)');
    return;
  }
  fs.writeFileSync('review-result.md', text);
  console.log(text);
}

main().catch(err => {
  fs.writeFileSync('review-result.md', `⚠️ 스크립트 오류: ${err.message}`);
});