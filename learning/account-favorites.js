export function createAuthenticatedFavoritesRequest(rawRequest){
  let checking=null
  const temporary=()=>Object.assign(new Error('账号状态暂时无法确认，请稍后重试。'),{status:503})
  return async function request(path,data){
    try{return await rawRequest(path,data)}catch(error){
      if(![401,403].includes(error.status))throw error
      // A failed favorites request alone is not proof that login expired.
      if(!checking){
        checking=Promise.resolve().then(()=>rawRequest('/api/me')).finally(()=>{checking=null})
      }
      let account
      try{account=await checking}catch{throw temporary()}
      if(account?.user===null)throw Object.assign(new Error('请重新登录。'),{status:401})
      if(typeof account?.user?.id!=='string'||typeof account.interactive!=='boolean')throw temporary()
      if(!account.interactive)throw Object.assign(new Error('当前账号的图鉴权限不可用。'),{status:403})
      try{return await rawRequest(path,data)}catch(retryError){
        // Keep the page and queued writes when the independent check succeeded.
        if([401,403].includes(retryError.status))throw temporary()
        throw retryError
      }
    }
  }
}

export function createFavoritesClient({request,onChange=()=>{},onStatus=()=>{},onAuthError=()=>{},onSaved=()=>{}}){
  let userId='',words=[],confirmed=new Set(),sequence=0,running=null,stopped=false
  const pending=new Map()
  async function sync(){
    if(pending.size||running||stopped)return
    const revision=sequence
    const data=await request('/api/favorites')
    if(userId&&data.userId!==userId){stop();onAuthError();throw new Error('账号已切换，请重新登录。')}
    if(pending.size||sequence!==revision)return
    userId=data.userId;confirmed=new Set(data.words);words=[...confirmed];onChange()
  }
  function stop(){stopped=true;pending.clear();confirmed.clear();words=[];onChange()}
  function write(next){
    if(stopped||!userId)return
    next=[...new Set(next)]
    const previous=new Set(words),desired=new Set(next)
    let changed=false
    for(const id of new Set([...previous,...desired]))if(previous.has(id)!==desired.has(id)){changed=true;pending.set(id,{saved:desired.has(id),version:++sequence})}
    if(!changed)return
    words=next
    if(pending.size)void flush()
  }
  function flush(){
    if(running)return running
    if(stopped||!pending.size)return Promise.resolve()
    onStatus('saving')
    running=(async()=>{
      try{
        while(pending.size&&!stopped){
          const [wordId,operation]=pending.entries().next().value
          await request('/api/favorites',{userId,wordId,saved:operation.saved})
          if(operation.saved)confirmed.add(wordId);else confirmed.delete(wordId)
          if(pending.get(wordId)?.version===operation.version)pending.delete(wordId)
        }
        if(!stopped){words=[...confirmed];onChange();onStatus('saved');onSaved()}
      }catch(error){
        if([401,403,409].includes(error.status)){stop();onAuthError()}
        else {words=[...confirmed];onChange();onStatus('error')}
      }finally{running=null}
    })()
    return running
  }
  return {sync,write,flush,read:()=>[...words],hasPending:()=>!!pending.size,getUserId:()=>userId}
}

export async function startAccountFavorites(){
  const status=document.createElement('div')
  status.setAttribute('role','status');status.setAttribute('aria-live','polite');status.hidden=true
  Object.assign(status.style,{position:'fixed',bottom:'20px',left:'50%',transform:'translateX(-50%)',zIndex:'1000',width:'max-content',maxWidth:'calc(100% - 32px)',padding:'12px 16px',borderRadius:'12px',background:'#fff',color:'#242424',boxShadow:'0 4px 24px #0002',font:'14px system-ui',display:'none',alignItems:'center',gap:'12px'})
  const copy=document.createElement('span')
  status.append(copy);document.body.append(status)
  let hideTimer,client,channel,ready=false,navigating=false
  const notify=()=>window.dispatchEvent(new StorageEvent('storage',{key:'word-atlas-saved'}))
  const redirect=()=>{if(!navigating){navigating=true;window.location.assign('/account/')}}
  async function rawRequest(path,data){
    const response=await fetch(path,{method:data?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined})
    const result=await response.json()
    if(!response.ok){const error=new Error(result.error||'收藏同步失败');error.status=response.status;throw error}
    return result
  }
  const request=createAuthenticatedFavoritesRequest(rawRequest)
  function show(state){
    if(state!=='error'){
      clearTimeout(hideTimer);status.hidden=true;status.style.display='none'
      return
    }
    clearTimeout(hideTimer);status.hidden=false;status.style.display='flex'
    copy.textContent={saving:'正在同步收藏…',saved:'收藏已同步',error:'收藏失败，请重试',loading:'正在加载账号收藏…'}[state]
    if(state==='saved'||state==='error')hideTimer=setTimeout(()=>{status.hidden=true;status.style.display='none'},state==='error'?3500:1200)
  }
  client=createFavoritesClient({request,onChange:notify,onStatus:show,onAuthError:redirect,onSaved:()=>channel?.postMessage({userId:client.getUserId()})})
  // Install synchronously before mounting. Never seed an account with local
  // favorites or allow initial empty React state to overwrite cloud favorites.
  window.hhxAccountFavorites={...client,isReady:()=>ready}
  async function initialize(){
    try{await client.sync();ready=true;window.dispatchEvent(new Event('hhx-favorites-state'));status.hidden=true;status.style.display='none';return true}
    catch(error){if([401,403,409].includes(error.status)){redirect();return true}show('error');return false}
  }
  while(!await initialize())await new Promise(resolve=>setTimeout(resolve,5000))
  if(navigating)return
  try{channel=new BroadcastChannel('hhx-account-favorites');channel.onmessage=event=>{if(event.data?.userId===client.getUserId())refresh()}}catch{}
  async function refresh(){try{await client.sync()}catch(error){if([401,403,409].includes(error.status))redirect()}}
  window.addEventListener('focus',refresh)
  window.addEventListener('online',()=>client.hasPending()?client.flush():refresh())
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')refresh()})
  window.addEventListener('beforeunload',event=>{if(client.hasPending()){event.preventDefault();event.returnValue=''}})
}
