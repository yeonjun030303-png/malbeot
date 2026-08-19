path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

patches = []

# 1) CSS: 색상 스와치 active 표시
patches.append((
    """.photo-tool-btn.active{color:var(--primary);background:rgba(255,255,255,.14);}""",
    """.photo-tool-btn.active{color:var(--primary);background:rgba(255,255,255,.14);}
.pe-color-swatch.active{border-color:#fff !important;box-shadow:0 0 0 2px rgba(255,255,255,.5);}"""
))

# 2) HTML: 색상 선택 행 추가
patches.append((
    """        <div id="photoEditThicknessRow" style="display:flex;align-items:center;gap:8px;padding:0 6px 10px;">
          <span style="color:#fff;font-size:12px;flex-shrink:0;">굵기</span>
          <input type="range" id="photoEditThickness" min="4" max="40" value="14" oninput="onThicknessChange()" style="flex:1;">
        </div>
        <div style="display:flex;justify-content:space-around;">""",
    """        <div id="photoEditColorRow" style="display:flex;align-items:center;gap:8px;padding:0 6px 10px;">
          <span style="color:#fff;font-size:12px;flex-shrink:0;">색깔</span>
          <div style="display:flex;gap:8px;flex:1;overflow-x:auto;">
            <div class="pe-color-swatch active" data-color="#ff3040" onclick="selectPeColor('#ff3040')" style="width:24px;height:24px;border-radius:50%;background:#ff3040;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
            <div class="pe-color-swatch" data-color="#ff9f1c" onclick="selectPeColor('#ff9f1c')" style="width:24px;height:24px;border-radius:50%;background:#ff9f1c;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
            <div class="pe-color-swatch" data-color="#ffd60a" onclick="selectPeColor('#ffd60a')" style="width:24px;height:24px;border-radius:50%;background:#ffd60a;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
            <div class="pe-color-swatch" data-color="#2ec4b6" onclick="selectPeColor('#2ec4b6')" style="width:24px;height:24px;border-radius:50%;background:#2ec4b6;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
            <div class="pe-color-swatch" data-color="#3a86ff" onclick="selectPeColor('#3a86ff')" style="width:24px;height:24px;border-radius:50%;background:#3a86ff;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
            <div class="pe-color-swatch" data-color="#8338ec" onclick="selectPeColor('#8338ec')" style="width:24px;height:24px;border-radius:50%;background:#8338ec;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
            <div class="pe-color-swatch" data-color="#ff006e" onclick="selectPeColor('#ff006e')" style="width:24px;height:24px;border-radius:50%;background:#ff006e;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
            <div class="pe-color-swatch" data-color="#ffffff" onclick="selectPeColor('#ffffff')" style="width:24px;height:24px;border-radius:50%;background:#ffffff;flex-shrink:0;cursor:pointer;border:2px solid #999;"></div>
            <div class="pe-color-swatch" data-color="#000000" onclick="selectPeColor('#000000')" style="width:24px;height:24px;border-radius:50%;background:#000000;flex-shrink:0;cursor:pointer;border:2px solid transparent;"></div>
          </div>
        </div>
        <div id="photoEditThicknessRow" style="display:flex;align-items:center;gap:8px;padding:0 6px 10px;">
          <span style="color:#fff;font-size:12px;flex-shrink:0;">굵기</span>
          <input type="range" id="photoEditThickness" min="4" max="40" value="14" oninput="onThicknessChange()" style="flex:1;">
        </div>
        <div style="display:flex;justify-content:space-around;">"""
))

# 3) JS 변수 선언
patches.append((
    """let peTool = 'pen';
let peThickness = 14;""",
    """let peTool = 'pen';
let peColor = '#ff3040';
let peThickness = 14;"""
))

# 4) 편집모드 진입시 초기화
patches.append((
    """    peStrokes = [];
    peBlurCanvas = null;
    peDirty = false;
    peThickness = Number(document.getElementById('photoEditThickness').value) || 14;""",
    """    peStrokes = [];
    peBlurCanvas = null;
    peDirty = false;
    peColor = '#ff3040';
    document.querySelectorAll('.pe-color-swatch').forEach(el=> el.classList.toggle('active', el.dataset.color==='#ff3040'));
    peThickness = Number(document.getElementById('photoEditThickness').value) || 14;"""
))

# 5) selectPhotoTool 함수 + selectPeColor 함수 추가
patches.append((
    """function selectPhotoTool(tool){
  peTool = tool;
  document.querySelectorAll('.photo-tool-btn').forEach(b=> b.classList.toggle('active', b.dataset.tool===tool));
  document.getElementById('photoEditThicknessRow').style.visibility = (tool==='rotate') ? 'hidden' : 'visible';
}
function onThicknessChange(){ peThickness = Number(document.getElementById('photoEditThickness').value) || 14; }""",
    """function selectPhotoTool(tool){
  peTool = tool;
  document.querySelectorAll('.photo-tool-btn').forEach(b=> b.classList.toggle('active', b.dataset.tool===tool));
  document.getElementById('photoEditThicknessRow').style.visibility = (tool==='rotate') ? 'hidden' : 'visible';
  document.getElementById('photoEditColorRow').style.display = (tool==='pen') ? 'flex' : 'none';
}
function selectPeColor(color){
  peColor = color;
  document.querySelectorAll('.pe-color-swatch').forEach(el=> el.classList.toggle('active', el.dataset.color===color));
}
function onThicknessChange(){ peThickness = Number(document.getElementById('photoEditThickness').value) || 14; }"""
))

# 6) 펜 스트로크 색상 반영
patches.append((
    """  peCurrentStroke = { tool: peTool, thickness: peThickness, color: peTool==='pen' ? '#ff3040' : undefined, points: [p] };""",
    """  peCurrentStroke = { tool: peTool, thickness: peThickness, color: peTool==='pen' ? peColor : undefined, points: [p] };"""
))

fail = False
for i, (old, new) in enumerate(patches, 1):
    if old not in content:
        print(f"❌ {i}번 패치 매치 실패")
        fail = True
        continue
    content = content.replace(old, new, 1)
    print(f"✅ {i}번 패치 적용")

if not fail:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ 0-44 패치 완료: 펜 색깔 다양화(9가지) 적용됨")
else:
    print("⚠️ 일부 패치 실패 - 저장하지 않음")