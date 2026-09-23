import re

path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(
    r"(?:[ \t]*//[^\n]*\n){0,4}"
    r"[ \t]*var dbg = document\.createElement\('div'\);.*?"
    r"window\.addEventListener\('load', updateDebugOverlay\);\n"
    r"(?:[ \t]*//[^\n]*\n)?",
    re.DOTALL
)

matches = pattern.findall(content)
if len(matches) != 1:
    raise SystemExit(f"[실패] 디버그 오버레이 블록 매치 {len(matches)}개 (1개여야 함) - 코드가 이전과 달라졌는지 확인 필요")

content = pattern.sub("", content, count=1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("[완료] 디버그 오버레이(초록창) 코드 전체 제거함")
