import {createFavoritesClient,createAuthenticatedFavoritesRequest} from '../account-favorites.js';
const types=['words','readings','phrases'],prefix='hhx-learning-',listeners=new Set();
const kind=id=>id.startsWith('reading-')?'readings':id.startsWith('phrase-')?'phrases':'words';
let client,ready=false,guest=false;
const guestKey=t=>prefix+'guest-'+t+'-saved';
const safeRead=key=>{try{const a=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(a)?a.filter(x=>typeof x==='string'):[]}catch{return []}};
const read=t=>guest?safeRead(guestKey(t)):client?client.read().filter(id=>kind(id)===t):[];
const notify=()=>{for(const f of listeners)f();window.dispatchEvent(new Event('hhx-live-collection-change'));window.dispatchEvent(new Event('hhx-favorites-state'));window.dispatchEvent(new StorageEvent('storage',{key:null}));};
let notice;
function status(message){
 if(!message){notice?.remove();notice=null;return}
 if(!notice){notice=document.createElement('div');notice.setAttribute('role','status');notice.style.cssText='position:fixed;z-index:9999;bottom:20px;left:50%;transform:translateX(-50%);max-width:calc(100% - 32px);padding:12px 16px;background:white;color:#333;border:1px solid #ddd;border-radius:12px;font:14px system-ui;display:flex;gap:12px;align-items:center';document.body.append(notice)}
 notice.replaceChildren(document.createTextNode(message));const retry=document.createElement('button');retry.type='button';retry.textContent='重试';retry.style.cssText='border:0;background:transparent;color:#287f70;white-space:nowrap;font:inherit';retry.onclick=()=>retryPending();notice.append(retry);
}
const queueKey=()=>prefix+'pending-favorites:'+client.getUserId();
function operations(){try{return JSON.parse(localStorage.getItem(queueKey())||'{}')}catch{return {}}}
function storeOperations(ops){try{localStorage.setItem(queueKey(),JSON.stringify(ops))}catch{status('此浏览器无法保存待同步收藏，请保持页面打开并重试。')}}
function clearOperations(){try{localStorage.removeItem(queueKey())}catch{}}
function desiredWithPending(){const next=new Set(client.read());for(const [id,saved]of Object.entries(operations()))if(saved)next.add(id);else next.delete(id);return [...next]}
async function rawRequestOnce(path,data){const response=await fetch(!data&&path==='/api/favorites'?path+'?scope=learning':path,{method:data?'POST':'GET',signal:globalThis.AbortSignal?.timeout?.(12000),credentials:'same-origin',cache:'no-store',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined});const out=await response.json();if(!response.ok)throw Object.assign(new Error(out.error||'收藏同步暂时不可用'),{status:response.status});return out}
async function rawRequest(path,data){
 for(let attempt=0;attempt<2;attempt++){
  try{return await rawRequestOnce(path,data)}catch(error){
   // Read-only requests can retry once; writes keep their existing pending queue.
   if(data||attempt||error.status&&![408,425,429,500,502,503,504].includes(error.status))throw error;
   await new Promise(resolve=>setTimeout(resolve,250));
  }
 }
}

function write(t,next){
 if(!ready||!types.includes(t))return;
 next=[...new Set(next.filter(id=>typeof id==='string'&&kind(id)===t))];
 if(guest){const old=read(t);if(old.length===next.length&&old.every(id=>next.includes(id)))return;try{localStorage.setItem(guestKey(t),JSON.stringify(next))}catch{}notify();return}
 const before=new Set(read(t)),after=new Set(next);if(before.size===after.size&&[...before].every(id=>after.has(id)))return;const ops=operations();for(const id of new Set([...before,...after]))if(before.has(id)!==after.has(id))ops[id]=after.has(id);storeOperations(ops);
 client.write(desiredWithPending());notify();
}
async function retryPending(){if(!ready){location.reload();return}if(!client||guest)return;client.write(desiredWithPending());await client.flush();if(!client.hasPending())await client.sync()}
window.hhxLearningFavorites={read,write,isReady:()=>ready,handles:key=>types.some(t=>key===prefix+t+'-saved'),readKey:key=>read(types.find(t=>key===prefix+t+'-saved')),writeKey:(key,ids)=>write(types.find(t=>key===prefix+t+'-saved'),ids),subscribe:f=>{listeners.add(f);return()=>listeners.delete(f)}};
export const learningFavoritesReady=(async()=>{
 client=createFavoritesClient({request:createAuthenticatedFavoritesRequest(rawRequest),onChange:()=>{if(ready)notify()},onStatus:s=>{if(s==='error')status('收藏暂未同步，联网后可重试。');else if(s==='saved')status('')},onAuthError:()=>{ready=false;status('账号状态已变化，请重新打开学习页面。')},onSaved:()=>{clearOperations();try{const channel=new BroadcastChannel('hhx-account-favorites');channel.postMessage({userId:client.getUserId()});channel.close()}catch{}}});
 try{await client.sync();ready=true;if(Object.keys(operations()).length){client.write(desiredWithPending());await client.flush()}}
 catch(error){if([401,403].includes(error.status)){guest=true;ready=true}else{status('暂时无法读取账号收藏，请检查网络后重试。');throw error}}
 notify();return window.hhxLearningFavorites;
})();
learningFavoritesReady.catch(()=>{});
async function refresh(){if(document.visibilityState!=='visible'||!ready||guest)return;await retryPending().catch(()=>{});}
window.addEventListener('pageshow',event=>{if(event.persisted)void refresh()});document.addEventListener('visibilitychange',()=>void refresh());window.addEventListener('online',()=>void refresh());
try{const channel=new BroadcastChannel('hhx-account-favorites');channel.onmessage=event=>{if(client&&event.data?.userId===client.getUserId())void refresh()}}catch{}
// Persist operations before writes; native back/close can replay only this account's queue.
document.addEventListener('click',event=>{const link=event.target.closest?.('a[href]');if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.target==='_blank'||!client||!ready||guest||!client.hasPending())return;const to=new URL(link.href,location.href);if(to.origin!==location.origin)return;event.preventDefault();void client.flush().then(()=>{if(!client.hasPending())location.assign(to.href);else status('收藏暂未同步，请重试后返回。')})},true);
