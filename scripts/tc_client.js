(function(){
  function $(q){return document.querySelector(q)}
  function toast(msg){let t=document.getElementById('anni-tc-toast');if(!t){t=document.createElement('div');t.id='anni-tc-toast';t.style.cssText='position:fixed;right:14px;bottom:14px;z-index:99999;background:#111;color:#fff;padding:10px 14px;border-radius:10px;font:12px/1.2 system-ui,Arial,sans-serif;box-shadow:0 4px 12px rgba(0,0,0,.2)';document.body.appendChild(t)}t.textContent=msg;t.style.opacity='0.95';setTimeout(()=>t.style.opacity='0',2000)}
  async function runTC(){
    const src=$('#source')||document.querySelector('select'); const tgts=$('#targets')||document.querySelector('select[multiple]')||document.querySelectorAll('select')[1]; const txt=$('#sourceText')||document.querySelector('textarea')||document.querySelector('[contenteditable="true"]');
    if(!src||!tgts||!txt){toast('TC error: fields missing');return}
    const S=src.value||'en'; const T=tgts.multiple? (tgts.selectedOptions[0]?.value||'ja') : (tgts.value||'ja');
    const X=txt.value!==undefined? txt.value : (txt.innerText||txt.textContent||'');
    const body={source:S,target:T,text:X,profile:'marketing',persona:'ogilvy',level:2};
    let j=null, status=''; try{
      const r=await fetch('http://127.0.0.1:8095/transcreate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      j=await r.json(); const m=(j.trace&&j.trace.tc_model)||'?'; const d=!!j.degraded; const l=(j.transcreated_text||j.text||'').length; status=`TC ✓ model=${m} degraded=${d} len=${l}`;
    }catch(e){status='TC ✕ '+String(e)}
    if(j&&j.transcreated_text){window.__tc_last_text__=j.transcreated_text}
    toast(status)
    let pane=document.getElementById('anni-tc-pane'); if(!pane){pane=document.createElement('textarea');pane.id='anni-tc-pane';pane.readOnly=true;pane.style.cssText='position:fixed;left:12px;bottom:12px;width:40%;height:28%;z-index:99997;background:#fff;color:#111;padding:10px 12px;border:1px solid #ddd;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,.08);font:12px/1.4 system-ui,Arial';document.body.appendChild(pane)}
    pane.value=(j&&j.transcreated_text)||'';
  }
  function ensureBtn(){
    if(document.getElementById('anni-tc-btn')) return;
    const b=document.createElement('button'); b.id='anni-tc-btn'; b.type='button'; b.textContent='Transcreate';
    b.style.cssText='position:fixed;right:14px;bottom:110px;z-index:99998;background:#1d4ed8;color:#fff;border:none;border-radius:10px;padding:10px 14px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.2)';
    b.onclick=runTC;
    const add=()=>document.body.appendChild(b);
    if(document.readyState==='complete'||document.readyState==='interactive') add(); else document.addEventListener('DOMContentLoaded',add)
  }
  ensureBtn();
})();
