# -*- coding: utf-8 -*-
import subprocess, sys

path = "malbeot-app/public/index.html"
with open(path, "r", encoding="utf-8", newline='') as f:
    content = f.read()

def must_replace(old, new, label):
    global content
    if old not in content:
        print(f"❌ [{label}] 대상 코드를 찾을 수 없습니다. 코드가 이미 바뀌어 있을 수 있어요.")
        sys.exit(1)
    if content.count(old) != 1:
        print(f"❌ [{label}] 대상 코드가 1곳이 아니라 {content.count(old)}곳에서 발견됐습니다. 중단합니다.")
        sys.exit(1)
    content = content.replace(old, new, 1)
    print(f"✅ [{label}] 적용 완료")

# ── 0-46: 메시지 삭제 표시("메시지가 삭제되었습니다")는 이미 텍스트/이미지/실시간 모두 구현되어 있어
#          이번 패치에서는 건드리지 않음(재확인만 완료).

# ── 0-47a(핵심 원인 수정): 프로그램이 스스로 모달/화면을 닫을 때(closeModal 등) 히스토리 보정용으로
#    호출하는 history.back()이 popstate 핸들러에서 "진짜 사용자가 뒤로가기를 누른 것"으로 다시 처리되면서
#    화면이 한 번에 2개씩 닫히던 근본 원인을 수정(취소를 눌렀는데 전체화면 밖으로 나가지는 버그의 진짜 원인)
must_replace(
    "let uiBackStack = [];\r\nlet uiPopping = false;\r\nconst uiOverlayObserver = new MutationObserver(muts=>{\r\n  muts.forEach(m=>{\r\n    if (m.attributeName !== 'class') return;\r\n    const el = m.target;\r\n    if (!(el.classList.contains('full-screen-overlay') || el.classList.contains('modal-overlay'))) return;\r\n    const isActive = el.classList.contains('active');\r\n    const idx = uiBackStack.indexOf(el);\r\n    if (isActive && idx === -1){\r\n      uiBackStack.push(el);\r\n      history.pushState({ uiOverlay: uiBackStack.length }, '');\r\n    } else if (!isActive && idx !== -1){\r\n      uiBackStack.splice(idx, 1);\r\n      if (!uiPopping){ try{ history.back(); }catch(e){} }\r\n    }\r\n  });\r\n});\r\ndocument.querySelectorAll('.full-screen-overlay, .modal-overlay').forEach(el=> uiOverlayObserver.observe(el, {attributes:true}));\r\nwindow.addEventListener('popstate', ()=>{\r\n  if (uiBackStack.length > 0){\r\n    uiPopping = true;\r\n    const el = uiBackStack[uiBackStack.length - 1];\r\n    el.classList.remove('active');\r\n    setTimeout(()=>{ uiPopping = false; }, 0);\r\n",
    "let uiBackStack = [];\r\nlet uiPopping = false;\r\nconst uiOverlayObserver = new MutationObserver(muts=>{\r\n  muts.forEach(m=>{\r\n    if (m.attributeName !== 'class') return;\r\n    const el = m.target;\r\n    if (!(el.classList.contains('full-screen-overlay') || el.classList.contains('modal-overlay'))) return;\r\n    const isActive = el.classList.contains('active');\r\n    const idx = uiBackStack.indexOf(el);\r\n    if (isActive && idx === -1){\r\n      uiBackStack.push(el);\r\n      history.pushState({ uiOverlay: uiBackStack.length }, '');\r\n    } else if (!isActive && idx !== -1){\r\n      uiBackStack.splice(idx, 1);\r\n      // 0-47: 프로그램이 스스로 닫을 때(closeModal 등)도 히스토리 동기화를 위해 history.back()을 호출하는데,\r\n      // 이 back()이 나중에 popstate로 돌아왔을 때 \"사용자가 진짜로 뒤로가기를 누른 것\"으로 오인해서\r\n      // 그 아래 화면까지 한 번 더 닫아버리던 게 진짜 원인이었음. uiPopping을 여기서 미리 true로 세팅해서\r\n      // 그 되돌아온 popstate가 무시되도록 함(진짜 뒤로가기와 구분).\r\n      if (!uiPopping){ uiPopping = true; try{ history.back(); }catch(e){} }\r\n    }\r\n  });\r\n});\r\ndocument.querySelectorAll('.full-screen-overlay, .modal-overlay').forEach(el=> uiOverlayObserver.observe(el, {attributes:true}));\r\nwindow.addEventListener('popstate', ()=>{\r\n  // 0-47: 위에서 프로그램이 스스로 유발한 back()으로 인한 popstate면(uiPopping===true) 여기선 아무것도 안 하고 소비만 함\r\n  if (uiPopping){ uiPopping = false; return; }\r\n  if (uiBackStack.length > 0){\r\n    uiPopping = true;\r\n    const el = uiBackStack[uiBackStack.length - 1];\r\n    el.classList.remove('active');\r\n    setTimeout(()=>{ uiPopping = false; }, 0);\r\n",
    "0-47a 히스토리 이중닫힘 근본원인 수정"
)

