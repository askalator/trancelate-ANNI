(function(){
  const BASE='http://127.0.0.1:8091';
  const orig=window.fetch.bind(window);
  window.fetch=function(input, init){
    let url=typeof input==='string'?input:(input&&input.url)||'';
    if(url && !/^https?:\/\//i.test(url)){
      if(url.startsWith('/')) url=BASE+url;
      else if(url.startsWith('translate')||url.startsWith('meta')) url=BASE+'/'+url;
      if(typeof input==='string') input=url; else input=new Request(url,input);
    }
    
  try{
    const u=new URL(url);
    if(u.hostname==='127.0.0.1' && u.port==='8092' && (u.pathname.includes('/translate')||u.pathname.includes('/meta'))){
      u.port='8091';
      url=u.toString();
      if(typeof input==='string') input=url; else input=new Request(url,input);
    }
  }catch(e){}
    return orig(input, init);
  };
})();
