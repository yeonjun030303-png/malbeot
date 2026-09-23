import os

base = r"C:\malbeot\.github\workflows"

static_map = {
    "abuse-detection.yml": ("subject: \"\U0001F6A8 [\uB9D0\uBC97] \uC774\uC0C1\uD589\uB3D9\uD0D0\uC9C0 \uACB0\uACFC\"", "subject: \"[\uAE34\uAE09] \uB9D0\uBC97 \uC774\uC0C1\uD589\uB3D9\uD0D0\uC9C0 \uBCF4\uACE0\uC758 \uAC74\""),
    "benchmark-research.yml": ("subject: \"\U0001F4CA [\uB9D0\uBC97] \uBCA4\uCE58\uB9C8\uD0B9 \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uBCA4\uCE58\uB9C8\uD0B9 \uBCF4\uACE0\uC758 \uAC74\""),
    "blue-ocean-planner.yml": ("subject: \"[\uB9D0\uBC97] \uBE14\uB8E8\uC624\uC158\uAE30\uD68D\uAD00 \uC8FC\uAC04 \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uBE14\uB8E8\uC624\uC158\uAE30\uD68D\uAD00 \uBCF4\uACE0\uC758 \uAC74\""),
    "bot-quality-audit.yml": ("subject: \"\U0001F50D [\uB9D0\uBC97] \uBD07 \uD488\uC9C8\uAC10\uC0AC \uACB0\uACFC\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uBD07\uD488\uC9C8\uAC10\uC0AC \uBCF4\uACE0\uC758 \uAC74\""),
    "budget-report.yml": ("subject: \"\U0001F9FE [\uB9D0\uBC97] \uC608\uC0B0\uC9D1\uD589 \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC608\uC0B0\uC9D1\uD589 \uBCF4\uACE0\uC758 \uAC74\""),
    "health-check.yml": ("subject: \"\U0001F3E5 [\uB9D0\uBC97] \uC11C\uBE44\uC2A4 \uC774\uC0C1 \uAC10\uC9C0\"", "subject: \"[\uAE34\uAE09] \uB9D0\uBC97 \uC11C\uBE44\uC2A4\uC774\uC0C1\uAC10\uC9C0 \uBCF4\uACE0\uC758 \uAC74\""),
    "inquiry-monitor.yml": ("subject: \"\U0001F4EE [\uB9D0\uBC97] \uACE0\uAC1D\uBB38\uC758 \uBAA8\uB2C8\uD130\uB9C1 \uACB0\uACFC\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uACE0\uAC1D\uBB38\uC758\uBAA8\uB2C8\uD130\uB9C1 \uBCF4\uACE0\uC758 \uAC74\""),
    "license-audit.yml": ("subject: \"\U0001F4C4 [\uB9D0\uBC97] \uB77C\uC774\uC120\uC2A4\u00B7\uC800\uC791\uAD8C \uC810\uAC80\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uB77C\uC774\uC120\uC2A4\uC800\uC791\uAD8C\uC810\uAC80 \uBCF4\uACE0\uC758 \uAC74\""),
    "metrics-monitor.yml": ("subject: \"\U0001F4C8 [\uB9D0\uBC97] \uC8FC\uAC04 \uC9C0\uD45C \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC8FC\uAC04\uC9C0\uD45C \uBCF4\uACE0\uC758 \uAC74\""),
    "monetization-idea.yml": ("subject: \"\U0001F4B0 [\uB9D0\uBC97] \uC218\uC775\uD654 \uC544\uC774\uB514\uC5B4\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC218\uC775\uD654\uC544\uC774\uB514\uC5B4 \uBCF4\uACE0\uC758 \uAC74\""),
    "new-dev-lead-review.yml": ("subject: \"[\uB9D0\uBC97] \uC2E0\uAC1C\uBC1C\uD300\uC7A5 \uC8FC\uAC04 \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC2E0\uAC1C\uBC1C\uD300\uC7A5 \uBCF4\uACE0\uC758 \uAC74\""),
    "pain-point-scout.yml": ("subject: \"[\uB9D0\uBC97] \uBD88\uD3B8\uD568\uC870\uC0AC\uAD00 \uC8FC\uAC04 \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uBD88\uD3B8\uD568\uC870\uC0AC\uAD00 \uBCF4\uACE0\uC758 \uAC74\""),
    "policy-check.yml": ("subject: \"\u2696\uFE0F [\uB9D0\uBC97] \uC57D\uAD00\u00B7\uC815\uCC45 \uC810\uAC80\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC57D\uAD00\uC815\uCC45\uC810\uAC80 \uBCF4\uACE0\uC758 \uAC74\""),
    "report-review.yml": ("subject: \"\U0001F6A8 [\uB9D0\uBC97] \uC2E0\uACE0-\uC81C\uC7AC \uAC80\uD1A0 \uACB0\uACFC\"", "subject: \"[\uAE34\uAE09] \uB9D0\uBC97 \uC2E0\uACE0\uC81C\uC7AC\uAC80\uD1A0 \uBCF4\uACE0\uC758 \uAC74\""),
    "review-monitor.yml": ("subject: \"\u2B50 [\uB9D0\uBC97] \uD6C4\uAE30 \uBAA8\uB2C8\uD130\uB9C1 \uACB0\uACFC\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uD6C4\uAE30\uBAA8\uB2C8\uD130\uB9C1 \uBCF4\uACE0\uC758 \uAC74\""),
    "sns-content-publisher.yml": ("subject: \"[\uB9D0\uBC97] SNS\uD3EC\uC2A4\uD305\uC9D1\uD589\uAD00 \uC77C\uC77C \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 SNS\uD3EC\uC2A4\uD305\uC9D1\uD589\uAD00 \uBCF4\uACE0\uC758 \uAC74\""),
    "sns-trend-analyst.yml": ("subject: \"[\uB9D0\uBC97] SNS\uD2B8\uB80C\uB4DC\uBD84\uC11D\uAD00 \uC77C\uC77C \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 SNS\uD2B8\uB80C\uB4DC\uBD84\uC11D\uAD00 \uBCF4\uACE0\uC758 \uAC74\""),
    "weekly-committee-review.yml": ("subject: \"\U0001F3E2 [\uB9D0\uBC97] \uC8FC\uAC04 \uCD1D\uAD04 \uB9AC\uD3EC\uD2B8\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC8FC\uAC04\uCD1D\uAD04 \uBCF4\uACE0\uC758 \uAC74\""),
    "weekly-idea-scout.yml": ("subject: \"\U0001F4A1 [\uB9D0\uBC97] \uC8FC\uAC04 \uC544\uC774\uB514\uC5B4 \uC81C\uC548\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC8FC\uAC04\uC544\uC774\uB514\uC5B4\uC81C\uC548 \uBCF4\uACE0\uC758 \uAC74\""),
    "weekly-marketing-advisor.yml": ("subject: \"\U0001F4CA [\uB9D0\uBC97] \uC8FC\uAC04 \uB9C8\uCF00\uD305 \uC81C\uC548\"", "subject: \"[\uC815\uAE30] \uB9D0\uBC97 \uC8FC\uAC04\uB9C8\uCF00\uD305\uC81C\uC548 \uBCF4\uACE0\uC758 \uAC74\""),
}

