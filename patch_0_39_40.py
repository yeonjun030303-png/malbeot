# 0-39: 채팅 사진/동영상 미리보기를 5개 한 줄로 + 전체보기를 우측 드로어 방식으로 변경
# 0-40: 채팅 사진 전송 전 미리보기(뒤로가기/전송) + 편집(회전/펜/블러브러시/지우개) 기능 추가
# ※ 0-38에서 이미 반영된 "관리자 구독지급 시 포인트 동시지급"과 겹치는 작업은 이번 패치에서 제외함
#    (server.js는 이번 패치에서 건드리지 않습니다)

path_h = "public/index.html"
with open(path_h, "r", encoding="utf-8") as f:
    h = f.read()

# 1) CSS 추가
old = '''.icon-round-btn.active{background:var(--primary);color:#fff;}'''
assert old in h, "icon-round-btn CSS를 찾을 수 없습니다"
new = '''.icon-round-btn.active{background:var(--primary);color:#fff;}
.photo-tool-btn{background:none;border:none;color:#fff;display:flex;flex-direction:column;align-items:center;gap:4px;font-size:11px;cursor:pointer;padding:7px 12px;border-radius:10px;}
.photo-tool-btn.active{color:var(--primary);background:rgba(255,255,255,.14);}
#photoPreviewCanvas,#photoEditCanvas{max-width:100%;max-height:100%;touch-action:none;}'''
h = h.replace(old, new)
print("✅ [1/9] CSS 추가 완료")

# 2) 채팅방 정보 - 사진갤러리 미리보기 6개→5개 한 줄
old = '''        <div id="groupInfoGallery" style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;"></div>'''
assert old in h, "groupInfoGallery를 찾을 수 없습니다"
h = h.replace(old, '''        <div id="groupInfoGallery" style="display:grid;grid-template-columns:repeat(5,1fr);gap:4px;"></div>''')

old = '''  gallery.innerHTML = (res.gallery||[]).slice(0,6).map(g=>`<div style="aspect-ratio:1;border-radius:8px;overflow:hidden;background:#eee;cursor:pointer;" onclick="openImageLightbox('${g.data}')"><img src="${g.data}" style="width:100%;height:100%;object-fit:cover;"></div>`).join('') || `<div style="grid-column:1/-1;color:var(--text-muted);font-size:12px;text-align:center;padding:10px 0;">등록된 사진/동영상이 없습니다.</div>`;
  document.getElementById('groupGalleryMoreBtn').style.display = (res.gallery||[]).length > 6 ? 'block' : 'none';'''
assert old in h, "renderGroupInfoScreen 갤러리 렌더링부를 찾을 수 없습니다"
h = h.replace(old, '''  gallery.innerHTML = (res.gallery||[]).slice(0,5).map(g=>`<div style="aspect-ratio:1;border-radius:8px;overflow:hidden;background:#eee;cursor:pointer;" onclick="openImageLightbox('${g.data}')"><img src="${g.data}" style="width:100%;height:100%;object-fit:cover;"></div>`).join('') || `<div style="grid-column:1/-1;color:var(--text-muted);font-size:12px;text-align:center;padding:10px 0;">등록된 사진/동영상이 없습니다.</div>`;
  document.getElementById('groupGalleryMoreBtn').style.display = (res.gallery||[]).length > 5 ? 'block' : 'none';''')
print("✅ [2/9] 갤러리 미리보기 5개 한 줄 전환 완료")

# 3) 전체보기(더보기) 화면을 우측 드로어 방식으로 전환
old = '''  <div id="groupGalleryScreen" class="full-screen-overlay">
    <div class="chat-header-row">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeFullScreen('groupGalleryScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="chat-header-nick" style="cursor:default;">사진/동영상</div>
    </div>
    <div id="groupGalleryFullGrid" style="padding:10px;overflow-y:auto;flex:1;display:grid;grid-template-columns:repeat(3,1fr);gap:6px;"></div>
  </div>'''
