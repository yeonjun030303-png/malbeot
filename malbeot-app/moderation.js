cat > moderation.js << 'EOF'
const tf = require('@tensorflow/tfjs-node');
const nsfw = require('nsfwjs');

// ===== 이미지 노출 감지 (NSFWJS, 무료 오픈소스) =====
const NSFW_THRESHOLD = 0.95; // porn+hentai+sexy 확률 합이 이 값 이상이면 차단

let modelPromise = null;
function getModel() {
  if (!modelPromise) modelPromise = nsfw.load();
  return modelPromise;
}

// dataUrl(base64) 이미지를 검사해서 { blocked, score, predictions } 반환
async function checkImageNsfw(dataUrl) {
  if (!dataUrl || !/^data:image\//.test(dataUrl)) return { blocked: false, score: 0 };
  try {
    const base64 = dataUrl.split(',')[1];
    const buffer = Buffer.from(base64, 'base64');
    const image = tf.node.decodeImage(buffer, 3);
    const model = await getModel();
    const predictions = await model.classify(image);
    image.dispose();
    const badProb = predictions
      .filter(p => ['Porn', 'Hentai', 'Sexy'].includes(p.className))
      .reduce((sum, p) => sum + p.probability, 0);
    return { blocked: badProb >= NSFW_THRESHOLD, score: badProb, predictions };
  } catch (e) {
    console.error('[NSFW 이미지 검사 오류]', e);
    // 검사 자체가 실패하면 서비스 중단을 막기 위해 일단 통과시킴 (필요하면 반대로 바꿀 수 있음)
    return { blocked: false, score: 0, error: true };
  }
}

// ===== 텍스트 금지어 필터 =====
// 필요에 따라 계속 추가해서 확장하시면 됩니다.
const BANNED_WORDS = [
  // 성적인 단어
  '섹스', '19금', '자위', '성매매', '조건만남', '스와핑', 'fwb', '떡치',
  // 정치적으로 민감한 단어
  '국회의원', '대통령선거', '탄핵', '보수정당', '진보정당', '여의도',
  // 비하/조롱성 단어
  '노무현', '일베', '틀딱', '한남', '한녀', '급식충'
];

function containsBannedWord(text) {
  if (!text) return null;
  const lower = String(text).toLowerCase();
  return BANNED_WORDS.find(w => lower.includes(w.toLowerCase())) || null;
}

module.exports = { checkImageNsfw, containsBannedWord, NSFW_THRESHOLD, BANNED_WORDS };
EOF