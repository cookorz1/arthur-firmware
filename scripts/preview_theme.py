import pathlib
import re
import sys
from pathlib import Path

ROOT = pathlib.Path(__file__).resolve().parents[1]
repo = ROOT
assets = repo / 'package/arthur/files/www/luci-static/resources'
preview = ROOT / 'logs/ui'
preview.mkdir(parents=True,exist_ok=True)
menu = {'children': {'admin': {'name': 'admin', 'title': '管理', 'children': {}}}}
groups = [('overview', '首页', []), ('status', '网络状态', [('overview','状态总览'),('realtime','实时信息')]),
          ('network', '网络设置', [('network','上网设置'),('wireless','无线设置'),('arthur','亚瑟网络面板'),('arthur-performance','加速与内存')]),
          ('services', '应用服务', [('openclash','OpenClash'),('store','iStore 应用商店')]), ('system', '系统设置', [('flash','系统升级'),('admin','管理权')])]
for name, title, children in groups:
    menu['children']['admin']['children'][name] = {'name': name, 'title': title, 'children': {n: {'name': n, 'title': t, 'children': {}} for n,t in children}}
import json
harness = r'''
window.E = function(tag, attrs, children) {
    var node = document.createElement(tag || 'div');
    Object.entries(attrs || {}).forEach(([key,value]) => { if (typeof value === 'function') node.addEventListener(key,value); else node.setAttribute(key,value); });
    function add(c) {if (Array.isArray(c)) c.forEach(add); else if(c!=null) node.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));}
    add(children);return node;
};
window._ = t=>t;
window.L = {url:(...p)=>'/cgi-bin/luci/'+p.join('/')};
window.view={extend:o=>o};window.poll={add:f=>{window.previewPoll=f;}};
window.ui={menu:{load:async()=>(MENU),getChildren:o=>Object.values(o.children||{})}};
window.baseclass={extend:o=>o};
var tick=0;
window.rpc={declare:spec=>async()=>{
 if(spec.method==='board')return {hostname:'jdy-cookorz'};
 if(spec.method==='info')return {uptime:108224,localtime:1792547400};
 if(spec.method==='dashboard')return {sample_time:100+tick*3,cpu:{total:1000+tick*100,idle:800+tick*82},storage:{total_kib:2097152,used_kib:326000},
 uplinks:[{name:'wan',device:'wan',ready:true,rx_bytes:100000+tick*53400000,tx_bytes:100000+tick*7800000},{name:'f50',device:'usb0',ready:true,rx_bytes:30000+tick*12000000,tx_bytes:6000+tick*3000000}],
 clients:[{hostname:'DESKTOP-Home',mac:'00:11:22:33:44:55',address:'192.168.10.100',state:'REACHABLE'},{hostname:'iPhone',mac:'00:11:22:33:44:56',address:'192.168.10.101',state:'STALE'},{hostname:'NAS',mac:'00:11:22:33:44:57',address:'192.168.10.102',state:'REACHABLE'}]};
 if(spec.method==='status')return {usb_enabled:true,usb_present:true,usb_up:true,ports:[{label:'WAN',link:true,speed:1000,duplex:'full'},{label:'LAN1',link:true,speed:1000,duplex:'full'},{label:'LAN2',link:false},{label:'LAN3',link:true,speed:100,duplex:'full'}],usb_port:{label:'USB',link:true,speed:null}};
 if(spec.method==='performance')return {proxy_guard:true,reason:'openclash',tcp_cc:'bbr',zram_active:true,zram_size_kib:131072,memory:{total_kib:417792,available_kib:227960},ecm_loaded:true,ecm_stop4:1,ecm_stop6:1};
}};
'''.replace('MENU', json.dumps(menu,ensure_ascii=False))
navigation=''.join('<li class="'+('slide' if c else '')+'"><a class="'+('menu' if c else 'food')+' '+('active' if n=='overview' else '')+'" href="/cgi-bin/luci/admin/'+n+'">'+t+'</a>'+('<ul class="slide-menu">'+''.join('<li><a href="/cgi-bin/luci/admin/'+n+'/'+a+'">'+b+'</a></li>' for a,b in c)+'</ul>' if c else '')+'</li>' for n,t,c in groups)
head='<!doctype html><html lang="zh-CN" data-arthur-theme="light"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>jdy-cookorz · 界面预览</title>' + '<style>' + Path(sys.argv[1]).read_text(encoding='utf-8') + '</style><style>' + (repo/'package/arthur/files/www/luci-static/arthur/theme.css').read_text(encoding='utf-8').replace('url(logo.svg)', 'url('+(repo/'package/arthur/files/www/luci-static/arthur/logo.svg').resolve().as_uri()+')').replace('url(mountain.png)', 'url('+(repo/'package/arthur/files/www/luci-static/arthur/mountain.png').resolve().as_uri()+')') + '</style>'
body='<body class="logged-in"><div class="main"><aside class="main-left" id="mainmenu"><div class="sidenav-header"><a class="brand">jdy-cookorz</a></div><ul class="nav">'+navigation+'</ul></aside><div class="main-right"><header class="bg-primary"><div class="fill"><div class="container"><div class="flex1"><a class="showSide">☰</a><a class="brand">jdy-cookorz</a></div><div id="indicators" class="status"></div></div></div></header><div class="darkMask"></div><div id="maincontent"><div class="container"><div style="font-size:11px;color:#8091a9">界面预览 · 示例数据 · 非设备实时状态</div><div id="view"></div></div></div></div></div>'
dashboard=(assets/'view/arthur/dashboard.js').read_text(encoding='utf-8')
shell=(assets/'arthur-shell.js').read_text(encoding='utf-8').replace('@ARTHUR_VERSION@', (repo/'VERSION').read_text().strip())
boot='''
(async function(){
 var v=(new Function(DASHBOARD))(); var data=await v.load(); document.getElementById('view').replaceWith(await v.render(data));
 var shell=(new Function(SHELL))();shell.__init__();
 document.querySelector('a.showSide').addEventListener('click',()=>document.querySelector('#mainmenu').classList.toggle('active'));
 for(var i=0;i<55;i++){tick++;await window.previewPoll();}
 window.previewReady=true;
})().catch(e=>{window.previewError=e.stack;document.body.appendChild(E('pre',{},e.stack));console.error(e);});
'''.replace('DASHBOARD',json.dumps(dashboard,ensure_ascii=False)).replace('SHELL',json.dumps(shell,ensure_ascii=False))
(preview/'dashboard.html').write_text(head+body+'<script>'+harness+boot+'</script></body></html>',encoding='utf-8')
login=(repo/'package/arthur/theme/sysauth.ut').read_text(encoding='utf-8').replace('@ARTHUR_VERSION@', (repo/'VERSION').read_text().strip())
login=re.sub(r'{#.*?#}|{%.*?%}', '', login,flags=re.S)
login=re.sub(r'{{.*?}}',lambda m:'root' if 'duser' in m[0] else '/preview/login.html' if 'REQUEST_URI' in m[0] else '账号或密码错误，请重试。',login,flags=re.S)
login=re.sub(r'<div class="alert-message error".*?</div>','',login)
(preview/'login.html').write_text(head+'<body>'+login,encoding='utf-8')
print('Preview pages generated')

