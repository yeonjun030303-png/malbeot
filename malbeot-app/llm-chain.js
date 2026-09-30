// 무료 AI 폴백 체인: 앞 단계가 한도 초과/오류면 즉시 다음 단계로 넘어감.
// 키(환경변수)가 없는 제공자는 자동으로 건너뜀. 전부 OpenAI 호환 chat/completions 형식.
// 순서는 LLM_ORDER 환경변수(예: "groq,gemini")로, 모델은 <NAME>_MODELS(쉼표 구분)로 덮어쓸 수 있음.
'use strict';

function list(envName, def) {
  const v = process.env[envName];
  return v ? v.split(',').map(s => s.trim()).filter(Boolean) : def;
}

const PROVIDERS = {
  gemini: {
    key: () => process.env.GEMINI_API_KEY,
    url: () => 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    models: () => list('GEMINI_MODELS', ['gemini-2.5-flash', 'gemini-2.5-flash-lite'])
  },
  groq: {
    key: () => process.env.GROQ_API_KEY,
    url: () => 'https://api.groq.com/openai/v1/chat/completions',
    models: () => list('GROQ_MODELS', ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant'])
  },
  cerebras: {
    key: () => process.env.CEREBRAS_API_KEY,
    url: () => 'https://api.cerebras.ai/v1/chat/completions',
    models: () => list('CEREBRAS_MODELS', ['gpt-oss-120b', 'llama3.1-8b'])
  },
  cloudflare: {
    key: () => (process.env.CF_API_TOKEN && process.env.CF_ACCOUNT_ID) ? process.env.CF_API_TOKEN : '',
    url: () => 'https://api.cloudflare.com/client/v4/accounts/' + process.env.CF_ACCOUNT_ID + '/ai/v1/chat/completions',
    models: () => list('CLOUDFLARE_MODELS', ['@cf/meta/llama-3.3-70b-instruct-fp8-fast', '@cf/meta/llama-3.1-8b-instruct'])
  },
  openrouter: {
    key: () => process.env.OPENROUTER_API_KEY,
    url: () => 'https://openrouter.ai/api/v1/chat/completions',
    models: () => list('OPENROUTER_MODELS', ['meta-llama/llama-3.3-70b-instruct:free', 'openai/gpt-oss-20b:free'])
  },
  zai: {
    key: () => process.env.ZAI_API_KEY,
    url: () => 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    models: () => list('ZAI_MODELS', ['glm-4.7-flash'])
  }
};const DEFAULT_ORDER = ['gemini', 'groq', 'cerebras', 'cloudflare', 'openrouter', 'zai'];

// 쉬는 중인 제공자/모델 기록 (메모리, 프로세스 재시작하면 초기화)
const providerPause = {}; // name -> until(ms)
const modelPause = {};    // name|model -> until(ms)

function order() {
  return list('LLM_ORDER', DEFAULT_ORDER).filter(n => PROVIDERS[n]);
}
function configured() {
  return order().filter(n => !!PROVIDERS[n].key());
}

function cleanText(t) {
  const lt = String.fromCharCode(60);
  const re = new RegExp(lt + 'think>[\\s\\S]*?' + lt + '/think>', 'gi');
  return String(t || '').replace(re, '').trim();
}

async function callOne(name, model, body, timeoutMs) {
  const p = PROVIDERS[name];
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const payload = { model, messages: body.messages, max_tokens: body.maxTokens, temperature: body.temperature };
    if (name === 'gemini' && /2\.5-flash/.test(model)) payload.reasoning_effort = 'none'; // 생각 토큰이 답변을 잡아먹지 않게
    const res = await fetch(p.url(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${p.key()}` },
      body: JSON.stringify(payload),
      signal: ctrl.signal
    });
    if (!res.ok) {
      let detail = '';
      try { detail = (await res.text()).slice(0, 200); } catch (e) {}
      const err = new Error(`HTTP ${res.status} ${detail}`);
      err.status = res.status;
      err.retryAfter = parseInt(res.headers.get('retry-after') || '0', 10) || 0;
      throw err;
    }
    const data = await res.json();
    const text = cleanText(data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content);
    if (!text) { const err = new Error('빈 응답'); err.status = 0; throw err; }
    return text;
  } catch (e) {
    if (e.name === 'AbortError') { const err = new Error('시간 초과'); err.status = 0; throw err; }
    throw e;
  } finally { clearTimeout(timer); }
}

/**
 * chat({ system, messages, maxTokens, temperature, validate })
 * - system: 시스템 프롬프트 문자열
 * - messages: [{role:'user'|'assistant', content}]
 * - validate(text): 선택. false를 돌려주면 그 응답은 버리고 다음 모델로 넘어감(JSON 검사 등)
 * 성공: { text, provider, model, attempts }   전부 실패: throw (err.attempts에 시도 기록)
 */
async function chat(opts) {
  const timeoutMs = parseInt(process.env.LLM_TIMEOUT_MS || '20000', 10);
  const body = {
    messages: [{ role: 'system', content: opts.system || '' }].concat(opts.messages || []),
    maxTokens: opts.maxTokens || 400,
    temperature: opts.temperature == null ? 0.9 : opts.temperature
  };
  const attempts = [];
  const now = () => Date.now();

  for (const name of order()) {
    const p = PROVIDERS[name];
    if (!p.key()) continue;                                   // 키 없으면 건너뜀
    if ((providerPause[name] || 0) > now()) { attempts.push({ provider: name, ok: false, err: '쉬는 중' }); continue; }
    for (const model of p.models()) {
      if ((modelPause[name + '|' + model] || 0) > now()) continue;
      try {
        const text = await callOne(name, model, body, timeoutMs);
        if (opts.validate && !opts.validate(text)) {
          attempts.push({ provider: name, model, ok: false, err: '검증 실패' });
          continue;
        }
        attempts.push({ provider: name, model, ok: true });
        return { text, provider: name, model, attempts };
      } catch (e) {
        const st = e.status || 0;
        attempts.push({ provider: name, model, ok: false, status: st, err: String(e.message).slice(0, 160) });
        if (st === 429) { providerPause[name] = now() + Math.min(Math.max((e.retryAfter || 60) * 1000, 30000), 600000); break; }   // 한도 초과: 이 제공자 잠시 쉬고 다음 제공자로
        if (st === 401 || st === 403) { providerPause[name] = now() + 30 * 60 * 1000; break; }                                   // 키 문제: 30분 쉼
        if (st === 400 || st === 404) { modelPause[name + '|' + model] = now() + 30 * 60 * 1000; continue; }                     // 모델 이름 문제: 같은 제공자의 다음 모델
        if (st >= 500 || st === 0) { modelPause[name + '|' + model] = now() + 30 * 1000; continue; }                             // 서버 오류/시간 초과: 잠깐 쉬고 다음
      }
    }
  }
  const err = new Error('모든 AI 제공자 실패');
  err.attempts = attempts;
  throw err;
}

module.exports = { chat, configured, order };
