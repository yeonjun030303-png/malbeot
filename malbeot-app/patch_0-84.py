path = "public/child-safety-standards.html"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_email = "kickoff030303@gmail.com"
new_email = "owner@cnsstudiokorea.com"

count = content.count(old_email)
content = content.replace(old_email, new_email)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"{count}곳 교체 완료: {old_email} -> {new_email}")