// 무료 AI 폴백 체인: 앞 단계가 한도 초과/오류면 즉시 다음 단계로 넘어감.
// 키(환경변수)가 없는 제공자는 자동으로 건너뜀. 전부 OpenAI 호환 chat/completions 형식.
// 순서는 LLM_ORDER 환경변수(예: groq,gemini)로, 모델은 이름_MODELS(쉼표 구분)로 덮어쓸 수 있음.
// 모델 이름이 없어졌거나 막혔으면(400/404) 제공자의 모델 목록을 조회해서 쓸 수 있는 모델을 자동으로 찾음.
'use strict';

function list(envName, def) {
  const v = process.env[envName];
  return v ? v.split(',').map(s => s.trim()).filter(Boolean) : def;
}
const bearer = k => ({ 'Authorization': 'Bearer ' + k });

const PROVIDERS = {
  gemini: {
    key: () => process.env.GEMINI_API_KEY,
    url: () => 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    models: () => list('GEMINI_MODELS', ['gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-2.5-flash', 'gemini-2.5-flash-lite']),
    listUrl: () => 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=200',
    listHeaders: k => ({ 'x-goog-api-key': k }),
    parseList: j => (j.models || []).filter(m => !m.supportedGenerationMethods || m.supportedGenerationMethods.indexOf('generateContent') >= 0).map(m => String(m.name).replace(/^models\//, ''))
  },
  groq: {
    key: () => process.env.GROQ_API_KEY,
    url: () => 'https://api.groq.com/openai/v1/chat/completions',
    models: () => list('GROQ_MODELS', ['llama-3.3-70b-versatile', 'openai/gpt-oss-20b', 'llama-3.1-8b-instant']),
    listUrl: () => 'https://api.groq.com/openai/v1/models',
    listHeaders: bearer,
    parseList: j => (j.data || []).filter(m => m.active !== false).map(m => m.id)
  },
  cerebras: {
    key: () => process.env.CEREBRAS_API_KEY,
    url: () => 'https://api.cerebras.ai/v1/chat/completions',
    models: () => list('CEREBRAS_MODELS', ['gpt-oss-120b', 'llama3.1-8b']),
    listUrl: () => 'https://api.cerebras.ai/v1/models',
    listHeaders: bearer,
    parseList: j => (j.data || []).map(m => m.id)
  },
  cloudflare: {
    key: () => (process.env.CF_API_TOKEN && process.env.CF_ACCOUNT_ID) ? process.env.CF_API_TOKEN : '',
    url: () => 'https://api.cloudflare.com/client/v4/accounts/' + process.env.CF_ACCOUNT_ID + '/ai/v1/chat/completions',
    models: () => list('CLOUDFLARE_MODELS', ['@cf/meta/llama-3.3-70b-instruct-fp8-fast', '@cf/meta/llama-3.1-8b-instruct'])
  },
  openrouter: {
    key: () => process.env.OPENROUTER_API_KEY,
    url: () => 'https://openrouter.ai/api/v1/chat/completions',
    models: () => list('OPENROUTER_MODELS', ['meta-llama/llama-3.3-70b-instruct:free', 'openai/gpt-oss-20b:free']),
    listUrl: () => 'https://openrouter.ai/api/v1/models',
    listHeaders: bearer,
    parseList: j => (j.data || []).map(m => m.id)
  },
  zai: {
    key: () => process.env.ZAI_API_KEY,
    url: () => 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    models: () => list('ZAI_MODELS', ['glm-4.7-flash'])
  }
};
const DEFAULT_ORDER = ['gemini', 'groq', 'cerebras', 'cloudflare', 'openrouter', 'zai'];

// 모델 목록에서 쓸 만한 것 고르기
function versionOf(id) { const m = String(id).match(/(\d+(?:\.\d+)?)/); return m ? parseFloat(m[1]) : 0; }
function pref(ids, regs) {
  const out = [];
  regs.forEach(re => ids.forEach(id => { if (re.test(id) && out.indexOf(id) < 0) out.push(id); }));
  ids.forEach(id => { if (out.indexOf(id) < 0) out.push(id); });
  return out;
}
const RANK = {
  gemini: ids => ids
    .filter(id => /^gemini-/.test(id) && /flash/.test(id) && !/(image|tts|embed|live|audio|vision|robotics|computer|thinking|exp|learnlm|nano|banana|customtools|pro)/.test(id))
    .map(id => ({ id, s: versionOf(id) * 100 - (/preview/.test(id) ? 1000 : 0) + (/lite/.test(id) ? 5 : 0) + (/latest/.test(id) ? 500 : 0) }))
    .sort((a, b) => b.s - a.s).map(x => x.id).slice(0, 4),
  groq: ids => pref(ids.filter(id => !/(whisper|guard|tts|playai|orpheus|embed|safeguard|distil|compound)/.test(id)),
    [/llama-3\.3-70b/, /gpt-oss-120b/, /gpt-oss-20b/, /llama-4/, /qwen/, /kimi/, /llama-3\.1-8b/]).slice(0, 4),
  cerebras: ids => pref(ids.filter(id => !/embed/.test(id)), [/gpt-oss-120b/, /llama-3\.3-70b/, /qwen/, /llama/]).slice(0, 3),
  openrouter: ids => pref(ids.filter(id => /:free$/.test(id) && !/(embed|vision|image|audio|moderation|vl)/.test(id)),
    [/llama-3\.3-70b/, /gpt-oss/, /qwen/, /gemma/, /mistral/, /deepseek/]).slice(0, 4)
};

const providerPause = {}; // name -> until(ms)
const modelPause = {};    // name|model -> { until, why }
const preferred = {};     // name -> 자동으로 찾아서 성공한 모델
const noReasoning = {};   // name|model -> reasoning_effort를 모르는 모델
const discovered = {};    // name -> { at, ids }
const discoverPause = {}; // name -> until(ms)

function order() { return list('LLM_ORDER', DEFAULT_ORDER).filter(n => PROVIDERS[n]); }
function configured() { return order().filter(n => !!PROVIDERS[n].key()); }
function cleanText(t) {
  const lt = String.fromCharCode(60);
  const re = new RegExp(lt + 'think>[\\s\\S]*?' + lt + '/think>', 'gi');
  return String(t || '').replace(re, '').trim();
}

async function fetchWithTimeout(url, init, timeoutMs) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try { return await fetch(url, Object.assign({}, init, { signal: ctrl.signal })); }
  finally { clearTimeout(timer); }
}

async function callOne(name, model, body, timeoutMs) {
  const p = PROVIDERS[name];
  const payload = { model, messages: body.messages, max_tokens: body.maxTokens, temperature: body.temperature };
  if (name === 'gemini') { payload.max_tokens = Math.max(body.maxTokens, 800); payload.reasoning_effort = 'none'; }   // 생각 토큰이 답변을 잡아먹지 않게
  if ((name === 'groq' || name === 'cerebras') && /gpt-oss/.test(model)) { payload.max_tokens = Math.max(body.maxTokens, 600); payload.reasoning_effort = 'low'; }
  if (noReasoning[name + '|' + model]) delete payload.reasoning_effort;
  const post = async pl => {
    try {
      return await fetchWithTimeout(p.url(), {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, bearer(p.key())),
        body: JSON.stringify(pl)
      }, timeoutMs);
    } catch (e) {
      const err = new Error(e && e.name === 'AbortError' ? '시간 초과' : ('네트워크 오류 ' + (e && e.message)));
      err.status = 0; throw err;
    }
  };
  let res = await post(payload);
  if (res.status === 400 && payload.reasoning_effort) {   // 이 모델이 reasoning_effort를 모르면 빼고 재시도
    delete payload.reasoning_effort; res = await post(payload);
    if (res.ok) noReasoning[name + '|' + model] = true;
  }
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.text()).replace(/\s+/g, ' ').slice(0, 220); } catch (e) {}
    const err = new Error('HTTP ' + res.status + ' ' + detail);
    err.status = res.status;
    err.retryAfter = parseInt((res.headers && res.headers.get && res.headers.get('retry-after')) || '0', 10) || 0;
    throw err;
  }
  const data = await res.json();
  const text = cleanText(data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content);
  if (!text) { const err = new Error('빈 응답'); err.status = 0; throw err; }
  return text;
}

