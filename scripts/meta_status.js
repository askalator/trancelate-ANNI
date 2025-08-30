(function(){
  const API='http://127.0.0.1:8091/meta';
  const pill=document.createElement('div');
  pill.id='anni-meta-pill';
  pill.style.cssText='position:fixed;left:12px;bottom:12px;z-index:99999;font:12px/1.2 system-ui,Arial,sans-serif;background:#111;color:#fff;border-radius:999px;padding:8px 12px;box-shadow:0 4px 12px rgba(0,0,0,.2);cursor:pointer;opacity:.9';
  pill.textContent='Anni: checking…';
  document.addEventListener('DOMContentLoaded',()=>document.body.appendChild(pill));
  let collapsed=false;
  pill.onclick=()=>{collapsed=!collapsed; pill.style.opacity=collapsed?.4:.9};
  async function tick(){
    try{
      const r=await fetch(API,{cache:'no-store'}); const j=await r.json();
      const ok=!!j.backend_alive, url=j.backend_url||'—';
      pill.style.background= ok ? '#0a7d32' : '#9b1c1c';
      pill.textContent = `Anni ${ok?'✓':'✕'} · ${url}`;
      pill.title = JSON.stringify(j,null,2);
    }catch(e){
      pill.style.background='#9b1c1c';
      pill.textContent='Anni ✕ · meta error';
      pill.title=String(e);
    }
  }
  setInterval(tick, 10000); tick();
})();