# ── 0-47b: 차단/신고 선택창(blockReportModal), 신고 사유 선택창(reportCategoryModal) 빈 공간 터치시 닫히게
must_replace(
    '<div id="reportCategoryModal" class="modal-overlay">',
    '<div id="reportCategoryModal" class="modal-overlay" onclick="if(event.target===this) closeModal(\'reportCategoryModal\')">',
    "0-47b reportCategoryModal 빈공간 터치 닫기"
)
must_replace(
    '<div id="blockReportModal" class="modal-overlay">',
    '<div id="blockReportModal" class="modal-overlay" onclick="if(event.target===this) closeModal(\'blockReportModal\')">',
    "0-47b blockReportModal 빈공간 터치 닫기"
)

# ── 0-47c: 차단 확인을 브라우저 네이티브 confirm() 대신 앱 자체 확인창(showMiniAlert)으로 교체.
#    또한 기존엔 confirm()을 띄우기도 전에 blockReportModal을 먼저 닫아버려서 "취소"를 눌러도 이미 닫힌 상태였음 -> 취소를 누르면 아무 것도 닫지 않고(원래 화면 그대로 유지), 차단을 누른 경우에만 닫도록 순서 수정
must_replace(
    "function handleBlockAction(){\r\n  closeModal('blockReportModal');\r\n  if (!confirm('이 사용자를 차단하시겠습니까? 차단하면 서로 연락을 주고받을 수 없습니다.')) return;\r\n  let targetId = blockReportContext.id;\r\n  if (blockReportContext.type==='post' && currentPostCache) targetId = currentPostCache.authorId;\r\n  if (blockReportContext.type==='comment' && blockReportContext.authorId) targetId = blockReportContext.authorId;\r\n  socket.emit('user:block', targetId, ()=>{\r\n    if (blockReportContext.type==='chat'){ closeChatModal(); loadChatRoomList(); }\r\n    showMiniAlert('해당 사용자를 차단했습니다.', [{label:'확인', primary:true}]);\r\n  });\r\n}",
    "function handleBlockAction(){\r\n  // 0-47: 네이티브 confirm() 대신 앱 자체 확인창 사용 + 취소 시엔 blockReportModal을 닫지 않고 그대로 유지\r\n  showMiniAlert('이 사용자를 차단하시겠습니까? 차단하면 서로 연락을 주고받을 수 없습니다.', [\r\n    {label:'취소'},\r\n    {label:'차단', danger:true, onClick:()=>{\r\n      closeModal('blockReportModal');\r\n      let targetId = blockReportContext.id;\r\n      if (blockReportContext.type==='post' && currentPostCache) targetId = currentPostCache.authorId;\r\n      if (blockReportContext.type==='comment' && blockReportContext.authorId) targetId = blockReportContext.authorId;\r\n      socket.emit('user:block', targetId, ()=>{\r\n        if (blockReportContext.type==='chat'){ closeChatModal(); loadChatRoomList(); }\r\n        showMiniAlert('해당 사용자를 차단했습니다.', [{label:'확인', primary:true}]);\r\n      });\r\n    }}\r\n  ]);\r\n}",
    "0-47c 차단 확인창을 앱 자체 확인창으로 교체"
)

