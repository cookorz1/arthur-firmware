'use strict';
'require view';
'require rpc';
'require form';
'require uci';
'require poll';
'require dom';

var callStatus = rpc.declare({object: 'arthur', method: 'status', expect: {'': {}}});
var callDiagnose = rpc.declare({object: 'arthur', method: 'diagnose', expect: {'': {}}});

return view.extend({
    load: function() {
        return Promise.all([uci.load('arthur'), callStatus()]);
    },

    updateStatus: function(data) {
        var ports = (data.ports || []).slice();
        if (data.usb_port)
            ports.push(data.usb_port);
        var rows = ports.map(function(port) {
            var state = !port.present ? _('接口不存在') : (port.link ? _('已连接') : _('未连接'));
            var speed = !port.link ? '—' : (port.speed > 0 ? port.speed + ' Mbps' : _('无法读取'));
            var duplex = !port.link ? '—' : (port.duplex === 'full' ? _('全双工') : (port.duplex === 'half' ? _('半双工') : _('未知')));
            return E('tr', {'class': 'tr'}, [
                E('td', {'class': 'td'}, [port.label]),
                E('td', {'class': 'td'}, [port.device]),
                E('td', {'class': 'td'}, [state]),
                E('td', {'class': 'td'}, [speed]),
                E('td', {'class': 'td'}, [duplex])
            ]);
        });
        dom.content(this.portRows, rows);
        var usb = !data.usb_enabled ? _('USB 上网已关闭') :
            (!data.usb_present ? _('USB 上网已开启，等待连接随身 WiFi') :
            (data.usb_up ? _('随身 WiFi 已连接并取得上网接口') : _('已发现随身 WiFi，正在建立 DHCP 连接')));
        dom.content(this.usbStatus, [usb + (data.usb_device ? ' · ' + data.usb_device : '')]);
        var busSpeed = data.usb_bus_speed > 0 ? data.usb_bus_speed + ' Mbps' : _('无法读取');
        dom.content(this.usbSpeed, [
            _('USB 总线连接速率：') + (data.usb_present ? busSpeed : _('未连接')) +
            _('。USB 行的链路速率由网卡驱动报告；两者均不代表蜂窝网络或宽带测速。')
        ]);
    },

    showDiagnosis: function(data) {
        var rows = (data.uplinks || []).map(function(link) {
            var probes = link.probes || [];
            var web = (link.https || []).some(function(test) { return test.reachable; });
            var ping = probes.some(function(test) { return typeof test.loss === 'number' && test.loss < 100; });
            var unstable = probes.some(function(test) {
                return (typeof test.loss === 'number' && test.loss > 0 && test.loss < 100) ||
                    (typeof test.latency === 'number' && test.latency > 150);
            });
            var summary = !link.up ? _('接口未连接') : (!link.ready ? _('未取得 IPv4 地址') :
                (web ? (unstable ? _('外网可达，本次采样有延迟或丢包') : _('本次外网检测可达')) :
                (ping ? _('IP 可达，HTTPS 检测未通过') : _('本次外网检测未通过'))));
            var samples = probes.map(function(test) {
                var latency = typeof test.latency === 'number' ? test.latency + ' ms' : _('无响应或无法读取');
                var loss = typeof test.loss === 'number' ? test.loss + '%' : _('未测得');
                return E('div', {}, [test.target + '：' + latency + ' / ' + _('丢包 ') + loss]);
            });
            return E('tr', {'class': 'tr'}, [
                E('td', {'class': 'td'}, [link.interface === 'f50' ? _('随身 WiFi（USB）') : _('宽带（WAN）')]),
                E('td', {'class': 'td'}, [summary]),
                E('td', {'class': 'td'}, [link.address || '—']),
                E('td', {'class': 'td'}, [!link.ready ? '—' : (web ? _('可达') : _('未通过'))]),
                E('td', {'class': 'td'}, samples.length ? samples : ['—'])
            ]);
        });
        if (!rows.length)
            throw new Error(_('未返回有效检测结果，请重试。'));
        dom.content(this.healthRows, rows);
        var time = data.timestamp ? new Date(data.timestamp * 1000).toLocaleTimeString() : '';
        dom.content(this.healthStatus, [_('检测完成（IPv4）') + (time ? ' · ' + time : '')]);
    },

    runDiagnosis: function(event) {
        if (this.diagnosing)
            return Promise.resolve();
        var button = event.currentTarget;
        this.diagnosing = true;
        button.disabled = true;
        dom.content(this.healthStatus, [_('正在检测，请稍候……')]);
        return callDiagnose().then(L.bind(this.showDiagnosis, this)).catch(L.bind(function() {
            dom.content(this.healthStatus, [_('本次检测失败，请重试。下方如有结果，仍为上一次采样。')]);
        }, this)).finally(L.bind(function() {
            this.diagnosing = false;
            button.disabled = false;
        }, this));
    },

    render: function(data) {
        var m = new form.Map('arthur', _('USB 上网设置'),
            _('控制随身 WiFi 的 USB 上网接口。支持 CDC-ECM、RNDIS、NCM 共享网络模式；关闭后保留设备供电，设置在重启后继续生效。'));
        var s = m.section(form.NamedSection, 'usb', 'usb');
        s.anonymous = true;
        var o = s.option(form.Flag, 'enabled', _('开启 USB 上网'));
        o.default = '1';
        o.rmempty = false;

        this.portRows = E('tbody');
        this.usbStatus = E('p', {'class': 'cbi-section-descr'});
        this.usbSpeed = E('p', {'class': 'cbi-section-descr'});
        this.healthRows = E('tbody');
        this.healthStatus = E('p', {'class': 'cbi-section-descr'}, [_('尚未检测，点击按钮开始。')]);
        var healthTable = E('table', {'class': 'table'}, [
            E('thead', {}, [E('tr', {'class': 'tr table-titles'},
                [_('上网来源'), _('检测状态'), _('IPv4 地址'), _('HTTPS'), _('测点：平均延迟 / 丢包')].map(function(title) {
                    return E('th', {'class': 'th'}, [title]);
                }))]), this.healthRows
        ]);
        var table = E('table', {'class': 'table'}, [
            E('thead', {}, [E('tr', {'class': 'tr table-titles'},
                [_('网口'), _('设备'), _('链路状态'), _('协商速率'), _('双工模式')].map(function(title) {
                    return E('th', {'class': 'th'}, [title]);
                }))]), this.portRows
        ]);
        this.updateStatus(data[1]);
        poll.add(L.bind(function() {
            return callStatus().then(L.bind(this.updateStatus, this));
        }, this), 3);
        return m.render().then(L.bind(function(formNode) {
            return E('div', {}, [
                E('h2', {}, [_('亚瑟网络面板')]),
                E('div', {'class': 'cbi-section'}, [
                    E('h3', {}, [_('接口协商速率')]),
                    E('p', {'class': 'cbi-section-descr'}, [_('每 3 秒刷新 WAN、LAN1、LAN2、LAN3 和 USB 网卡链路状态。协商速率不代表宽带测速结果。')]),
                    table,
                    E('h3', {}, [_('USB 上网状态')]),
                    this.usbStatus,
                    this.usbSpeed
                ]),
                E('div', {'class': 'cbi-section'}, [
                    E('h3', {}, [_('网络质量检测')]),
                    E('p', {'class': 'cbi-section-descr'}, [_('手动检测 WAN 与 USB 随身 WiFi 的 IPv4 接入、外网可达性、延迟和丢包，约需 6 秒。每个 IP 测点采样 3 次；HTTPS 测点为百度和腾讯。检测使用当前路由与代理策略，少量采样及测点限制不能代表长期质量。')]),
                    E('p', {'class': 'cbi-section-descr'}, [_('此处不提供蜂窝信号格数或光猫光功率：USB/网线通常不会传递这些数据，需要上游设备提供查询接口。')]),
                    E('button', {'class': 'cbi-button cbi-button-action', 'type': 'button',
                        'click': L.bind(this.runDiagnosis, this)}, [_('开始检测')]),
                    this.healthStatus,
                    healthTable
                ]), formNode
            ]);
        }, this));
    }
});
