// Explicit diagnostic link only; no analytics, storage, network or account data.
if(new URLSearchParams(location.search).has('viewport-check')){
 const panel=document.createElement('aside');panel.setAttribute('aria-label','页面缩放诊断');panel.style.cssText='position:fixed;bottom:8px;left:8px;right:8px;z-index:1000;padding:10px 12px;background:#fff;color:#222;border:1px solid #bbb;border-radius:8px;font:13px/1.5 monospace;pointer-events:none;white-space:pre-wrap';document.body.append(panel)
 let previous='—',lastOrientation=screen.orientation?.type||'unknown'
 function snapshot(){const v=window.visualViewport;return `scale=${v?.scale?.toFixed(3)||'?'}; screen=${screen.width}x${screen.height}; layout=${document.documentElement.clientWidth}; content=${document.documentElement.scrollWidth}; visible=${v?.width?.toFixed(0)||'?'}; input=${document.activeElement?.tagName==='INPUT'?'focused':'none'}`}
 function update(){const orientation=screen.orientation?.type||(innerWidth>innerHeight?'landscape':'portrait');if(orientation!==lastOrientation){previous=panel.dataset.current||'—';lastOrientation=orientation}const current=snapshot();panel.dataset.current=current;panel.textContent='缩放诊断（请截图）\n当前 '+orientation+'\n'+current+'\n切换前 '+previous}
 addEventListener('resize',update);addEventListener('orientationchange',()=>{update();setTimeout(update,500);setTimeout(update,1500)});window.visualViewport?.addEventListener('resize',update);update()
}
