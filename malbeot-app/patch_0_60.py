# -*- coding: utf-8 -*-
# 0-60: 채팅목록 검색결과에 검색어 매칭 부분(닉네임/방이름/대화내용)을 파란색으로 강조 표시
import os

path = "public/index.html"
if not os.path.exists(path):
    print("❌ public/index.html 을 찾을 수 없습니다. malbeot-app 폴더 안에서 실행했는지 확인하세요. (현재 위치:", os.getcwd(), ")")
    raise SystemExit(1)

with open(path, encoding="utf-8") as f:
    content = f.read()

old = """      localGroupMatches.forEach(r=>{
        const meta = r.meta || {};
        const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
        wrap.innerHTML = `<div class="chat-row-fg">
          <div class="avatar-sm" style="display:flex;align-items:center;justify-content:center;background:var(--bg-secondary,#eee);"><i class="fa-solid fa-users"></i></div>
          <div class="chat-row-text"><div class="chat-row-nick">${escapeHtml(meta.title||'')}</div></div>
        </div>`;
        wrap.querySelector('.chat-row-fg').addEventListener('click', ()=>{ clearGroupSearch(); openGroupChatRoom(r.roomId); });
        resultBox.appendChild(wrap);
      });
      localDmMatches.forEach(r=>{
        const target = r.targetUser || {};
        const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
        wrap.innerHTML = `<div class="chat-row-fg">
          <span onclick="event.stopPropagation();openProfileDetailScreen('${target.id}')" style="cursor:pointer;display:inline-block;">${avatarHtmlFor(target,'avatar-sm')}</span>
          <div class="chat-row-text"><div class="chat-row-nick">${escapeHtml(target.nickname||'')}</div></div>
        </div>`;
        wrap.querySelector('.chat-row-fg').addEventListener('click', ()=>{ clearGroupSearch(); openChatModal(r.roomId, target, r.messages); });
        resultBox.appendChild(wrap);
      });"""

new = """      // 0-60: 검색어가 매칭된 부분(닉네임/방이름 또는 대화내용)을 파란색으로 강조 표시
      const findMatchSnippet = (r)=>{
        const m = (r.messages||[]).slice().reverse().find(m => m.type!=='image' && (m.text||'').toLowerCase().includes(qLower));
        return m ? m.text : '';
      };
      localGroupMatches.forEach(r=>{
        const meta = r.meta || {};
        const snippet = findMatchSnippet(r);
        const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
        wrap.innerHTML = `<div class="chat-row-fg">
          <div class="avatar-sm" style="display:flex;align-items:center;justify-content:center;background:var(--bg-secondary,#eee);"><i class="fa-solid fa-users"></i></div>
          <div class="chat-row-text">
            <div class="chat-row-nick">${highlightMatch(meta.title||'', q)}</div>
            ${snippet ? `<div class="chat-row-last">${highlightMatch(snippet, q)}</div>` : ''}
          </div>
        </div>`;
        wrap.querySelector('.chat-row-fg').addEventListener('click', ()=>{ clearGroupSearch(); openGroupChatRoom(r.roomId); });
        resultBox.appendChild(wrap);
      });
      localDmMatches.forEach(r=>{
        const target = r.targetUser || {};
        const snippet = findMatchSnippet(r);
        const wrap = document.createElement('div'); wrap.className='chat-row-wrap';
        wrap.innerHTML = `<div class="chat-row-fg">
          <span onclick="event.stopPropagation();openProfileDetailScreen('${target.id}')" style="cursor:pointer;display:inline-block;">${avatarHtmlFor(target,'avatar-sm')}</span>
          <div class="chat-row-text">
            <div class="chat-row-nick">${highlightMatch(target.nickname||'', q)}</div>
            ${snippet ? `<div class="chat-row-last">${highlightMatch(snippet, q)}</div>` : ''}
          </div>
        </div>`;
        wrap.querySelector('.chat-row-fg').addEventListener('click', ()=>{ clearGroupSearch(); openChatModal(r.roomId, target, r.messages); });
        resultBox.appendChild(wrap);
      });"""

if old not in content:
    print("❌ 패치 대상 코드를 찾지 못했습니다. 이미 적용됐거나 코드가 변경됐을 수 있습니다.")
    raise SystemExit(1)

content = content.replace(old, new)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 0-60 패치 적용 완료: 채팅목록 검색결과(닉네임/방이름/대화내용)에 파란색 강조 표시 반영됨")