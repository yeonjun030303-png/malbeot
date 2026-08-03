path = "public/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """  if (editingPostId){
    socket.emit('posts:update', {id:editingPostId, content, photo:composePhotoBase64, logType:composeLogType}, (res)=>{
      if (res && res.success){
        closeComposeScreen(); loadCommunityPosts();
        if (currentPostId===editingPostId) refreshPostDetail();
        showMiniAlert('글을 수정하였습니다.', [{label:'확인', primary:true}]);
      } else {
        showMiniAlert('글 수정에 실패했습니다. 네트워크 상태를 확인하고 다시 시도해주세요.', [{label:'확인', primary:true}]);
      }
    });
    return;
  }
  socket.emit('posts:create', {content, photo:composePhotoBase64, logType:composeLogType}, (res)=>{
    if (res && res.success){
      currentUser.points = res.points; updateUserUI(); saveSession();
      closeComposeScreen(); loadCommunityPosts();
      if (res.earned) showMiniAlert('오늘 첫 글 작성으로 포인트 지급이 완료되었습니다. (쌀 50개)', [{label:'확인', primary:true}]);
    } else {
      showMiniAlert('글 등록에 실패했습니다. 네트워크 상태를 확인하고 다시 시도해주세요.', [{label:'확인', primary:true}]);
    }
  });
}"""

new = """  if (editingPostId){
    submitComposeUpdate(false);
    return;
  }
  submitComposeCreate(false);
}
function submitComposeUpdate(confirmed){
  const content = document.getElementById('composeTextarea').value.trim();
  socket.emit('posts:update', {id:editingPostId, content, photo:composePhotoBase64, logType:composeLogType, confirmed}, (res)=>{
    if (res && res.success){
      closeComposeScreen(); loadCommunityPosts();
      if (currentPostId===editingPostId) refreshPostDetail();
      showMiniAlert('글을 수정하였습니다.', [{label:'확인', primary:true}]);
    } else if (res && res.needsConfirm){
      showMiniAlert('부적절한 단어가 발견되었습니다. 게시 안되지만 그래도 변경하시겠습니까?', [
        {label:'취소', primary:false},
        {label:'확인', primary:true, onClick:()=>submitComposeUpdate(true)}
      ]);
    } else {
      showMiniAlert('글 수정에 실패했습니다. 네트워크 상태를 확인하고 다시 시도해주세요.', [{label:'확인', primary:true}]);
    }
  });
}
function submitComposeCreate(confirmed){
  const content = document.getElementById('composeTextarea').value.trim();
  socket.emit('posts:create', {content, photo:composePhotoBase64, logType:composeLogType, confirmed}, (res)=>{
    if (res && res.success){
      currentUser.points = res.points; updateUserUI(); saveSession();
      closeComposeScreen(); loadCommunityPosts();
      if (res.earned) showMiniAlert('오늘 첫 글 작성으로 포인트 지급이 완료되었습니다. (쌀 50개)', [{label:'확인', primary:true}]);
    } else if (res && res.needsConfirm){
      showMiniAlert('부적절한 단어가 발견되었습니다. 게시 안되지만 그래도 변경하시겠습니까?', [
        {label:'취소', primary:false},
        {label:'확인', primary:true, onClick:()=>submitComposeCreate(true)}
      ]);
    } else {
      showMiniAlert('글 등록에 실패했습니다. 네트워크 상태를 확인하고 다시 시도해주세요.', [{label:'확인', primary:true}]);
    }
  });
}"""

count = content.count(old)
if count != 1:
    print(f"경고: 매치 개수가 {count}개 입니다 (1개여야 정상). 수정하지 않았습니다.")
else:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("수정 완료!")