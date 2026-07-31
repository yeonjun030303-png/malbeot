const nsfwjs = require('nsfwjs');
const tf = require('@tensorflow/tfjs-node');

// 텍스트 금지어 목록 (예시 - 운영 전 계속 추가 필요)
const BANNED_WORDS = [
  '시발', '씨발', '개새끼', '병신', '지랄', '좆'
  // 필요한 금지어를 계속 추가하세요
];

function containsBannedWord(text) {
  if (!text) return false;
  const normalized = text.toLowerCase().replace(/\s/g, '');
  return BANNED_WORDS.some(word => normalized.includes(word));
}

// NSFW 이미지 감지 모델 (최초 1회 로드 후 재사용)
let nsfwModel = null;
async function loadNsfwModel() {
  if (!nsfwModel) {
    nsfwModel = await nsfwjs.load();
  }
  return nsfwModel;
}

// imageBuffer: 이미지 파일의 Buffer
async function checkImageNsfw(imageBuffer) {
  try {
    const model = await loadNsfwModel();
    const image = await tf.node.decodeImage(imageBuffer, 3);
    const predictions = await model.classify(image);
    image.dispose();

    const scoreMap = {};
    predictions.forEach(p => { scoreMap[p.className] = p.probability; });

    const dangerScore =
      (scoreMap['Porn'] || 0) +
      (scoreMap['Hentai'] || 0) +
      (scoreMap['Sexy'] || 0);

    return {
      isNsfw: dangerScore >= 0.95,
      score: dangerScore,
      details: predictions
    };
  } catch (err) {
    console.error('NSFW 검사 중 오류:', err);
    // 검사 실패 시 안전하게 통과시킬지 차단할지는 정책 결정 필요 (기본: 통과)
    return { isNsfw: false, score: 0, error: err.message };
  }
}

module.exports = {
  BANNED_WORDS,
  containsBannedWord,
  checkImageNsfw
};