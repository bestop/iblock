// iPad WebKit can retain the previous page scale after rotating a form page.
// Constrain scale only while orientation settles, then restore pinch zoom.
const viewport=document.querySelector('meta[name="viewport"]')
const touchApple=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1)
if(viewport&&touchApple){
 const normal='width=device-width,initial-scale=1,minimum-scale=1,viewport-fit=cover'
 let restoreTimer
 function restoreScale(){
  clearTimeout(restoreTimer)
  viewport.setAttribute('content',normal+',maximum-scale=1')
  restoreTimer=setTimeout(()=>viewport.setAttribute('content',normal),1000)
 }
 window.addEventListener('orientationchange',restoreScale)
 screen.orientation?.addEventListener('change',restoreScale)
 window.addEventListener('pagehide',()=>{clearTimeout(restoreTimer);viewport.setAttribute('content',normal)})
}
