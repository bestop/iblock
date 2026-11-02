const $=id=>document.getElementById(id)
const homeReturn='/'
const loginReturn='/account/'
$('account-back').href=homeReturn
let mode='login',challengeId='',verifyChallengeId=''
const resendUntil={auth:0,verify:0}
let challengeEmail=''
const normalizeEmail=value=>value.trim().toLowerCase()
function updateCountdowns(){for(const [key,id] of [['auth','send-code'],['verify','send-verify']]){const remaining=Math.max(0,Math.ceil((resendUntil[key]-Date.now())/1000)),button=$(id);if(button.dataset.sending==='true')continue;button.disabled=remaining>0;button.textContent=remaining?remaining+' 秒后重发':key==='auth'?'获取验证码':'发送邮箱验证码'}}
setInterval(updateCountdowns,1000)
export async function request(path,data) {
  const response=await fetch(path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,credentials:'same-origin'})
  const result=await response.json()
  if(!response.ok)throw new Error(result.error||'操作失败，请稍后重试。')
  return result
}
function entryMode(){const view=new URL(window.location.href).searchParams.get('view');return ['register','recover'].includes(view)?view:'login'}
function setMode(next,{updateHistory=true}={}) {
  if(next===mode)return
  const authPanel=$('auth')
  if(next==='recover'||mode==='recover'){authPanel.style.minHeight=''}
  else if(authPanel.getBoundingClientRect&&authPanel.style){
    const height=Math.ceil(authPanel.getBoundingClientRect().height)
    if(height>0)authPanel.style.minHeight=height+'px'
  }
  mode=next;challengeId='';$('email-code').value='';$('auth').dataset.mode=next;document.querySelector('.mode-switch').hidden=next==='recover';document.querySelector('.mode-switch').dataset.active=next
  document.querySelectorAll('.mode-switch button[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===next)))
  $('registration-contact').hidden=next!=='register'
  $('form-title').textContent={login:'欢迎回来',register:'注册账号',recover:'重置密码'}[next]
  $('auth-submit').textContent={login:'登录',register:'注册并激活',recover:'重置密码并登录'}[next]
  $('password-label').textContent=next==='recover'?'新密码':'密码'
  $('confirm-password-field').hidden=next!=='recover';$('confirm-password').required=next==='recover';$('confirm-password').value='';$('confirm-password').setCustomValidity('');$('confirm-password').removeAttribute('aria-invalid')
  $('password').autocomplete=next==='login'?'current-password':'new-password'
  $('password').placeholder=next==='recover'?'新密码（至少 10 个字符）':'密码（至少 10 个字符）'
  $('register-code-field').hidden=next!=='register';$('register-code').required=next==='register'
  $('email-code-input').hidden=next==='login';$('email-code').required=next!=='login'
  $('auth-message').textContent=''
  updateCountdowns()
  $('register-purchase').hidden=next!=='register'
  $('recover-mode').hidden=next!=='login'
  $('account-back-label').textContent='返回';
  const back=$('account-back');back.href=next==='recover'?loginReturn:homeReturn;back.setAttribute('aria-label',next==='recover'?'返回登录':'返回首页')
  const currentUrl=new URL(window.location.href)
  if(updateHistory&&next==='recover'&&currentUrl.searchParams.get('view')!=='recover'){currentUrl.searchParams.set('view','recover');history.pushState({hhxRecover:true},'',currentUrl)}
  else if(updateHistory&&next==='register'){currentUrl.searchParams.set('view','register');history.replaceState(null,'',currentUrl)}
  else if(updateHistory&&next==='login'&&currentUrl.searchParams.has('view')){currentUrl.searchParams.delete('view');history.replaceState(null,'',currentUrl)}
  document.querySelector('footer').hidden=true
  $('recover-mode').textContent=next==='login'?'忘记密码？':next==='register'?'已有账号？返回登录':'返回登录'
}
function render(data) {
  // This hint selects a loading layout only; permissions still come from /api/me.
  try{sessionStorage.setItem('hhxAccountLayout',data.user?'member':'auth')}catch{}
  if(data.user&&data.interactive&&data.user.role!=='admin'&&new URL(window.location.href).searchParams.get('view')!=='account') {
    window.location.replace('/learn/')
    return
  }
  document.body.classList.remove('account-pending','auth-pending')
  $('loading').hidden=true;$('auth').hidden=!!data.user;$('member').hidden=!data.user
  const admin=data.user?.role==='admin'
  document.body.classList.toggle('admin-account',admin)
  document.body.classList.toggle('member-account',!!data.user&&!admin)
  $('admin-home').hidden=!admin
  document.querySelector('.account-page .intro').hidden=!!data.user
  document.querySelector('footer').hidden=true
  if(!data.user){setMode(entryMode(),{updateHistory:false});return}
  $('member-email').textContent=data.user.email
  $('member-access-badge').hidden=admin||!data.interactive
  $('unlocked').hidden=admin||!data.interactive
  $('redeem-title').textContent=data.interactive?'兑换其他购买码':'兑换你的互动版'
  $('redeem-section').hidden=admin||!!data.interactive
  $('admin-link').hidden=true
  $('verify-notice').hidden=!!data.user.email_verified_at

}
document.querySelectorAll('.mode-switch button[data-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)))
$('recover-mode').addEventListener('click',()=>setMode(mode==='login'?'recover':'login'))
$('auth-form').addEventListener('submit',async event=>{
  event.preventDefault()
  $('email-code').value=$('email-code').value.replace(/[\s\u200b-\u200d\ufeff]/g,'').replace(/[０-９]/g,digit=>String(digit.charCodeAt(0)-0xff10))
  const fields=[['email','请输入有效的邮箱地址。'],['password','密码至少需要 10 个字符。'],...(mode==='register'?[['register-code','请填写购买订单编号或兑换码。']]:[]),...(mode!=='login'?[['email-code','请输入邮件中的 6 位验证码。']]:[])]
  for(const [id,message] of fields){if(!$(id).checkValidity()){$('auth-message').textContent=message;$(id).focus();return}}
  if(mode==='recover'&&$('password').value!==$('confirm-password').value){$('auth-message').textContent='两次输入的密码不一致，请重新确认。';$('confirm-password').setAttribute('aria-invalid','true');$('confirm-password').focus();return}
  const button=$('auth-submit');button.disabled=true;$('auth-form').setAttribute('aria-busy','true');$('auth-message').textContent=''
  let navigating=false
  button.classList.add('is-loading');button.textContent=mode==='register'?'正在注册并激活…':'正在校验…'
  try {
    const data=await request('/api/'+mode,{email:$('email').value,password:$('password').value,emailCode:$('email-code').value,challengeId,code:mode==='register'?$('register-code').value:undefined})
    $('password').value='';$('confirm-password').value='';$('email-code').value='';challengeId=''
    if(data.interactive&&data.user?.role!=='admin'){navigating=true;button.textContent='正在进入图鉴…';window.location.replace('/learn/')}
    else render(data)
  }
  catch(error){$('auth-message').textContent=error.message}
  finally{if(!navigating){button.disabled=false;button.classList.remove('is-loading');$('auth-form').removeAttribute('aria-busy');button.textContent={login:'登录',register:'注册并激活',recover:'重置密码并登录'}[mode]}}
})
$('redeem-form').addEventListener('submit',async event=>{
  event.preventDefault()
  const button=$('redeem-submit'),form=$('redeem-form'),originalLabel=button.textContent
  if(button.disabled)return
  button.disabled=true;button.classList.add('is-loading');button.setAttribute('aria-busy','true');form.setAttribute('aria-busy','true');button.textContent='正在激活…';$('redeem-message').textContent=''
  try{
    await request('/api/redeem',{code:$('code').value})
    button.textContent='正在校验权限…'
    const data=await request('/api/me')
    if(!data.user||!data.interactive)throw new Error('权限暂未确认，请重试或刷新页面。')
    button.textContent='正在进入图鉴…'
    window.location.replace('/learn/')
  }catch(error){
    $('redeem-message').textContent=error.message
    button.disabled=false;button.classList.remove('is-loading');button.removeAttribute('aria-busy');form.removeAttribute('aria-busy');button.textContent=originalLabel
  }
})
$('logout').addEventListener('click',async()=>{
  try{await request('/api/logout',{});render({user:null});setMode('login')}
  catch(error){$('redeem-message').textContent=error.message}
})
$('email').addEventListener('input',()=>{if(challengeEmail&&normalizeEmail($('email').value)!==challengeEmail){challengeId='';$('email-code').value='';challengeEmail='';resendUntil.auth=0;$('auth-message').textContent='邮箱已更改，请重新获取验证码。';updateCountdowns()}})
$('send-code').addEventListener('click',async()=>{
  if(!$('email').reportValidity()||(mode==='register'&&!$('register-code').reportValidity()))return
  const requestedEmail=normalizeEmail($('email').value),requestedMode=mode
  const button=$('send-code');button.disabled=true;button.dataset.sending='true'
  try{const data=await request('/api/email-code',{email:requestedEmail,purpose:requestedMode,code:requestedMode==='register'?$('register-code').value:undefined});if(normalizeEmail($('email').value)!==requestedEmail||mode!==requestedMode)return;challengeId=data.challengeId||'';challengeEmail=requestedEmail;$('auth-message').textContent=data.message;if(data.sent!==false)resendUntil.auth=Date.now()+60000}
  catch(e){if(normalizeEmail($('email').value)===requestedEmail&&mode===requestedMode)$('auth-message').textContent=e.message}
  finally{button.dataset.sending='false';updateCountdowns()}
})
$('send-verify').addEventListener('click',async()=>{
  const button=$('send-verify');button.disabled=true;button.dataset.sending='true'
  try{const data=await request('/api/email-code',{email:$('member-email').textContent,purpose:'verify'});verifyChallengeId=data.challengeId;$('verify-status').textContent=data.message;if(data.sent!==false)resendUntil.verify=Date.now()+60000}
  catch(e){$('verify-status').textContent=e.message}
  finally{button.dataset.sending='false';updateCountdowns()}
})
$('verify-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=$('verify-form').querySelector('button');button.disabled=true
  try{await request('/api/verify-email',{challengeId:verifyChallengeId,emailCode:$('verify-code').value});verifyChallengeId='';$('verify-code').value='';render(await request('/api/me'))}
  catch(e){$('verify-status').textContent=e.message}
  finally{button.disabled=false}
})
request('/api/me').then(render).catch(error=>{$('loading').textContent=error.message+' 请刷新页面重试。'})
// Safari may restore the account page from its back/forward cache without
// running this module again. Recheck access instead of showing a stale panel.
window.addEventListener('pageshow',event=>{
  if(event.persisted)request('/api/me').then(render).catch(error=>{$('loading').textContent=error.message+' 请刷新页面重试。'})
})

// Help entry points share one accessible, dismissible dialog.
const contactWechat=$('contact-wechat-id').textContent.trim()||'kerh4-'
$('contact-wechat-id').textContent=contactWechat
for(const button of document.querySelectorAll('[data-account-help]')){
  if(button.dataset.accountHelp==='contact')button.hidden=!contactWechat||(button.id==='registration-contact'&&mode!=='register')
  button.addEventListener('click',()=>{
    const example=button.dataset.accountHelp==='example',dialog=$('account-help-dialog')
    $('account-help-title').textContent=example?'订单编号在哪里？':'联系我们'
    $('order-example').hidden=!example;$('account-contact').hidden=example;$('copy-wechat').hidden=example
    $('contact-message').textContent=''
    dialog.addEventListener('close',()=>{if(button.isConnected)button.focus({preventScroll:true})},{once:true})
    dialog.showModal()
  })
}
$('copy-wechat').addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText(contactWechat);$('contact-message').classList.add('success');$('contact-message').textContent='微信号已复制，请打开微信搜索添加。'}
  catch{$('contact-message').classList.remove('success');$('contact-message').textContent='请长按上方微信号复制。'}
})

for(const id of ['password','confirm-password'])$(id).addEventListener('input',()=>{if(mode==='recover'){$('confirm-password').removeAttribute('aria-invalid');$('auth-message').textContent=''}})

$('account-back').addEventListener('click',event=>{if(mode!=='recover')return;event.preventDefault();if(history.state?.hhxRecover)history.back();else setMode('login')})
window.addEventListener('popstate',()=>{if(!$('auth').hidden)setMode(entryMode(),{updateHistory:false})})