# ── 0-48: 프로필 추가사진 순서변경(숫자 배지 클릭식) - 대표사진은 "1" 표시(고정), 추가사진은 2,3,4,5 배지를
#    누르면 그 사진이 추가사진 목록 맨 뒤로 이동(=번호가 마지막으로 밀림)
must_replace(
    '<div class="photo-slots"><div class="photo-slot" onclick="triggerEditPhotoInput()">\r\n              <img id="editPhotoPreview" class="photo-preview hidden" alt="수정 사진">\r\n              <span id="editPhotoPlaceholder"><i class="fa-solid fa-plus"></i></span>\r\n            </div></div>',
    '<div class="photo-slots"><div class="photo-slot" onclick="triggerEditPhotoInput()">\r\n              <img id="editPhotoPreview" class="photo-preview hidden" alt="수정 사진">\r\n              <span id="editPhotoPlaceholder"><i class="fa-solid fa-plus"></i></span>\r\n              <span id="editPhotoBadgeMain" class="hidden" style="position:absolute;top:2px;left:2px;background:var(--primary);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;">1</span>\r\n            </div></div>',
    "0-48 대표사진 1번 배지 추가"
)
must_replace(
    "const EXTRA_PHOTO_MAX = 4;\r\nlet editExtraPhotos = [];\r\nfunction renderExtraPhotoSlots(){\r\n  const wrap = document.getElementById('editExtraPhotoSlots');\r\n  let html = editExtraPhotos.map((src,i)=>`\r\n    <div class=\"photo-slot\" style=\"flex:0 0 68px;width:68px;height:68px;\">\r\n      <img src=\"${src}\" class=\"photo-preview\">\r\n      <span onclick=\"event.stopPropagation();removeExtraPhoto(${i})\" style=\"position:absolute;top:2px;right:2px;background:rgba(0,0,0,.55);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;cursor:pointer;\"><i class=\"fa-solid fa-xmark\"></i></span>\r\n    </div>`).join('');\r\n  if (editExtraPhotos.length < EXTRA_PHOTO_MAX){\r\n    html += `<div class=\"photo-slot\" style=\"flex:0 0 68px;width:68px;height:68px;\" onclick=\"document.getElementById('editExtraPhotoInput').click()\"><span><i class=\"fa-solid fa-plus\"></i></span></div>`;\r\n  }\r\n  wrap.innerHTML = html;\r\n}",
    "const EXTRA_PHOTO_MAX = 4;\r\nlet editExtraPhotos = [];\r\n// 0-48: 사진 위 숫자 배지를 누르면 그 사진이 추가사진 목록 맨 뒤로 이동(=번호가 마지막으로 밀림), 나머지는 한 칸씩 앞으로 당겨짐\r\nfunction reorderExtraPhoto(i){\r\n  const item = editExtraPhotos.splice(i,1)[0];\r\n  editExtraPhotos.push(item);\r\n  renderExtraPhotoSlots();\r\n}\r\nfunction renderExtraPhotoSlots(){\r\n  const wrap = document.getElementById('editExtraPhotoSlots');\r\n  let html = editExtraPhotos.map((src,i)=>`\r\n    <div class=\"photo-slot\" style=\"flex:0 0 68px;width:68px;height:68px;\">\r\n      <img src=\"${src}\" class=\"photo-preview\">\r\n      <span onclick=\"event.stopPropagation();reorderExtraPhoto(${i})\" title=\"누르면 순서를 맨 뒤로 보냅니다\" style=\"position:absolute;top:2px;left:2px;background:var(--primary);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;cursor:pointer;\">${i+2}</span>\r\n      <span onclick=\"event.stopPropagation();removeExtraPhoto(${i})\" style=\"position:absolute;top:2px;right:2px;background:rgba(0,0,0,.55);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;cursor:pointer;\"><i class=\"fa-solid fa-xmark\"></i></span>\r\n    </div>`).join('');\r\n  if (editExtraPhotos.length < EXTRA_PHOTO_MAX){\r\n    html += `<div class=\"photo-slot\" style=\"flex:0 0 68px;width:68px;height:68px;\" onclick=\"document.getElementById('editExtraPhotoInput').click()\"><span><i class=\"fa-solid fa-plus\"></i></span></div>`;\r\n  }\r\n  wrap.innerHTML = html;\r\n}",
    "0-48 추가사진 순서변경 배지+함수 추가"
)
# 대표사진 배지(1) 표시/숨김을 기존 대표사진 미리보기 표시/숨김과 함께 토글되도록 3곳 동기화
must_replace(
    "function handleEditPhotoUpload(e){\r\n  const file=e.target.files[0]; if(!file) return;\r\n  editPhotoBase64 = await compressImageFile(file);\r\n  const p=document.getElementById('editPhotoPreview'); p.src=editPhotoBase64; p.classList.remove('hidden'); document.getElementById('editPhotoPlaceholder').classList.add('hidden');",
    "function handleEditPhotoUpload(e){\r\n  const file=e.target.files[0]; if(!file) return;\r\n  editPhotoBase64 = await compressImageFile(file);\r\n  const p=document.getElementById('editPhotoPreview'); p.src=editPhotoBase64; p.classList.remove('hidden'); document.getElementById('editPhotoPlaceholder').classList.add('hidden'); document.getElementById('editPhotoBadgeMain').classList.remove('hidden');",
    "0-48 업로드시 1번 배지 표시"
)
must_replace(
    "if (currentUser.photos && currentUser.photos.length){\r\n    editPhotoBase64=currentUser.photos[0]; preview.src=editPhotoBase64; preview.classList.remove('hidden'); document.getElementById('editPhotoPlaceholder').classList.add('hidden');",
    "if (currentUser.photos && currentUser.photos.length){\r\n    editPhotoBase64=currentUser.photos[0]; preview.src=editPhotoBase64; preview.classList.remove('hidden'); document.getElementById('editPhotoPlaceholder').classList.add('hidden'); document.getElementById('editPhotoBadgeMain').classList.remove('hidden');",
    "0-48 폼 로드시 1번 배지 표시"
)
must_replace(
    "  } else {\r\n    editPhotoBase64 = '';\r\n    preview.classList.add('hidden'); document.getElementById('editPhotoPlaceholder').classList.remove('hidden');",
    "  } else {\r\n    editPhotoBase64 = '';\r\n    preview.classList.add('hidden'); document.getElementById('editPhotoPlaceholder').classList.remove('hidden'); document.getElementById('editPhotoBadgeMain').classList.add('hidden');",
    "0-48 대표사진 없을 때 1번 배지 숨김"
)

