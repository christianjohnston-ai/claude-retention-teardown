(async()=>{
// One Reel's insights, run as ordinary page JavaScript inside the account's own cmux profile (www.instagram.com).
// collect.py replaces __MEDIA_IGID__ (the shortcode decoded to a number) before passing this to `cmux browser eval`.
//
// Why a page fetch works without an extension (measured 2026-10-14): i.instagram.com/graphql_www answers
// Origin https://www.instagram.com with Access-Control-Allow-Origin www.instagram.com + Allow-Credentials true, the
// page's CSP connect-src allows *.instagram.com, and www -> i is same-site, so WebKit sends the session cookies.
// It is a plain GET with credentials included and no custom headers.
//
// Credit: the request shape and the two Instagram-internal ids below were learned from the ReelCurve v0.4.0 Chrome extension.
// SYNC WARNING: if Instagram rotates client_doc_id or bloksVersioningId, the answer stops containing ig_reel_insights
// and collect.py exits 7 (FORMAT_CHANGED). They also appear in ig_parse.METHOD; change both together.
const DOC='34117726176169458716316101',BLOKS='06d2ce5b718bc1f7b81c5c853dadef374aea8a009110982b5b80ff74164fd5dc';
const u='https://i.instagram.com/graphql_www?'+new URLSearchParams({client_doc_id:DOC,variables:JSON.stringify({bloksVersioningId:BLOKS,mediaIgid:'__MEDIA_IGID__'}),method:'get',format:'json',enable_canonical_naming:'true',enable_canonical_variable_overrides:'true',enable_canonical_naming_ambiguous_type_prefixing:'true'});
for(let i=0;i<3;i++){
  try{
    const r=await fetch(u,{credentials:'include',cache:'no-store'});
    const t=await r.text();
    // The whole body goes back to Python, which parses it and decides. Nothing is kept in the page.
    return JSON.stringify({ok:true,status:r.status,type:r.type,len:t.length,text:t});
  }catch(e){
    // Only a transport failure is retried: a WebKit tab that sat idle answers its first fetch with
    // "TypeError: Load failed" (learned on TikTok, 2026-10-07). An answer from Instagram is never retried here.
    if(i===2)return JSON.stringify({ok:false,error:String(e)});
    await new Promise(r=>setTimeout(r,2000*(i+1)));
  }
}
})()