assert old in h, "groupGalleryScreen을 찾을 수 없습니다"
new = '''  <div id="groupGalleryScreen" class="full-screen-overlay drawer-right">
    <div class="chat-header-row">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;" onclick="closeFullScreen('groupGalleryScreen')"><i class="fa-solid fa-arrow-left"></i></button>
      <div class="chat-header-nick" style="cursor:default;">사진/동영상</div>
    </div>
    <div id="groupGalleryFullGrid" style="padding:10px;overflow-y:auto;flex:1;display:grid;grid-template-columns:repeat(5,1fr);gap:4px;"></div>
  </div>'''
h = h.replace(old, new)

old = '''  <div id="drawerBackdrop" onclick="closeFullScreen('groupInfoScreen')"></div>'''
assert old in h, "drawerBackdrop을 찾을 수 없습니다"
h = h.replace(old, '''  <div id="drawerBackdrop" onclick="closeAnyDrawer()"></div>''')
print("✅ [3/9] 전체보기 화면 우측 드로어 전환 완료")

# 4) drawer가 여러 개일 때 뒷배경 클릭으로 전부 닫히도록 일반화
old = '''function closeFullScreen(id){
  const el = document.getElementById(id);
  el.classList.remove('active');
  if (el.classList.contains('drawer-right')){
    const backdrop = el.parentElement.querySelector('#drawerBackdrop');
    if (backdrop) backdrop.classList.remove('active');
  }
}'''
assert old in h, "closeFullScreen 함수를 찾을 수 없습니다"
new = old + '''
// 0-39: drawer-right 형태 화면이 여러 개(채팅방 정보/사진갤러리)로 늘어나면서, 뒷배경(drawerBackdrop) 클릭 시
// 특정 화면만 닫도록 고정되어 있던 걸 "현재 열려있는 drawer를 전부 닫기"로 일반화함
function closeAnyDrawer(){
  document.querySelectorAll('.full-screen-overlay.drawer-right.active').forEach(el=> closeFullScreen(el.id));
}'''
h = h.replace(old, new)
print("✅ [4/9] closeAnyDrawer 함수 추가 완료")

# 5) 사진 미리보기+편집 화면 마크업 삽입
old = '''  <div id="imageLightboxOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:9999;align-items:center;justify-content:center;" onclick="closeImageLightbox()">
    <img id="imageLightboxImg" src="" style="max-width:94%;max-height:88%;object-fit:contain;">
  </div>

  <div id="scrollTopBtn" onclick="scrollActiveContainerToTop()"><i class="fa-solid fa-arrow-up"></i></div>'''
