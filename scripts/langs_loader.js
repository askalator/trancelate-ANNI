document.addEventListener('DOMContentLoaded', async () => {
  const srcSel = document.querySelector('#source');
  const tgtSel = document.querySelector('#targets');
  if (!srcSel || !tgtSel) return;
  try {
    const r = await fetch('http://127.0.0.1:8094/langs.json', {cache:'no-store'});
    const j = await r.json();
    const langs = j.langs || [];
    const mk = (code) => { const o=document.createElement('option'); o.value=code; o.textContent=code; return o; };
    srcSel.innerHTML=''; tgtSel.innerHTML='';
    langs.forEach(code => { srcSel.appendChild(mk(code)); tgtSel.appendChild(mk(code).cloneNode(true)); });
    if (!srcSel.value && langs.includes('en')) srcSel.value='en';
    if (tgtSel.multiple) { Array.from(tgtSel.options).forEach(o => { o.selected = (o.value==='ja'); }); } else { tgtSel.value='ja'; }
  } catch(e) { console.error('langs_loader error', e); }
});