results = []
for fname, (old, new) in static_map.items():
    path = os.path.join(base, fname)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    count = content.count(old)
    if count == 0:
        results.append(f"[\uC624\uB958] {fname}: \uD328\uD134\uC744 \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.")
        continue
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    results.append(f"[\uC644\uB8CC] {fname}")

# daily-bug-review.yml: dynamic
path = os.path.join(base, "daily-bug-review.yml")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

anchor = "            echo \"has_result=false\" >> $GITHUB_OUTPUT\n          fi\n"
insert = anchor + "\n      - name: \uC2EC\uAC01\uB3C4 \uD310\uC815\n        if: steps.check.outputs.has_result == 'true'\n        id: severity\n        run: |\n          if grep -q \"CRITICAL\" review-result.md; then\n            echo \"level=\uAE34\uAE09\" >> \"$GITHUB_OUTPUT\"\n          else\n            echo \"level=\uC815\uAE30\" >> \"$GITHUB_OUTPUT\"\n          fi\n"

if anchor not in content:
    results.append("[\uC624\uB958] daily-bug-review.yml: \uC0BD\uC785\uC9C0\uC810 \uC5C6\uC74C")
else:
    content = content.replace(anchor, insert, 1)
    old_subj = "subject: \"\U0001F41B [\uB9D0\uBC97] \uB370\uC77C\uB9AC \uBC84\uADF8 \uB9AC\uBDF0\""
    new_subj = "subject: \"[${{ steps.severity.outputs.level }}] \uB9D0\uBC97 \uB370\uC77C\uB9AC\uBC84\uADF8\uB9AC\uBDF0 \uBCF4\uACE0\uC758 \uAC74\""
    if old_subj not in content:
        results.append("[\uC624\uB958] daily-bug-review.yml: subject \uD328\uD134 \uC5C6\uC74C")
    else:
        content = content.replace(old_subj, new_subj)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        results.append("[\uC644\uB8CC] daily-bug-review.yml (\uB3D9\uC801 \uAE34\uAE09/\uC815\uAE30)")

# security-audit.yml: dynamic
path = os.path.join(base, "security-audit.yml")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

anchor2 = "            echo \"exists=false\" >> \"$GITHUB_OUTPUT\"\n          fi\n"
insert2 = anchor2 + "\n      - name: \uAE34\uAE09 \uC5EC\uBD80 \uD310\uC815\n        if: steps.check.outputs.exists == 'true'\n        id: severity\n        run: |\n          if grep -qE \"critical: [1-9]|high: [1-9]\" review-result.md; then\n            echo \"level=\uAE34\uAE09\" >> \"$GITHUB_OUTPUT\"\n          else\n            echo \"level=\uC815\uAE30\" >> \"$GITHUB_OUTPUT\"\n          fi\n"

if anchor2 not in content:
    results.append("[\uC624\uB958] security-audit.yml: \uC0BD\uC785\uC9C0\uC810 \uC5C6\uC74C")
else:
    content = content.replace(anchor2, insert2, 1)
    old_subj2 = "subject: \"\U0001F512 [\uB9D0\uBC97] \uBCF4\uC548 \uC810\uAC80 \uACB0\uACFC\""
    new_subj2 = "subject: \"[${{ steps.severity.outputs.level }}] \uB9D0\uBC97 \uBCF4\uC548\uC810\uAC80 \uBCF4\uACE0\uC758 \uAC74\""
    if old_subj2 not in content:
        results.append("[\uC624\uB958] security-audit.yml: subject \uD328\uD134 \uC5C6\uC74C")
    else:
        content = content.replace(old_subj2, new_subj2)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        results.append("[\uC644\uB8CC] security-audit.yml (\uB3D9\uC801 \uAE34\uAE09/\uC815\uAE30)")

for r in results:
    print(r)