assert old in h, "imageLightboxOverlay/scrollTopBtn 삽입 위치를 찾을 수 없습니다"
new = '''  <div id="imageLightboxOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:9999;align-items:center;justify-content:center;" onclick="closeImageLightbox()">
    <img id="imageLightboxImg" src="" style="max-width:94%;max-height:88%;object-fit:contain;">
  </div>

  <!-- 0-40: 채팅 사진 전송 전 미리보기 + 편집(회전/블러/펜/지우개) 화면 -->
  <div id="photoPreviewScreen" class="full-screen-overlay" style="background:#000;z-index:300;">
    <div class="chat-header-row" style="background:#000;border:none;">
      <button class="back-btn" style="background:none;border:none;font-size:18px;cursor:pointer;color:#fff;" onclick="closePhotoPreview()"><i class="fa-solid fa-arrow-left"></i></button>
      <div style="margin-left:auto;">
        <button class="btn btn-primary btn-sm" onclick="sendPreviewedPhoto()">전송</button>
      </div>
    </div>
    <div style="flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;">
      <canvas id="photoPreviewCanvas"></canvas>
    </div>
    <div style="display:flex;justify-content:center;padding:14px;">
      <button type="button" style="background:rgba(255,255,255,.15);border:none;color:#fff;border-radius:20px;padding:9px 20px;display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;" onclick="enterPhotoEditMode()"><i class="fa-solid fa-pen"></i> 편집</button>
    </div>

    <div id="photoEditBar" class="hidden" style="position:absolute;inset:0;background:#000;display:flex;flex-direction:column;z-index:2;">
      <div class="chat-header-row" style="background:#000;border:none;">
        <button class="back-btn" style="background:none;border:none;font-size:14px;cursor:pointer;color:#fff;" onclick="cancelPhotoEdit()">취소</button>
        <div style="margin-left:auto;">
          <button class="btn btn-primary btn-sm" onclick="savePhotoEdit()">저장</button>
        </div>
      </div>
      <div style="flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;">
        <canvas id="photoEditCanvas"></canvas>
      </div>
      <div style="padding:8px 10px 14px;background:#111;">
        <div id="photoEditThicknessRow" style="display:flex;align-items:center;gap:8px;padding:0 6px 10px;">
          <span style="color:#fff;font-size:12px;flex-shrink:0;">굵기</span>
          <input type="range" id="photoEditThickness" min="4" max="40" value="14" oninput="onThicknessChange()" style="flex:1;">
        </div>
        <div style="display:flex;justify-content:space-around;">
          <button type="button" class="photo-tool-btn" data-tool="rotate" onclick="rotatePhotoEdit()"><i class="fa-solid fa-rotate-right"></i><span>회전</span></button>
          <button type="button" class="photo-tool-btn" data-tool="pen" onclick="selectPhotoTool('pen')"><i class="fa-solid fa-pencil"></i><span>펜</span></button>
          <button type="button" class="photo-tool-btn" data-tool="blur" onclick="selectPhotoTool('blur')"><i class="fa-solid fa-droplet"></i><span>블러</span></button>
          <button type="button" class="photo-tool-btn" data-tool="eraser" onclick="selectPhotoTool('eraser')"><i class="fa-solid fa-eraser"></i><span>지우개</span></button>
        </div>
      </div>
    </div>
  </div>

  <div id="scrollTopBtn" onclick="scrollActiveContainerToTop()"><i class="fa-solid fa-arrow-up"></i></div>'''
h = h.replace(old, new)
print("✅ [5/9] 사진 미리보기/편집 화면 마크업 추가 완료")

