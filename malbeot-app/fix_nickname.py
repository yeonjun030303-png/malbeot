import re

with open('server.js', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = []

# 1. validateProfileInput 안의 강제 차단 로직 제거
old1 = """function validateProfileInput(data) {
  if (!data.nickname || !String(data.nickname).trim().length) return '닉네임을 입력해주세요.';
  if (containsBannedWord(data.nickname)) return '닉네임에 부적절한 단어가 포함되어 있습니다.';
  const age = parseInt(data.age, 10);"""
new1 = """function validateProfileInput(data) {
  if (!data.nickname || !String(data.nickname).trim().length) return '닉네임을 입력해주세요.';
  const age = parseInt(data.age, 10);"""
replacements.append((old1, new1, 'validateProfileInput'))

# 2. auth:signup - confirmed 플래그 + nicknameFiltered 추가
old2 = """      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      const existing = await findUserByPhone(data.phone);
      if (existing) return cb({ success: false, alreadyExists: true });
      const passwordHash = await hashPassword(String(data.password));
      const user = {
        id: genId('u'), phone: data.phone, passwordHash, nickname: data.nickname,
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),"""
new2 = """      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      if (containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      const existing = await findUserByPhone(data.phone);
      if (existing) return cb({ success: false, alreadyExists: true });
      const passwordHash = await hashPassword(String(data.password));
      const user = {
        id: genId('u'), phone: data.phone, passwordHash, nickname: data.nickname,
        nicknameFiltered: containsBannedWord(data.nickname),
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),"""
replacements.append((old2, new2, 'auth:signup'))

# 3. auth:kakao_complete_profile - confirmed 플래그 + nicknameFiltered 추가
old3 = """      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      const user = {
        id: genId('u'), phone: '', kakaoId: payload.kakaoId, nickname: data.nickname,
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),"""
new3 = """      const profileError = validateProfileInput(data);
      if (profileError) return cb({ success: false, message: profileError });
      if (containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      const user = {
        id: genId('u'), phone: '', kakaoId: payload.kakaoId, nickname: data.nickname,
        nicknameFiltered: containsBannedWord(data.nickname),
        region: data.region, gender: data.gender, age: parseInt(data.age, 10),"""
replacements.append((old3, new3, 'auth:kakao_complete_profile'))

# 4. profile:update - 하드 블록을 confirmed 플래그 방식으로 교체
old4 = """      if (data.nickname && containsBannedWord(data.nickname)) {
        return cb({ success: false, message: '닉네임에 부적절한 단어가 포함되어 변경할 수 없습니다.' });
      }

      if (data.photos && data.photos[0]) {"""
new4 = """      if (data.nickname && containsBannedWord(data.nickname) && data.confirmed !== true) {
        return cb({ success: false, needsConfirm: true });
      }
      if (data.nickname) {
        data.nicknameFiltered = containsBannedWord(data.nickname);
      }

      if (data.photos && data.photos[0]) {"""
replacements.append((old4, new4, 'profile:update'))

for old, new, label in replacements:
    count = content.count(old)
    if count != 1:
        print(f'[경고] {label}: 매치 {count}개 (1개여야 정상) - 이 부분은 수동 확인 필요')
        continue
    content = content.replace(old, new)
    print(f'[완료] {label}')

with open('server.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('저장 완료')