with open("capacitor.config.json", "r", encoding="utf-8") as f:
    cap_config = f.read()

with open("public/index.html", "r", encoding="utf-8") as f:
    content = f.read()

keywords = ["visualViewport", "Keyboard", "full-screen-overlay", "chat-window-card"]

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
    start = max(0, ln - 10)
    end = min(len(lines), ln + 10)
    ranges.append((start, end))

merged = []
for r in sorted(ranges):
    if merged and r[0] <= merged[-1][1]:
        merged[-1] = (merged[-1][0], max(merged[-1][1], r[1]))
    else:
        merged.append(list(r))

output = ["===== capacitor.config.json =====\n", cap_config, "\n\n===== index.html 관련 구간 =====\n"]
for start, end in merged:
    output.append(f"\n===== 줄 {start+1} ~ {end} =====\n")
    output.extend(lines[start:end])

with open("keyboard_extract.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"추출 완료: capacitor.config.json + index.html {len(merged)}개 구간, keyboard_extract.txt 저장됨")
