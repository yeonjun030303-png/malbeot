import re

path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_desc = '''닉네임으로 유저를 검색해 골드/플래티넘을 결제 없이 즉시 지급하거나 회수할 수 있어요(테스트·CS 대응용).'''
new_desc = '''닉네임으로 유저를 검색해 기본/골드/플래티넘 등급을 결제 없이 바로 설정할 수 있어요(테스트·CS 대응용).'''
assert content.count(old_desc) == 1, f"desc count={content.count(old_desc)}"
content = content.replace(old_desc, new_desc, 1)

old_block = '''    box.innerHTML = res.users.map(u=>{
      const sub = u.subscription;
      const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now();
      const statusText = active
        ? `${sub.tier==='platinum'?'플래티넘':'골드'} 구독 중 · ${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지`
        : '구독 없음';
      return `
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b>${escapeHtml(u.nickname)}</b>
          <span style="font-size:11px;color:${active?'var(--primary)':'var(--text-muted)'};">${statusText}</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','gold',14)">골드 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','gold',365)">골드 1년</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','platinum',14)">플래 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','platinum',365)">플래 1년</button>
          ${active?`<button class="btn btn-sm" style="background:var(--danger,#ef4444);color:#fff;" onclick="revokeAdminSubscription('${u.id}')">회수</button>`:''}
        </div>
      </div>`;
    }).join('');
  });
}'''

new_block = '''    box.innerHTML = res.users.map(u=>{
      const sub = u.subscription;
      const active = sub && sub.tier && sub.expiresAt && sub.expiresAt > Date.now();
      const curTier = active ? sub.tier : 'basic';
      const statusText = active
        ? `${sub.tier==='platinum'?'플래티넘':'골드'} 구독 중 · ${new Date(sub.expiresAt).toLocaleDateString('ko-KR')}까지`
        : '기본(구독 없음)';
      const btnStyle = (on)=> on
        ? 'background:var(--primary);color:#fff;border-color:var(--primary);'
        : 'background:var(--bg-input);color:var(--text-main);';
      return `
      <div class="settings-list-item" style="flex-direction:column;align-items:stretch;cursor:default;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b>${escapeHtml(u.nickname)}</b>
          <span style="font-size:11px;color:${active?'var(--primary)':'var(--text-muted)'};">${statusText}</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
          <button class="btn btn-sm" style="${btnStyle(curTier==='basic')}" onclick="revokeAdminSubscription('${u.id}')">기본</button>
          <button class="btn btn-sm" style="${btnStyle(curTier==='gold')}" onclick="grantAdminSubscription('${u.id}','gold',14)">골드 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','gold',365)">골드 1년</button>
          <button class="btn btn-sm" style="${btnStyle(curTier==='platinum')}" onclick="grantAdminSubscription('${u.id}','platinum',14)">플래 14일</button>
          <button class="btn btn-secondary btn-sm" onclick="grantAdminSubscription('${u.id}','platinum',365)">플래 1년</button>
        </div>
      </div>`;
    }).join('');
  });
}'''

assert content.count(old_block) == 1, f"block count={content.count(old_block)}"
content = content.replace(old_block, new_block, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 0-23 패치 적용 완료: 관리자 구독관리 탭에 기본/골드/플래티넘 등급 버튼 통일 표시")