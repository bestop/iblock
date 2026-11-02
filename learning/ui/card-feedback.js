// Delegated pointer handling also supports cards rendered after startup.
const selector='a.topic,a.list-card,a.continue,a.word-result-card,button.category-drawer-card';
let pressed=null,origin=null;
function reset(){pressed?.removeAttribute('data-ui-pressed');pressed=null;origin=null}
document.addEventListener('pointerdown',event=>{
 reset();if(!event.isPrimary||event.button!==0)return;
 const card=event.target.closest?.(selector);
 if(!card||card.matches(':disabled,[aria-disabled="true"]'))return;
 pressed=card;origin={id:event.pointerId,x:event.clientX,y:event.clientY};card.setAttribute('data-ui-pressed','');
},{passive:true});
document.addEventListener('pointermove',event=>{if(origin&&event.pointerId===origin.id&&Math.hypot(event.clientX-origin.x,event.clientY-origin.y)>8)reset()},{passive:true});
for(const type of ['pointerup','pointercancel','dragstart','scroll'])document.addEventListener(type,reset,{passive:true,capture:true});
window.addEventListener('blur',reset);window.addEventListener('pagehide',reset);
document.addEventListener('visibilitychange',reset);
document.addEventListener('keydown',event=>{if(event.repeat||!['Enter',' '].includes(event.key))return;const card=event.target.closest?.(selector);if(card&&!card.matches(':disabled,[aria-disabled="true"]')){reset();pressed=card;card.setAttribute('data-ui-pressed','')}});
document.addEventListener('keyup',reset);document.addEventListener('focusout',reset);
