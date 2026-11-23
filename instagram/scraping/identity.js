(async()=>{
// Which Instagram account this tab is signed in as, read from the session itself. The profile page being viewed is
// never evidence: any tab can view any profile.
//
// Why web_form_data (measured 2026-10-14, when this was built): it answers only for the signed-in account (it is the
// edit-profile form), as JSON with form_data.username. current_user/?edit=true returns HTML on web, and
// users/<pk>/info/ answered HTTP 429, so neither is used.
//
// PRIVACY: form_data also holds the account's email and phone. Only the username and the page-visible ds_user_id
// leave the page; never widen this return value.
const F=async(u,o)=>{for(let i=0;i<4;i++){try{return await fetch(u,o)}catch(e){if(i===3)throw e;await new Promise(r=>setTimeout(r,1500*(i+1)))}}};
const out={origin:location.origin,ds_page:(document.cookie.match(/(?:^|; )ds_user_id=(\d+)/)||[])[1]||null};
try{
  const r=await F('/api/v1/accounts/edit/web_form_data/',{credentials:'include',headers:{'X-IG-App-ID':'936619743392459','X-Requested-With':'XMLHttpRequest'}});
  out.status=r.status;
  const t=await r.text();
  let j=null;try{j=JSON.parse(t)}catch(e){}
  out.json=!!j;
  out.username=j&&j.form_data?(j.form_data.username||null):null;
  // A short non-JSON prefix helps diagnose a login wall or a changed endpoint without carrying personal data.
  if(!j)out.prefix=t.slice(0,60).replace(/\s+/g,' ');
  // Integrity signals on the identity call itself (checkpoint, rate limit) are passed up for collect.py's guard.
  if(j&&(j.checkpoint_url||j.challenge||/checkpoint_required|challenge_required|feedback_required|rate_limit|please wait/i.test(j.message||'')))
    out.signal={message:String(j.message||'').slice(0,120),checkpoint:!!j.checkpoint_url};
}catch(e){out.error=String(e)}
return JSON.stringify(out);
})()
