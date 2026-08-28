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
  console.log('주 모델(gemini-flash-latest) 실패 - 대체 모델(gemini-2.5-flash)로 재시도');
  text = await callGeminiModel('gemini-2.5-flash', prompt, apiKey, 2, 15000);
  return text;
}

async function main() {
  const prompt = `당신은 소규모 스타트업 전담 그로스 마케터입니다. "말벗"이라는 채팅/소셜 앱(1인 개발 수준, 무료 인프라로 운영, 아직 유저가 많지 않은 초기 단계, 안드로이드 출시 준비 중)의 마케팅을 맡았습니다.

이번 주 실행 가능한 마케팅 액션 아이디어를 3개만 제안해주세요. 조건:
- 예산이 거의 없다는 전제 (무료/저비용 채널 위주: 인스타그램, 커뮤니티, 입소문 등)
- 각 아이디어에 "왜 지금 이게 효과적일지"와 "구체적으로 뭘 올리거나 해야 하는지" 포함
- 과장된 baz-word 없이 실무적으로, 한국어로

마지막에 이번 주 인스타그램에 올리면 좋을 게시물 소재 1개도 짧게 제안해주세요(캡션 초안 포함).`;

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
