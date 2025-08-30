document.addEventListener('DOMContentLoaded', () => {
  const setAutoDir = el => {
    try {
      el.setAttribute('dir','auto');
      el.style.unicodeBidi = 'plaintext';
      el.style.direction = 'auto';
    } catch(e) {}
  };
  document.querySelectorAll('textarea, [contenteditable="true"]').forEach(setAutoDir);
  const mo = new MutationObserver(() => {
    document.querySelectorAll('textarea, [contenteditable="true"]').forEach(setAutoDir);
  });
  mo.observe(document.body, {subtree:true, childList:true});
});
