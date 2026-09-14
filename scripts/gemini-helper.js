async function callGemini(prompt, primaryModel = 'gemini-flash-latest', fallbackModel = 'gemini-3.6-flash') {
  const key = process.env.GEMINI_API_KEY;

  async function tryModel(model, retries, waits) {
    for (let i = 0; i < retries; i++) {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
        }
      );
      if (res.status === 503 || res.status === 429) {
        console.log(`${model} 과부하(${res.status}), ${waits[i] || 15}초 대기 후 재시도 (${i + 1}/${retries})`);
        await new Promise(r => setTimeout(r, (waits[i] || 15) * 1000));
        continue;
      }
      if (!res.ok) throw new Error(`Gemini API 오류 ${res.status}: ${await res.text()}`);
      const data = await res.json();
      return data.candidates[0].content.parts[0].text;
    }
    throw new Error(`${model} 재시도 소진`);
  }

  try {
    return await tryModel(primaryModel, 4, [20, 40, 80]);
  } catch (e) {
    console.log('주 모델 실패, 대체 모델로 전환:', e.message);
    return await tryModel(fallbackModel, 2, [15]);
  }
}

module.exports = { callGemini };