async function discover(name, attempts, timeoutMs) {
  const p = PROVIDERS[name];
  if (!p.listUrl || !RANK[name]) return [];
  const c = discovered[name];
  if (c && Date.now() - c.at < 6 * 3600 * 1000) return c.ids;
  if ((discoverPause[name] || 0) > Date.now()) return [];
  try {
    const res = await fetchWithTimeout(p.listUrl(), { method: 'GET', headers: p.listHeaders(p.key()) }, timeoutMs);
    if (!res.ok) { let d = ''; try { d = (await res.text()).replace(/\s+/g, ' ').slice(0, 160); } catch (e) {} throw new Error('HTTP ' + res.status + ' ' + d); }
    const ids = RANK[name](p.parseList(await res.json()));
    discovered[name] = { at: Date.now(), ids };
    attempts.push({ provider: name, ok: false, err: '모델 목록 조회 후보: ' + (ids.join(', ') || '없음') });
    return ids;
  } catch (e) {
    discoverPause[name] = Date.now() + 10 * 60 * 1000;
    attempts.push({ provider: name, ok: false, err: '모델 목록 조회 실패: ' + String(e.message).slice(0, 160) });
    return [];
  }
}

/**
 * chat({ system, messages, maxTokens, temperature, validate })
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
    if (!p.key()) continue;
    if ((providerPause[name] || 0) > now()) { attempts.push({ provider: name, ok: false, err: '쉬는 중(한도 초과/키 문제)' }); continue; }
    const st = { stop: false, modelProblem: false };
    const tried = {};

    const attempt = async model => {
      if (tried[model]) return null;
      tried[model] = true;
      const mp = modelPause[name + '|' + model];
      if (mp && mp.until > now()) {
        attempts.push({ provider: name, model, ok: false, err: '쉬는 중: ' + mp.why });
        if (/^HTTP 40[04]/.test(mp.why)) st.modelProblem = true;
        return null;
      }
      try {
        const text = await callOne(name, model, body, timeoutMs);
        if (opts.validate && !opts.validate(text)) { attempts.push({ provider: name, model, ok: false, err: '검증 실패(길이/금지어/중복)' }); return null; }
        return { text, model };
      } catch (e) {
        const s = e.status || 0;
        const why = String(e.message).slice(0, 220);
        attempts.push({ provider: name, model, ok: false, status: s, err: why });
        if (s === 429) { providerPause[name] = now() + Math.min(Math.max((e.retryAfter || 60) * 1000, 30000), 600000); st.stop = true; }
        else if (s === 401 || s === 403) { providerPause[name] = now() + 30 * 60 * 1000; st.stop = true; }
        else if (s === 400 || s === 404) { modelPause[name + '|' + model] = { until: now() + 30 * 60 * 1000, why }; st.modelProblem = true; }
        else { modelPause[name + '|' + model] = { until: now() + 30 * 1000, why }; }
        return null;
      }
    };

    let hit = null;
    const first = (preferred[name] ? [preferred[name]] : []).concat(p.models());
    for (const m of first) { hit = await attempt(m); if (hit || st.stop) break; }
    if (!hit && !st.stop && st.modelProblem && p.listUrl) {
      const extra = await discover(name, attempts, timeoutMs);
      for (const m of extra) { hit = await attempt(m); if (hit || st.stop) break; }
    }
    if (hit) {
      preferred[name] = hit.model;
      attempts.push({ provider: name, model: hit.model, ok: true });
      return { text: hit.text, provider: name, model: hit.model, attempts };
    }
  }
  const err = new Error('모든 AI 제공자 실패');
  err.attempts = attempts;
  throw err;
}

module.exports = { chat, configured, order };