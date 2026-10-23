const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const path=require('path');
const root=path.join(__dirname,'..');
const script=fs.readFileSync(path.join(root,'package/arthur/files/www/luci-static/arthur/apply-identity.js'),'utf8');
async function check(data){
 const elements={};
 const selectors=['meta[name="application-name"],meta[name="apple-mobile-web-app-title"]','link[rel="icon"],link[rel="apple-touch-icon"]','.arthur-mark,.arthur-avatar','.arthur-brand-copy strong,.arthur-side-footer b'];
 selectors.forEach(s=>elements[s]=[{style:{},removeAttribute(k){delete this[k];}}]);
 const welcome={};const window={};
 const document={readyState:'complete',title:'jdy-cookorz',querySelectorAll(s){return elements[s]||[];},querySelector(){return welcome;}};
 vm.runInNewContext(script,{window,document,fetch:async(url,opts)=>{assert.strictEqual(opts.cache,'no-store');assert.strictEqual(url,'/luci-static/arthur/identity.json');return {ok:true,json:async()=>data};}});
 await new Promise(r=>setImmediate(r));
 return {window,document,elements,welcome};
}
(async()=>{
 const state=await check({hostname:'my-cookwrt',logo:'/luci-static/arthur/custom-logo.png?v=123'});
 assert.strictEqual(state.document.title,'my-cookwrt');
 assert.strictEqual(state.welcome.textContent,'登录 my-cookwrt，掌握你的网络。');
 assert.strictEqual(state.elements['.arthur-mark,.arthur-avatar'][0].style.backgroundImage,'url("/luci-static/arthur/custom-logo.png?v=123")');
 assert.strictEqual(state.elements['link[rel="icon"],link[rel="apple-touch-icon"]'][0].href,'/luci-static/arthur/custom-logo.png?v=123');
 const bad=await check({hostname:'<img onerror=alert(1)>',logo:'https://evil.invalid/logo.png'});
 assert.strictEqual(bad.document.title,'jdy-cookorz');
 const defaults=await check({hostname:'jdy-cookorz',logo:'/luci-static/arthur/avatar.jpg'});
 assert.strictEqual(defaults.document.title,'jdy-cookorz');
 const viewSource=fs.readFileSync(path.join(root,'package/arthur/files/www/luci-static/resources/view/arthur/identity.js'),'utf8');
 const calls=[], notices=[], nodes=[];
 const settingsView=new Function('view','rpc','ui','E','window','FileReader','Image',viewSource)(
  {extend:o=>o},
  {declare:spec=>async(...args)=>{if(spec.method==='identity')return {hostname:'old-router',custom_logo:false};calls.push(args);return {hostname:args[0]};}},
  {addNotification:(...args)=>notices.push(args)},
  (tag,attrs,children)=>{const n={tag,attrs:attrs||{},children,value:(attrs||{}).value||'',disabled:false};nodes.push(n);return n;},
  {location:{reload(){calls.push('reload');}}},
  class {readAsDataURL(){this.result='data:image/png;base64,aGVsbG8=';this.onload();}},
  class {constructor(){this.width=256;this.height=256;}set src(v){this.onload();}}
 );
 settingsView.render(await settingsView.load());
 const name=nodes.find(n=>n.tag==='input'&&n.attrs.type==='text');
 const file=nodes.find(n=>n.tag==='input'&&n.attrs.type==='file');
 const restore=nodes.find(n=>n.tag==='button'&&String(n.children).startsWith('恢复'));
 const save=nodes.find(n=>n.tag==='button'&&n.children==='保存并刷新');
 name.value='bad hostname';await save.attrs.click();assert.strictEqual(calls.length,0);assert.strictEqual(notices.length,1);
 name.value='new-router';file.files=[{type:'image/png',size:12}];await file.attrs.change();
 assert.strictEqual(save.disabled,false);await save.attrs.click();
 assert.deepStrictEqual(calls[0],['new-router','aGVsbG8=',false]);assert.strictEqual(calls[1],'reload');
 restore.attrs.click();await save.attrs.click();assert.deepStrictEqual(calls[2],['new-router','',true]);
 file.files=[{type:'image/png',size:65537}];await file.attrs.change();assert.strictEqual(notices.length,2);
 assert.strictEqual(file.disabled,false);assert.strictEqual(save.disabled,false);
 console.log('Identity view: title, logos, login text, uncached settings and invalid configuration handling passed.');
})();
