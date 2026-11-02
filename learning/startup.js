// The module graph may be cold or unavailable in a home-screen browser session.
(()=>{
 let english=false;try{english=localStorage.getItem('hhx-interface-language')==='en'}catch{}if(english){const paragraph=document.querySelector('#startup-retry p'),button=document.getElementById('startup-reload');if(paragraph)paragraph.textContent='Unable to load. Check your connection and try again.';if(button)button.textContent='Try again'}
 const root=document.documentElement;const showFailure=()=>{if(root.dataset.learningReady==='true')return;const node=document.getElementById('startup-retry');if(node)node.hidden=false};
 const timer=setTimeout(showFailure,12000);
 window.addEventListener('error',showFailure,true);
 window.addEventListener('unhandledrejection',showFailure);
 window.addEventListener('hhx-learning-ready',()=>{root.dataset.learningReady='true';clearTimeout(timer);window.removeEventListener('error',showFailure,true);window.removeEventListener('unhandledrejection',showFailure)});
 document.getElementById('startup-reload')?.addEventListener('click',()=>{const url=new URL(location.href);url.searchParams.set('reload',String(Date.now()));location.replace(url)});
})();
