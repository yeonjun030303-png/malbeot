path = r"public\index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """  window.addEventListener('pageshow', resetPinchZoom);
})*
</script>"""

new = """  window.addEventListener('pageshow', resetPinchZoom);
})();
</script>"""

count = content.count(old)
if count == 0:
    print("[오류] 패턴을 찾을 수 없습니다.")
elif count > 1:
    print(f"[경고] {count}번 발견됨(1번이어야 함), 건너뜀")
else:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[완료] })*  ->  })(); 로 수정됨")
