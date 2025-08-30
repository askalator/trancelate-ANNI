(function(){
  function $(q){return document.querySelector(q)}
  function toast(msg){
    let t=document.getElementById('anni-preset-toast');
    if(!t){t=document.createElement('div');t.id='anni-preset-toast';t.style.cssText='position:fixed;right:14px;bottom:14px;z-index:99999;background:#111;color:#fff;padding:10px 14px;border-radius:10px;font:12px/1.2 system-ui,Arial,sans-serif;box-shadow:0 4px 12px rgba(0,0,0,.2)';document.body.appendChild(t)}
    t.textContent=msg;t.style.opacity='0.95';setTimeout(()=>t.style.opacity='0',1600)
  }
  async function loadFlags(){
    const r=await fetch('http://127.0.0.1:8094/scripts/langs_flags.json',{cache:'no-store'}); return r.json()
  }
  function selectSet(codes){
    const tgt = $('#targets') || document.querySelector('select[multiple]') || document.querySelectorAll('select')[1]
    if(!tgt) return 0
    const set=new Set(codes)
    Array.from(tgt.options).forEach(o=>o.selected=set.has(o.value))
    return Array.from(tgt.selectedOptions).length
  }
  function makeBtn(txt,setName,codes){
    const b=document.createElement('button')
    b.type='button'; b.textContent=txt
    b.style.cssText='margin:0 6px 0 0;padding:8px 10px;border:none;border-radius:10px;background:#0a7d32;color:#fff;cursor:pointer'
    b.onclick=()=>toast('Selected '+selectSet(codes)+' targets ('+setName+')')
    return b
  }
  async function init(){
    const f=await loadFlags()
    const bar=document.createElement('div')
    bar.id='anni-presets'; bar.style.cssText='position:fixed;left:12px;top:12px;z-index:99998;background:#fff;border:1px solid #ddd;border-radius:12px;padding:8px 10px;box-shadow:0 4px 12px rgba(0,0,0,.08);font:12px system-ui,Arial'
    bar.appendChild(makeBtn('Africa','africa',f.africa||[]))
    bar.appendChild(makeBtn('Asia','asia',f.asia||[]))
    bar.appendChild(makeBtn('CJK','cjk',f.cjk||[]))
    bar.appendChild(makeBtn('Indic','indic',f.indic||[]))
    bar.appendChild(makeBtn('RTL','rtl',f.rtl||[]))
    const clear=document.createElement('button'); clear.type='button'; clear.textContent='Clear'
    clear.style.cssText='margin-left:6px;padding:8px 10px;border:none;border-radius:10px;background:#9b1c1c;color:#fff;cursor:pointer'
    clear.onclick=()=>{selectSet([]);toast('Selected 0 targets')}
    bar.appendChild(clear)
    document.addEventListener('DOMContentLoaded',()=>document.body.appendChild(bar))
    if(document.readyState==='complete'||document.readyState==='interactive') document.body.appendChild(bar)
  }
  init()
})();
