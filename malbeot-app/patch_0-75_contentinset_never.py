import json

path = "capacitor.config.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

if data.get("ios", {}).get("contentInset") != "automatic":
    raise SystemExit(f"[실패] 현재 ios.contentInset 값이 예상과 다름: {data.get('ios')}")

data["ios"]["contentInset"] = "never"

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("[완료] ios.contentInset: automatic -> never 로 변경함")
