 'use strict';
'require view';
'require rpc';
'require ui';
var getIdentity = rpc.declare({object:'arthur', method:'identity', expect:{'':{}}});
var saveIdentity = rpc.declare({object:'arthur', method:'save_identity', params:['hostname','image','reset'], expect:{'':{}}});
return view.extend({
    load:function(){ return getIdentity(); },
    render:function(data){
        var image='', reset=false;
        var name=E('input',{type:'text',maxlength:63,'class':'cbi-input-text',value:data.hostname || 'jdy-cookorz'});
        var preview=E('img',{src:data.custom_logo?'/luci-static/arthur/custom-logo.png?v='+Date.now():'/luci-static/arthur/avatar.jpg',alt:'当前 Logo',style:'width:96px;height:96px;object-fit:contain;border-radius:16px'});
        var file=E('input',{type:'file',accept:'image/png',change:async function(){
            image=''; reset=false; save.disabled=true;file.disabled=true;restore.disabled=true;
            try {
                var f=file.files[0]; if(!f) return;
                if(f.size>65536 || f.type!=='image/png') throw Error('请选择不超过64KiB的PNG图片');
                var url=await new Promise(function(resolve,reject){var r=new FileReader();r.onload=function(){resolve(r.result);};r.onerror=reject;r.readAsDataURL(f);});
                var img=new Image(); await new Promise(function(resolve,reject){img.onload=resolve;img.onerror=function(){reject(Error('图片无法解码'));};img.src=url;});
                if(img.width>2048 || img.height>2048) throw Error('图片尺寸不能超过2048×2048');
                image=url.split(',')[1]; preview.src=url;
            } catch(e){file.value='';ui.addNotification(null,E('p',{},e.message),'error');} finally {save.disabled=false;file.disabled=false;restore.disabled=false;}
        }});
        var restore=E('button',{'class':'btn',click:function(){image='';reset=true;file.value='';preview.src='/luci-static/arthur/avatar.jpg';}},'恢复默认 Logo（保存后生效）');
        var save=E('button',{'class':'btn cbi-button-positive',click:async function(){
            if(!/^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/.test(name.value)) {ui.addNotification(null,E('p',{},'主机名为1～63位字母、数字或中间的连字符'),'error');return;}
            save.disabled=true;file.disabled=true;
            try {var result=await saveIdentity(name.value,image,reset);if(result.error) throw Error(result.error);window.location.reload();}
            catch(e){ui.addNotification(null,E('p',{},e.message),'error');save.disabled=false;file.disabled=false;}
        }},'保存并刷新');
        return E('div',{'class':'cbi-map'},[E('h2',{},'主机名与 Logo'),E('p',{},'自定义设备主机名及登录页、管理界面、浏览器标签页 Logo。保存后立即生效，重启及保留配置升级后保留。'),E('label',{},'主机名'),E('p',{},name),E('p',{},'主机名不会修改 Wi-Fi 名称、密码或管理地址。'),preview,E('p',{},file),E('p',{},'PNG，最大64KiB，建议正方形256×256，尺寸不超过2048×2048。Logo会在未登录页面公开展示，请勿上传私人信息。'),E('p',{},restore),E('p',{},save)]);
    },
    handleSaveApply:null,handleSave:null,handleReset:null
});
