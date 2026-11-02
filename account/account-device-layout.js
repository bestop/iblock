// Account layout follows device direction, not the keyboard-reduced viewport.
// Soft keyboards resize the viewport without changing the device orientation.
const root=document.documentElement
const apple=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1)
function syncAccountOrientation(){
 const angle=window.orientation
 const native=screen.orientation?.type
 const android=/Android/i.test(navigator.userAgent)
 const direction=android&&/^(landscape|portrait)-/.test(native||'')?native.split('-')[0]:apple&&typeof angle==='number'?(Math.abs(angle)%180===90?'landscape':'portrait'):apple&&native?native.split('-')[0]:window.innerWidth>window.innerHeight?'landscape':'portrait'
 root.dataset.accountOrientation=direction
}
syncAccountOrientation()
window.addEventListener('orientationchange',syncAccountOrientation)
screen.orientation?.addEventListener('change',syncAccountOrientation)
window.addEventListener('resize',()=>{
 if(document.activeElement?.matches('input,textarea,select,[contenteditable="true"]'))return
 syncAccountOrientation()
})
window.addEventListener('pageshow',syncAccountOrientation)
