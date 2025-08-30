(function(){
  const BTN_ID='anni-copy-cli-btn';
  function shQuote(s){ return "'" + String(s).replace(/'/g,"'\\''").replace(/\n/g,' ') + "'"; }
  function getEls(){
    const src = document.querySelector('#source') || document.querySelector('select');
    const tgts= document.querySelector('#targets[multiple]') || document.querySelector('select[multiple]') || document.querySelectorAll('select')[1];
    const txt = document.querySelector('#sourceText') || document.querySelector('textarea') || document.querySelector('[contenteditable="true"]');
    return {src,tgts,txt};
  }
  function toast(msg){
    let t=document.getElementById('anni-cli-toast');
    if(!t){
      t=document.createElement('div');
      t.id='anni-cli-toast';
      Object.assign(t.style,{
        position:'fixed', right:'14px', bottom:'14px', zIndex:99999,
        background:'#111', color:'#fff', padding:'10px 14px', borderRadius:'10px',
        font:'12px/1.2 system-ui,Arial,sans-serif', boxShadow:'0 4px 12px rgba(0,0,0,.2)'
      });
      document.body.appendChild(t);
    }
    t.textContent=msg; t.style.opacity='0.95'; setTimeout(()=>t.style.opacity='0',1600);
  }
  function buildCmd(){
    const {src,tgts,txt}=getEls();
    if(!src||!tgts||!txt){ alert('CLI: konnte Felder nicht finden (#source, #targets, #sourceText)'); return null; }
    const SRC = src.value || 'en';
    const targets = tgts.multiple ? Array.from(tgts.selectedOptions).map(o=>o.value) : [tgts.value||'ja'];
    const textVal = txt.value !== undefined ? txt.value : (txt.innerText||txt.textContent||'');
    if(targets.length<=1){
      return `anni ${SRC} ${targets[0]||'ja'} ${shQuote(textVal)}`;
    }else{
      return `anni ${SRC} -m ${targets.join(',')} ${shQuote(textVal)}`;
    }
  }
  async function copyCli(){
    const cmd = buildCmd(); if(!cmd) return;
    window.__anni_last_cli__ = cmd;
    // 1) modern API
    try{
      if (navigator.clipboard && window.isSecureContext !== false) {
        await navigator.clipboard.writeText(cmd);
        toast('CLI command copied');
        return;
      }
      throw new Error('Navigator clipboard not available');
    }catch(e1){
      // 2) fallback via hidden textarea
      try{
        const ta=document.createElement('textarea');
        ta.value=cmd; ta.setAttribute('readonly','');
        ta.style.position='fixed'; ta.style.left='-9999px'; ta.style.top='-9999px';
        document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
        toast('CLI command copied (fallback)');
        return;
      }catch(e2){
        console.error('copy failed', e1, e2);
        alert('Kopieren fehlgeschlagen. Der Befehl ist in window.__anni_last_cli__ gespeichert:\n\n'+cmd);
      }
    }
  }
  function ensureBtn(){
    if(document.getElementById(BTN_ID)) return;
    const b=document.createElement('button');
    b.id=BTN_ID; b.type='button'; b.textContent='Copy CLI';
    Object.assign(b.style,{
      position:'fixed', right:'14px', bottom:'60px', zIndex:99998,
      background:'#0a7d32', color:'#fff', border:'none', borderRadius:'10px',
      padding:'10px 14px', cursor:'pointer', boxShadow:'0 4px 12px rgba(0,0,0,.2)'
    });
    b.onmouseenter=()=>b.style.opacity='0.9';
    b.onmouseleave=()=>b.style.opacity='1';
    b.onclick=copyCli;
    const add=()=>document.body.appendChild(b);
    if(document.readyState==='complete' || document.readyState==='interactive') add();
    else document.addEventListener('DOMContentLoaded', add);
  }
  ensureBtn();
})();