# 6) 사진 미리보기/편집 로직(JS) 삽입 - compressImageFile 함수 바로 뒤
old = '''    reader.readAsDataURL(file);
  });
}

function showMiniAlert(text, buttons){'''
assert old in h, "compressImageFile 함수 뒤 삽입 위치를 찾을 수 없습니다"
new = '''    reader.readAsDataURL(file);
  });
}

/* ===================== 0-40: 채팅 사진 전송 전 미리보기 + 편집 ===================== */
let photoPreviewMeta = null; // {isGroup, roomId, currentDataUrl}
let previewCanvas = null, previewCtx = null;
let peCanvas = null, peCtx = null;
let peOrigImg = null;       // 편집 중인 기준 이미지(회전 시 갱신됨)
let peStrokes = [];         // {tool:'pen'|'blur', thickness, color?, points:[{x,y}]}
let peTool = 'pen';
let peThickness = 14;
let peDrawing = false;
let peCurrentStroke = null;
let peBlurCanvas = null;    // 전체 블러 처리된 사본(블러 브러시가 여기서 페인트해옴)
let peDirty = false;

function openPhotoPreview(dataUrl, isGroup, roomId){
  photoPreviewMeta = {isGroup, roomId, currentDataUrl: dataUrl};
  const img = new Image();
  img.onload = ()=>{
    previewCanvas = document.getElementById('photoPreviewCanvas');
    const maxW = Math.min(window.innerWidth, 520), maxH = window.innerHeight * 0.62;
    const scale = Math.min(maxW / img.width, maxH / img.height, 1);
    previewCanvas.width = Math.round(img.width * scale);
    previewCanvas.height = Math.round(img.height * scale);
    previewCtx = previewCanvas.getContext('2d');
    previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);
  };
  img.src = dataUrl;
  document.getElementById('photoEditBar').classList.add('hidden');
  openFullScreen('photoPreviewScreen');
}
function closePhotoPreview(){
  closeFullScreen('photoPreviewScreen');
  photoPreviewMeta = null;
}
function sendPreviewedPhoto(){
  if (!photoPreviewMeta) return;
  const meta = photoPreviewMeta;
  closeFullScreen('photoPreviewScreen');
  photoPreviewMeta = null;
  const onResult = (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  };
  if (meta.isGroup) socket.emit('group:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
  else socket.emit('chat:send_image', {roomId: meta.roomId, image: meta.currentDataUrl}, onResult);
}

/* ---- 편집 모드 ---- */
function enterPhotoEditMode(){
  if (!photoPreviewMeta) return;
  const img = new Image();
  img.onload = ()=>{
    peOrigImg = img;
    peStrokes = [];
    peBlurCanvas = null;
    peDirty = false;
    peThickness = Number(document.getElementById('photoEditThickness').value) || 14;
    setupPeCanvasSize(img.width, img.height);
    renderPhotoEdit();
    document.getElementById('photoEditBar').classList.remove('hidden');
    selectPhotoTool('pen');
  };
  img.src = photoPreviewMeta.currentDataUrl;
}
function setupPeCanvasSize(w, h){
  const maxW = Math.min(window.innerWidth, 520), maxH = window.innerHeight * 0.55;
  const scale = Math.min(maxW / w, maxH / h, 1);
  const cw = Math.max(1, Math.round(w * scale)), ch = Math.max(1, Math.round(h * scale));
  peCanvas = document.getElementById('photoEditCanvas');
  peCanvas.width = cw; peCanvas.height = ch;
  peCtx = peCanvas.getContext('2d');
  if (!peCanvas.dataset.bound){
    peCanvas.addEventListener('mousedown', peDown);
    peCanvas.addEventListener('mousemove', peMove);
    window.addEventListener('mouseup', peUp);
    peCanvas.addEventListener('touchstart', peDown, {passive:false});
    peCanvas.addEventListener('touchmove', peMove, {passive:false});
    peCanvas.addEventListener('touchend', peUp);
    peCanvas.dataset.bound = '1';
  }
}
function selectPhotoTool(tool){
  peTool = tool;
  document.querySelectorAll('.photo-tool-btn').forEach(b=> b.classList.toggle('active', b.dataset.tool===tool));
  document.getElementById('photoEditThicknessRow').style.visibility = (tool==='rotate') ? 'hidden' : 'visible';
}
function onThicknessChange(){ peThickness = Number(document.getElementById('photoEditThickness').value) || 14; }

function getPeCanvasPoint(evt){
  const rect = peCanvas.getBoundingClientRect();
  const t = evt.touches && evt.touches[0];
  const clientX = t ? t.clientX : evt.clientX;
  const clientY = t ? t.clientY : evt.clientY;
  return {
    x: (clientX - rect.left) * (peCanvas.width / rect.width),
    y: (clientY - rect.top) * (peCanvas.height / rect.height)
  };
}
function peDown(evt){
  if (!peCtx || peTool === 'rotate') return;
  evt.preventDefault();
  peDrawing = true;
  const p = getPeCanvasPoint(evt);
  if (peTool === 'eraser'){ eraseAtPoint(p); return; }
  peCurrentStroke = { tool: peTool, thickness: peThickness, color: peTool==='pen' ? '#ff3040' : undefined, points: [p] };
  peStrokes.push(peCurrentStroke);
  peDirty = true;
  renderPhotoEdit();
}
function peMove(evt){
  if (!peDrawing) return;
  evt.preventDefault();
  const p = getPeCanvasPoint(evt);
  if (peTool === 'eraser'){ eraseAtPoint(p); return; }
  if (peCurrentStroke){ peCurrentStroke.points.push(p); renderPhotoEdit(); }
}
function peUp(){ peDrawing = false; peCurrentStroke = null; }

function eraseAtPoint(p){
  const r = Math.max(peThickness, 14);
  let changed = false;
  const newStrokes = [];
  peStrokes.forEach(s=>{
    let current = [];
    s.points.forEach(pt=>{
      const d = Math.hypot(pt.x - p.x, pt.y - p.y);
      if (d <= r){
        changed = true;
        if (current.length > 1) newStrokes.push({tool:s.tool, thickness:s.thickness, color:s.color, points: current});
        current = [];
      } else {
        current.push(pt);
      }
    });
    if (current.length > 1) newStrokes.push({tool:s.tool, thickness:s.thickness, color:s.color, points: current});
  });
  if (changed){ peStrokes = newStrokes; peDirty = true; renderPhotoEdit(); }
}

function rotatePhotoEdit(){
  if (!peOrigImg) return;
  const oldW = peCanvas.width, oldH = peCanvas.height;
  // 회전 시 기존에 그려둔 펜/블러 좌표도 새 방향에 맞게 함께 회전시킴(90도 시계방향)
  peStrokes.forEach(s=>{ s.points = s.points.map(pt=>({ x: oldH - pt.y, y: pt.x })); });
  const off = document.createElement('canvas');
  off.width = oldH; off.height = oldW;
  const octx = off.getContext('2d');
  octx.translate(oldH, 0);
  octx.rotate(Math.PI / 2);
  octx.drawImage(peOrigImg, 0, 0, oldW, oldH);
  const rotatedImg = new Image();
  rotatedImg.onload = ()=>{
    peOrigImg = rotatedImg;
    peCanvas.width = oldH; peCanvas.height = oldW;
    peBlurCanvas = null;
    peDirty = true;
    renderPhotoEdit();
  };
  rotatedImg.src = off.toDataURL('image/png');
}

function renderPhotoEdit(){
  if (!peCtx || !peOrigImg) return;
  peCtx.clearRect(0, 0, peCanvas.width, peCanvas.height);
  peCtx.drawImage(peOrigImg, 0, 0, peCanvas.width, peCanvas.height);
  if (peStrokes.some(s=>s.tool==='blur') && !peBlurCanvas){
    peBlurCanvas = document.createElement('canvas');
    peBlurCanvas.width = peCanvas.width; peBlurCanvas.height = peCanvas.height;
    const bctx = peBlurCanvas.getContext('2d');
    bctx.filter = 'blur(10px)';
    bctx.drawImage(peOrigImg, 0, 0, peCanvas.width, peCanvas.height);
  }
  peStrokes.forEach(s=>{
    if (!s.points.length) return;
    if (s.tool === 'blur') paintPeBlurStroke(s); else paintPePenStroke(s);
  });
}
function strokePathOn(ctx, points){
  ctx.beginPath();
  points.forEach((p,i)=> i===0 ? ctx.moveTo(p.x,p.y) : ctx.lineTo(p.x,p.y));
  if (points.length === 1){ ctx.moveTo(points[0].x - 0.01, points[0].y); ctx.lineTo(points[0].x + 0.01, points[0].y); }
  ctx.stroke();
}
function paintPePenStroke(s){
  peCtx.save();
  peCtx.lineCap = 'round'; peCtx.lineJoin = 'round';
  peCtx.strokeStyle = s.color || '#ff3040';
  peCtx.lineWidth = s.thickness;
  strokePathOn(peCtx, s.points);
  peCtx.restore();
}
function paintPeBlurStroke(s){
  if (!peBlurCanvas) return;
  const temp = document.createElement('canvas');
  temp.width = peCanvas.width; temp.height = peCanvas.height;
  const tctx = temp.getContext('2d');
  tctx.drawImage(peBlurCanvas, 0, 0);
  tctx.globalCompositeOperation = 'destination-in';
  tctx.lineCap = 'round'; tctx.lineJoin = 'round';
  tctx.lineWidth = s.thickness;
  tctx.strokeStyle = '#000';
  strokePathOn(tctx, s.points);
  peCtx.drawImage(temp, 0, 0);
}

function savePhotoEdit(){
  if (!peCanvas || !photoPreviewMeta) return;
  photoPreviewMeta.currentDataUrl = peCanvas.toDataURL('image/jpeg', 0.85);
  document.getElementById('photoEditBar').classList.add('hidden');
  const img = new Image();
  img.onload = ()=>{
    previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);
  };
  img.src = photoPreviewMeta.currentDataUrl;
}
function cancelPhotoEdit(){
  if (peDirty){
    showMiniAlert('편집한 내용을 저장하시겠습니까?', [
      {label:'아니오', primary:false, onClick:()=>{ document.getElementById('photoEditBar').classList.add('hidden'); }},
      {label:'예', primary:true, onClick:()=> savePhotoEdit()}
    ]);
  } else {
    document.getElementById('photoEditBar').classList.add('hidden');
  }
}

function showMiniAlert(text, buttons){'''
h = h.replace(old, new)
print("✅ [6/9] 사진 미리보기/편집 로직(JS) 추가 완료")

