'use strict';
'require view';
'require rpc';
'require form';
'require uci';
'require poll';
'require dom';

var callStatus = rpc.declare({object: 'arthur', method: 'status', expect: {'': {}}});

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
            (!data.usb_present ? _('USB 上网已开启，等待连接 F50') :
            (data.usb_up ? _('F50 已连接并取得上网接口') : _('已发现 F50，正在建立 DHCP 连接')));
        dom.content(this.usbStatus, [usb + (data.usb_device ? ' · ' + data.usb_device : '')]);
        var busSpeed = data.usb_bus_speed > 0 ? data.usb_bus_speed + ' Mbps' : _('无法读取');
        dom.content(this.usbSpeed, [
            _('USB 总线连接速率：') + (data.usb_present ? busSpeed : _('未连接')) +
            _('。USB 行的链路速率由网卡驱动报告；两者均不代表蜂窝网络或宽带测速。')
        ]);
    },

    render: function(data) {
        var m = new form.Map('arthur', _('USB 上网设置'),
            _('控制 F50 的 USB 上网接口。关闭后保留设备供电，设置在重启后继续生效。'));
        var s = m.section(form.NamedSection, 'usb', 'usb');
        s.anonymous = true;
        var o = s.option(form.Flag, 'enabled', _('开启 USB 上网'));
        o.default = '1';
        o.rmempty = false;

        this.portRows = E('tbody');
        this.usbStatus = E('p', {'class': 'cbi-section-descr'});
        this.usbSpeed = E('p', {'class': 'cbi-section-descr'});
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
                    E('p', {'class': 'cbi-section-descr'}, [_('每 3 秒刷新 WAN、LAN1、LAN2、LAN3 的物理链路状态。协商速率不代表宽带测速结果。')]),
                    table,
                    E('h3', {}, [_('USB 上网状态')]),
                    this.usbStatus,
                    this.usbSpeed
                ]), formNode
            ]);
        }, this));
    }
});
