// Safari may retain :focus-visible after programmatic focus restoration.
// Show account-trigger focus only for actual keyboard navigation.
export function installFocusModality(){
 if(document.documentElement.hasAttribute('data-ui-input'))return;
 document.documentElement.dataset.uiInput='pointer';
 window.addEventListener('pointerdown',()=>{document.documentElement.dataset.uiInput='pointer'},{capture:true,passive:true});
 window.addEventListener('keydown',e=>{if(['Tab','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Escape'].includes(e.key))document.documentElement.dataset.uiInput='keyboard'},{capture:true});
}