# 7) 단체채팅 이미지 업로드 - 즉시전송 → 미리보기 경유
old = '''async function handleGroupChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeGroupRoomId) return;
  let image;
  try {
    image = await compressImageFile(file);
  } catch (err) {
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  socket.emit('group:send_image', {roomId:activeGroupRoomId, image}, (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  });
  e.target.value = '';
}'''
assert old in h, "handleGroupChatImageUpload를 찾을 수 없습니다 (0-38 이후 코드 구조가 다를 수 있습니다)"
h = h.replace(old, '''async function handleGroupChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeGroupRoomId) return;
  let image;
  try {
    image = await compressImageFile(file);
  } catch (err) {
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  e.target.value = '';
  openPhotoPreview(image, true, activeGroupRoomId);
}''')

# 8) 1:1 채팅 이미지 업로드 - 즉시전송 → 미리보기 경유
old = '''async function handleChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeRoomId) return;
  let image;
  try {
    image = await compressImageFile(file);
  } catch (err) {
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  socket.emit('chat:send_image', {roomId:activeRoomId, image}, (res)=>{
    if (!res) { showMiniAlert('사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]); return; }
    if (res.blocked) showMiniAlert(res.message || '부적절한 사진으로 감지되어 전송할 수 없습니다.', [{label:'확인', primary:true}]);
    else if (!res.success) showMiniAlert(res.message || '사진 전송에 실패했어요. 잠시 후 다시 시도해주세요.', [{label:'확인', primary:true}]);
  });
  e.target.value = '';
}'''
assert old in h, "handleChatImageUpload를 찾을 수 없습니다 (0-38 이후 코드 구조가 다를 수 있습니다)"
h = h.replace(old, '''async function handleChatImageUpload(e){
  const file = e.target.files[0]; if(!file || !activeRoomId) return;
  let image;
  try {
    image = await compressImageFile(file);
  } catch (err) {
    console.error('사진 처리 실패:', err);
    showMiniAlert('이 사진은 불러올 수 없어요. 다른 사진으로 다시 시도해주세요.', [{label:'확인', primary:true}]);
    e.target.value = '';
    return;
  }
  e.target.value = '';
  openPhotoPreview(image, false, activeRoomId);
}''')
print("✅ [7/9], [8/9] 1:1/단체채팅 이미지 업로드를 미리보기 경유로 전환 완료")

with open(path_h, "w", encoding="utf-8") as f:
    f.write(h)
print("✅ [9/9] public/index.html 저장 완료")
print("0-39, 0-40 패치 전체 완료")