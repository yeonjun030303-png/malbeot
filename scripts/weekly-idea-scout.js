const fs = require('fs');

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function callGeminiModel(model, prompt, apiKey, maxRetries, baseDelayMs) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
      }
    );
    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;

    if (text) return text;

    const isRetryable = data?.error?.code === 503 || data?.error?.code === 429;
    console.error(`[${model}] Gemini 응답 실패 (시도 ${attempt}/${maxRetries}):`, JSON.stringify(data));

    if (isRetryable && attempt < maxRetries) {
      const delay = baseDelayMs * Math.pow(2, attempt - 1); // 지수 백오프
      console.log(`[${model}] ${delay / 1000}초 후 재시도...`);
      await sleep(delay);
      continue;
    }
    return null;
  }
  return null;
}

async function callGemini(prompt, apiKey) {
  // 1차: 주 모델(gemini-flash-latest)로 지수 백오프 재시도 (20s, 40s, 80s)
  let text = await callGeminiModel('gemini-flash-latest', prompt, apiKey, 4, 20000);
  if (text) return text;

  // 2차: 주 모델이 계속 과부하면 대체 모델로 한 번 더 시도
  console.log('주 모델(gemini-flash-latest) 실패 - 대체 모델(gemini-3.6-flash)로 재시도');
  text = await callGeminiModel('gemini-3.6-flash', prompt, apiKey, 2, 15000);
  return text;
}

async function main() {
  const prompt = `당신은 소셜/데이팅 성격의 채팅 앱 "말벗"의 프로덕트 매니저입니다.
앱 특징: 실시간 채팅(1:1, 오픈채팅, 단체방), 프로필 사진 다중등록, 취미기반 매칭, 구독제(골드/플래티넘, 포인트명 "쌀"), 신고기반 콘텐츠 모더레이션, 안드로이드 앱 전환 중, 아직 상용화 전 단계.

이런 유형의 앱에서 유저 리텐션과 재미를 높이는 데 효과적이었던 기능이나 UX 패턴을 3~5개 제안해주세요. 각 제안마다:
- 어떤 기능인지 한두 문장
- 왜 이 앱에 맞을지
- 구현 난이도(쉬움/보통/어려움) 대략적인 추정

과장하지 말고 실제로 채팅/소셜 앱들이 흔히 쓰는 검증된 패턴 위주로, 한국어로 작성해주세요.`;

  const apiKey = process.env.GEMINI_API_KEY;
  const text = await callGemini(prompt, apiKey);

  if (!text) {
    console.error('Gemini 응답을 최종적으로 받지 못함 (주/대체 모델 모두 재시도 소진)');
    fs.writeFileSync('review-result.md', '⚠️ 이번 주 생성 실패 (API 응답을 재시도 후에도 받지 못함)');
    return;
  }

  fs.writeFileSync('review-result.md', text);
  console.log(text);
}

main().catch(err => {
  fs.writeFileSync('review-result.md', `⚠️ 스크립트 오류: ${err.message}`);
});
