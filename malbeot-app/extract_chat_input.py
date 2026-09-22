path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

keywords = ["message-input", "messageInput", "chat-input", "chatInput", "emoji", "이모지", "send-btn", "sendBtn", "보내기"]

lines = content.split("\n")
found_lines = []
for i, line in enumerate(lines):
    for kw in keywords:
        if kw.lower() in line.lower():
            found_lines.append(i)
            break

found_lines = sorted(set(found_lines))

ranges = []
for ln in found_lines:
    start = max(0, ln - 15)
    end = min(len(lines), ln + 15)
    ranges.append((start, end))

merged = []
for r in sorted(ranges):
    if merged and r[0] <= merged[-1][1]:
        merged[-1] = (merged[-1][0], max(merged[-1][1], r[1]))
    else:
        merged.append(list(r))

output = []
for start, end in merged:
    output.append(f"\n===== 줄 {start+1} ~ {end} =====\n")
    output.extend(lines[start:end])

with open("chat_input_extract.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"추출 완료: 총 {len(merged)}개 구간, chat_input_extract.txt 파일로 저장됨")