# ── 0-49: 뒤로가기 시 화면이 2단계씩 닫히던(설정→계정→차단목록에서 뒤로가기 누르면 설정 밖까지 나가지던) 원인이던
#    중복 등록된 백스페이스 키 리스너 제거(더 정교한 히스토리 기반 리스너가 이미 별도로 존재해서 그걸로 통일)
must_replace(
    "/* 백스페이스 키로 뒤로가기: 입력창/텍스트영역에 포커스가 있을 땐 원래 백스페이스 동작(글자 지우기)을 그대로 두고,\r\n   그 외의 경우엔 현재 열려있는 화면/모달을 하나씩 닫음(뒤로가기 버튼을 누른 것과 동일하게 동작) */\r\ndocument.addEventListener('keydown', (e)=>{\r\n  if (e.key !== 'Backspace') return;\r\n  const active = document.activeElement;\r\n  const tag = active && active.tagName;\r\n  if (tag === 'INPUT' || tag === 'TEXTAREA' || (active && active.isContentEditable)) return;\r\n  e.preventDefault();\r\n  closeTopmostScreen();\r\n});\r\n\r\n",
    "/* 0-49: 백스페이스 뒤로가기 리스너가 파일 아래쪽(히스토리 기반 uiBackStack 리스너)과 중복 등록되어 있어서,\r\n   백스페이스 한 번에 화면이 2단계씩(예: 설정→계정→차단목록에서 누르면 설정 화면까지) 닫히던 버그가 있었음.\r\n   아래쪽의 히스토리 기반 리스너가 이 역할을 이미 대신하므로 여기 있던 중복 리스너는 제거함. */\r\n\r\n",
    "0-49 중복 백스페이스 리스너 제거"
)

with open(path, "w", encoding="utf-8", newline='') as f:
    f.write(content)

print("\n✅ 0-46~0-49 패치 전체 적용 완료")
print("   0-46: 이미 정상 구현되어 있어 건드리지 않음(텍스트/이미지 삭제 모두 '메시지가 삭제되었습니다' 실시간 표시 확인됨)")
print("   0-47: 화면이 2개씩 닫히던 진짜 원인(히스토리 이중처리) 수정 + 차단확인창 앱UI로 교체 + 빈공간 터치시 닫힘")
print("   0-48: 프로필 추가사진에 순서변경 숫자배지 추가(누르면 맨 뒤로 이동)")
print("   0-49: 중복 등록되어 있던 백스페이스 리스너 제거")

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "0-46~0-49: 메시지삭제 재확인, 화면 이중닫힘 근본원인 수정, 차단확인창 UI교체, 사진순서변경, 백스페이스 중복리스너 제거"], check=True)
print("✅ 커밋 완료")