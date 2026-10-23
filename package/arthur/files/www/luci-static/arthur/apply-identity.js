(function(){
'use strict';
function apply(){
 var d=window.arthurIdentity;if(!d)return;
 document.title=d.hostname;
 document.querySelectorAll('meta[name="application-name"],meta[name="apple-mobile-web-app-title"]').forEach(function(e){e.content=d.hostname;});
 document.querySelectorAll('link[rel="icon"],link[rel="apple-touch-icon"]').forEach(function(e){e.href=d.logo;e.removeAttribute('type');});
 document.querySelectorAll('.arthur-mark,.arthur-avatar').forEach(function(e){e.style.backgroundImage='url("'+d.logo+'")';});
 document.querySelectorAll('.arthur-brand-copy strong,.arthur-side-footer b').forEach(function(e){e.textContent=d.hostname;});
 var welcome=document.querySelector('.arthur-login-card .arthur-muted');if(welcome)welcome.textContent='登录 '+d.hostname+'，掌握你的网络。';
}
window.arthurApplyIdentity=apply;
fetch('/luci-static/arthur/identity.json',{cache:'no-store',credentials:'omit'}).then(function(r){if(!r.ok)throw Error('identity unavailable');return r.json();}).then(function(d){
 if(!/^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/.test(d.hostname) || !/^\/luci-static\/arthur\/(?:avatar\.jpg|custom-logo\.png\?v=[0-9]+)$/.test(d.logo))return;
 window.arthurIdentity=d;apply();
}).catch(function(){});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply);else apply();
})();
