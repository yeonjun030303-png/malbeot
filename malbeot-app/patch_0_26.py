import re

path = "public/refund-policy.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) 제목을 쌀+구독 둘 다 아우르도록 수정
old_title = '<h1>쌀 충전 환불,<br>이렇게 처리돼요</h1>'
new_title = '<h1>쌀 충전·구독 환불,<br>이렇게 처리돼요</h1>'
assert old_title in content, "제목을 찾을 수 없습니다"
content = content.replace(old_title, new_title)

# 2) 기존 3,4,5번 섹션 번호를 4,5,6으로 밀기 (뒤에서부터 치환해야 안 꼬임)
content = content.replace('<h2 data-num="5">문의처</h2>', '<h2 data-num="6">문의처</h2>')
content = content.replace('<h2 data-num="4">환불 승인 후 처리</h2>', '<h2 data-num="5">환불 승인 후 처리</h2>')
content = content.replace('<h2 data-num="3">환불이 제한되는 경우</h2>', '<h2 data-num="4">환불이 제한되는 경우</h2>')

# 3) 새 구독 환불 규정 섹션(3번)을 "청약철회(환불) 가능 조건" 섹션 뒤에 삽입
anchor = '''      </ul>
    </section>

    <section>
      <h2 data-num="4">환불이 제한되는 경우</h2>'''
assert anchor in content, "삽입 위치를 찾을 수 없습니다"

new_section = '''      </ul>
    </section>

    <section>
      <h2 data-num="3">구독제(골드/플래티넘) 환불 규정</h2>
      <p>말벗의 골드/플래티넘 구독은 카드로 매달 자동 청구되는 정기구독이 아니라, <b>14일권/1년권을 한 번 결제하면 해당 기간 동안만 등급이 부여되는 기간제(1회성) 상품</b>이에요. 별도의 해지 절차가 필요 없고, 기간이 지나면 다음 결제 없이 자동으로 등급이 해제돼요.</p>
      <ul>
        <li>결제 완료일로부터 <b>7일 이내</b>이고, 구독 혜택(등급 표시, 함께 지급된 쌀, 방문자·좋아요 전체열람 등)을 <b>전혀 사용하지 않은 경우</b>에 한해 청약철회(환불)를 신청할 수 있어요.</li>
        <li>구독과 함께 지급되는 쌀을 사용했거나, 등급 뱃지·로고색상 등 구독 혜택을 한 번이라도 이용한 경우 환불 대상에서 제외돼요.</li>
        <li>환불이 승인되면 남은 구독 기간과 함께 지급됐던 쌀(미사용분)이 모두 회수되고, 등급도 즉시 기본으로 전환돼요.</li>
        <li>운영팀이 테스트·CS 대응 목적으로 결제 없이 직접 지급한 구독은 실제 결제 건이 아니므로 이 환불 규정의 적용 대상이 아니에요.</li>
      </ul>
    </section>

    <section>
      <h2 data-num="4">환불이 제한되는 경우</h2>'''

content = content.replace(anchor, new_section)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 0-26 패치 적용 완료: refund-policy.html에 구독제 환불 규정 섹션 추가됨")