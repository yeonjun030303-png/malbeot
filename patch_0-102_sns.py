# -*- coding: utf-8 -*-
# 0-102: SNS 콘텐츠 간접 홍보 개편
#  - 형식 5종: 공감형/밸런스게임형/이슈코멘트형/리스트형/상황극형
#  - 5일 중 4일은 앱 언급 완전히 없음(순수 콘텐츠), 1일만 마지막 줄에 약하게 연결
#  - 이슈코멘트형은 실존 인물/사건 단정 언급 금지, 일반 트렌드만
import io, os, shutil, subprocess

P = "scripts/sns-content-publisher.js"
if not os.path.exists(P):
    raise SystemExit("[실패] %s 없음. C:\\malbeot 에서 실행했는지 확인" % P)

s = io.open(P, "r", encoding="utf-8").read()
bak = P + ".bak"
shutil.copyfile(P, bak)

def rep(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit("[실패] %s : 매칭 %d곳(1곳이어야 함). 수정 없이 중단." % (label, n))
    return text.replace(old, new, 1)

OLD_FORMATS_BLOCK = """const FORMATS = ['공감형', '질문형', '리스트형', '상황극형', '관심사형'];
const FORMAT_GUIDE = {
  '공감형': '대학생이 일상에서 느끼는 심심함/혼자인 순간을 짚는 공감 한 줄로 시작',
  '질문형': '"너는 어느 쪽?" 같은 가벼운 선택 질문으로 시작해서 댓글을 유도',
  '리스트형': '"이럴 때 말벗 켜는 사람 특징 3가지"처럼 짧은 리스트',
  '상황극형': '카톡/과제/시험기간/공강 같은 상황을 짧은 대사 톤으로 묘사',
  '관심사형': 'MBTI, 게임, 카페, 여행 등 관심사로 사람을 만난다는 점을 강조'
};"""

NEW_FORMATS_BLOCK = """const FORMATS = ['공감형', '밸런스게임형', '이슈코멘트형', '리스트형', '상황극형'];
const FORMAT_GUIDE = {
  '공감형': '대학생이 일상에서 느끼는 심심함/공감 포인트를 짚는 한 줄',
  '밸런스게임형': '"자취 vs 기숙사", "아싸 vs 인싸"처럼 둘 중 하나를 고르게 하는 가벼운 밸런스 게임',
  '이슈코멘트형': '요즘 화제인 사회/문화/예능/일상 트렌드에 대한 짧고 재치있는 생각거리나 코멘트. 특정 실존 인물이나 사건을 사실처럼 단정하지 않고, 일반적인 현상이나 트렌드 위주로 가볍게 다룬다',
  '리스트형': '"이런 사람 특징 3가지"처럼 짧고 공감 가는 리스트',
  '상황극형': '카톡/과제/시험기간/공강 같은 상황을 짧은 대사 톤으로 묘사'
};
function promoLevel() {
  return (dayIndex() % 5 === 4) ? 'weak' : 'none';
}"""

s = rep(s, OLD_FORMATS_BLOCK, NEW_FORMATS_BLOCK, "0-102 FORMATS/GUIDE 교체")

OLD_PROMPT_FN = """function buildPrompt(trendGuide, format) {
  return `당신은 20대 초반 대학생을 대상으로 하는 SNS 마케터입니다.
"말벗"은 관심사(취미, MBTI, 만남 목적)로 실제 사람들과 채팅하는 19세 이상 전용 앱입니다.

[오늘의 트렌드 가이드]
${trendGuide || '(없음)'}

[오늘의 형식] ${format}: ${FORMAT_GUIDE[format]}

규칙:
- 대상은 대학생. 말투는 친구에게 말하듯 짧고 가볍게. 이모지는 캡션에 2개 이내.
- 트렌드 단어는 어휘로만 자연스럽게 쓰고, 다른 계정의 문장이나 유행 문장을 그대로 따라 쓰지 않는다.
- 실제 사람들과 채팅하는 앱이라는 점만 말한다. AI, 상담, 치유, 위로 약속, 랜덤채팅, 과장 표현(100%, 무조건, 24시간, 365일)은 쓰지 않는다.
- 연예인, 브랜드, 드라마/영화, 노래 제목, 특정 학교 이름은 쓰지 않는다.
- hook은 공백 포함 20자 이내, 스크롤을 멈추게 하는 한 줄.
- sub는 hook 보충 한 줄(30자 이내).
- caption은 첫 줄 후킹, 본문 3~4줄, 마지막 줄 행동 유도(예: 프로필 링크에서 확인).
- hashtags는 6~8개, 일반 단어만(예: 대학생, 공강, 시험기간, mbti, 친구만들기).
- blog_title, blog_body(500자 내외)는 네이버 블로그용.

반드시 아래 JSON만 출력하세요(코드블록 금지):
{"hook":"","sub":"","caption":"","hashtags":["",""],"blog_title":"","blog_body":""}`;
}"""

NEW_PROMPT_FN = """function buildPrompt(trendGuide, format, promo) {
  const promoRule = promo === 'weak'
    ? '- caption 맨 마지막 한 줄에만 아주 가볍게 연결한다. 예: "이런 얘기 나눌 사람 있으면 좋겠다 싶을 때, 프로필 확인해봐" 처럼 부담 없는 톤으로. 앱 이름은 쓰지 않는다.'
    : '- 이 글에는 앱, 서비스, 프로필 링크, "말벗" 등 어떤 홍보성 언급도 절대 넣지 않는다. 그냥 대학생이 저장하거나 공유하고 싶은 독립적인 콘텐츠로만 만든다.';
  const issueRule = format === '이슈코멘트형'
    ? '\\n- 특정 실존 인물, 회사, 사건을 사실처럼 단정하거나 이름을 지어내지 않는다. 실제 뉴스 기사의 문장을 절대 그대로 베끼지 않는다. "요즘 이런 얘기 많더라" 정도의 일반적인 트렌드 코멘트로만 쓴다.'
    : '';
  return `당신은 20대 초반 대학생 대상 SNS 계정의 콘텐츠 작가입니다.
이 계정은 대학생이 공감하고 저장하고 싶은 콘텐츠를 올리는 라이프스타일 계정입니다.

[오늘의 트렌드 가이드]
${trendGuide || '(없음)'}

[오늘의 형식] ${format}: ${FORMAT_GUIDE[format]}

규칙:
- 말투는 친구에게 말하듯 짧고 가볍게. 이모지는 캡션에 2개 이내.
- 트렌드 단어는 어휘로만 자연스럽게 쓰고, 다른 계정의 문장이나 유행 문장을 그대로 따라 쓰지 않는다.
- 연예인 실명, 특정 브랜드명, 드라마/영화 제목, 노래 제목, 특정 학교 이름은 쓰지 않는다.
- 과장 표현(100%, 무조건, 24시간, 365일)은 쓰지 않는다.
${promoRule}${issueRule}
- hook은 공백 포함 20자 이내, 스크롤을 멈추게 하는 한 줄.
- sub는 hook 보충 한 줄(30자 이내).
- caption은 첫 줄 후킹, 본문 3~4줄.
- hashtags는 6~8개, 일반 단어만(예: 대학생, 공강, 시험기간, mbti, 오늘의밸런스게임).
- blog_title, blog_body(500자 내외)는 네이버 블로그용.

반드시 아래 JSON만 출력하세요(코드블록 금지):
{"hook":"","sub":"","caption":"","hashtags":["",""],"blog_title":"","blog_body":""}`;
}"""

s = rep(s, OLD_PROMPT_FN, NEW_PROMPT_FN, "0-102 buildPrompt 교체")

s = rep(s,
  "async function generate(trendGuide, format) {\n  for (let i = 0; i < 2; i++) {\n    const raw = await callGemini(buildPrompt(trendGuide, format));",
  "async function generate(trendGuide, format, promo) {\n  for (let i = 0; i < 2; i++) {\n    const raw = await callGemini(buildPrompt(trendGuide, format, promo));",
  "0-102 generate() 시그니처")

s = rep(s,
  "const format = FORMATS[dayIndex() % FORMATS.length];\n\n  let g = null;\n  try { g = await generate(trendGuide, format); } catch (e) { console.log('Gemini call failed:', e.message); }",
  "const format = FORMATS[dayIndex() % FORMATS.length];\n  const promo = promoLevel();\n\n  let g = null;\n  try { g = await generate(trendGuide, format, promo); } catch (e) { console.log('Gemini call failed:', e.message); }",
  "0-102 main()에서 promo 전달")

s = rep(s,
  """    const igCaption = `${g.caption.trim()}\\n\\n${g.tags.map(t => '#' + t).join(' ')}\\n\\n19세 이상 이용 가능`;""",
  """    const igCaption = promo === 'weak'
      ? `${g.caption.trim()}\\n\\n${g.tags.map(t => '#' + t).join(' ')}\\n\\n19세 이상 이용 가능`
      : `${g.caption.trim()}\\n\\n${g.tags.map(t => '#' + t).join(' ')}`;""",
  "0-102 캡션 조립 - 순수 콘텐츠일 땐 19+문구 생략")

s = rep(s,
  """    report = `# SNS포스팅집행관 일일 리포트
생성일: ${TODAY}
형식: ${format}""",
  """    report = `# SNS포스팅집행관 일일 리포트
생성일: ${TODAY}
형식: ${format} (홍보 수준: ${promo === 'weak' ? '약한 연결' : '앱 언급 없음'})""",
  "0-102 리포트에 홍보 수준 표시")

with io.open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(s)

r = subprocess.run(["node", "--check", P], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copyfile(bak, P)
    os.remove(bak)
    print(r.stderr)
    raise SystemExit("[실패] 문법 오류. 원래 파일로 복구함.")

os.remove(bak)
print("[적용됨] 0-102: 형식 5종 개편(공감/밸런스게임/이슈코멘트/리스트/상황극), 5일 중 4일 앱 언급 없음")