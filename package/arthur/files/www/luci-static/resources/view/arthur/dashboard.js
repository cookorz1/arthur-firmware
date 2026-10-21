'use strict';
'require view';
'require rpc';
'require poll';
'require ui';

var callBoard = rpc.declare({object: 'system', method: 'board'});
var callInfo = rpc.declare({object: 'system', method: 'info'});
var callSnapshot = rpc.declare({object: 'arthur', method: 'dashboard'});
var callPorts = rpc.declare({object: 'arthur', method: 'status'});
var callPerformance = rpc.declare({object: 'arthur', method: 'performance'});
var paths = {
    globe: '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6h14M5 18h14"/>',
    devices: '<rect x="2" y="3" width="14" height="12" rx="2"/><path d="M6 20h6M9 15v5"/><rect x="15" y="10" width="7" height="11" rx="1.5"/>',
    cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 1v4m6-4v4M9 19v4m6-4v4M1 9h4m-4 6h4m14-6h4m-4 6h4"/>',
    memory: '<rect x="2" y="5" width="20" height="13" rx="2"/><path d="M6 9v5m4-5v5m4-5v5m4-5v5M6 18v3m4-3v3m4-3v3m4-3v3"/>',
    storage: '<path d="M6 3h12l3 17H3z"/><circle cx="16" cy="16" r="1"/><path d="M8 7h8"/>',
    wifi: '<path d="M2 8a16 16 0 0 1 20 0M5 12a11 11 0 0 1 14 0M8 16a6 6 0 0 1 8 0"/><circle cx="12" cy="20" r="1"/>',
    bolt: '<path d="M13 2L4 14h7l-1 8 10-13h-8z"/>',
    box: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 5V3h8v2m-6 9h4"/>',
    shield: '<path d="M12 2l9 4v6c0 5-9 10-9 10S3 17 3 12V6zM8 12l3 3 5-6"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="M7 12l3 3 7-7"/>',
    arrow: '<path d="M12 20V4m-6 6 6-6 6 6M4 20h16"/>'
};
function icon(name, color) {
    var node = E('span', {'class': 'arthur-icon ' + (color || ''), 'aria-hidden': 'true'});
    node.innerHTML = '<svg viewBox="0 0 24 24">' + (paths[name] || paths.globe) + '</svg>';
    return node;
}
function svg(tag, attrs, text) {
    var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attrs || {}).forEach(function(key) { el.setAttribute(key, attrs[key]); });
    if (text != null) el.textContent = text;
    return el;
}
function finite(value) { return typeof value === 'number' && Number.isFinite(value) && value >= 0; }
function percent(used, total) { return finite(used) && finite(total) && total > 0 ? Math.max(0, Math.min(100, Math.round(used / total * 100))) : null; }
function rate(value) { return !finite(value) ? '—' : value >= 1000000 ? (value / 1000000).toFixed(1) + ' Mbps' : (value / 1000).toFixed(1) + ' Kbps'; }
function capacity(kib) { return !finite(kib) ? '—' : kib >= 1048576 ? (kib / 1048576).toFixed(1) + ' GiB' : (kib / 1024).toFixed(0) + ' MiB'; }
function duration(seconds) {
    if (!finite(seconds)) return '—';
    var minutes = Math.floor(seconds / 60);
    return (minutes >= 1440 ? Math.floor(minutes / 1440) + ' 天 ' : '') + Math.floor(minutes % 1440 / 60) + ' 小时 ' + minutes % 60 + ' 分钟';
}
function sampleRates(previous, current, selection) {
    if (!previous || !current || !finite(current.sample_time) || !finite(previous.sample_time)) return null;
    var delta = current.sample_time - previous.sample_time;
    if (delta < 1 || delta > 20) return null;
    var seen = {}, rx = 0, tx = 0, count = 0;
    var uplinks = (current.uplinks || []).filter(function(item) { return item.ready && (selection === 'all' || item.name === selection); });
    for (var item of uplinks) {
        if (!item.device || seen[item.device]) continue;
        seen[item.device] = true;
        var old = (previous.uplinks || []).find(function(o) {return o.name === item.name && o.device === item.device && o.ready;});
        if (!old || !finite(item.rx_bytes) || !finite(item.tx_bytes) || !finite(old.rx_bytes) || !finite(old.tx_bytes) || item.rx_bytes < old.rx_bytes || item.tx_bytes < old.tx_bytes) return null;
        rx += (item.rx_bytes - old.rx_bytes) * 8 / delta;
        tx += (item.tx_bytes - old.tx_bytes) * 8 / delta;
        count++;
    }
    return count ? {rx: rx, tx: tx} : null;
}

function forwardingState(performance) {
    if (performance.error || performance.active_backend === 'conflict') return '请检查';
    if (performance.proxy_guard || performance.reason === 'openclash')
        return performance.software_flowtable || (performance.ecm_loaded && (performance.ecm_stop4 !== 1 || performance.ecm_stop6 !== 1)) ? '正在保护' : '代理保护中';
    if (performance.reason === 'qos') return 'QoS 保护中';
    if (performance.reason === 'steering') return '多核转发保护';
    if (performance.reason === 'off') return '已关闭';
    if (performance.active_backend === 'software') return '软件分载已启用';
    if (performance.mode === 'software') return '软件分载未就绪';
    return performance.ecm_loaded && performance.ecm_stop4 === 0 && performance.ecm_stop6 === 0 ? 'NSS 可加速' : '未就绪';
}

return view.extend({
    handleSaveApply: null, handleSave: null, handleReset: null,
    sampleRates: sampleRates,
    forwardingState: forwardingState,
    fetchData: function() { return Promise.all([callSnapshot(), callPorts(), callPerformance(), callInfo()]); },
    load: function() {return Promise.all([this.fetchData(), callBoard(), ui.menu.load().catch(function() {return {children: {}};})]);},
    metric: function(title, type, color) {
        var body = E('div', {'class': 'arthur-stat-body'}, [E('h3', {}, title)]);
        var value = E('strong', {}, '—');
        var note = E('small');
        body.appendChild(value);
        var meter = E('div', {'class': 'arthur-meter ' + (color || '')}, [E('span', {style: 'width:0%'})]);
        body.appendChild(meter); body.appendChild(note);
        return {node: E('section', {'class': 'arthur-card arthur-stat'}, [icon(type, color), body]), value: value, note: note, meter: meter.firstChild};
    },
    head: function(title, action) {return E('div', {'class': 'arthur-card-head'}, [E('h3', {}, title), action || E('span')]);},
    render: function(data) {
        var self = this;
        this.previous = null; this.history = []; this.selection = 'all';
        this.error = E('div', {'class': 'arthur-dashboard-error', role: 'status', 'aria-live': 'polite'});
        this.uptime = E('strong', {}, '—');
        this.clock = E('small');
        this.heroStatus = E('p', {}, '正在读取网络状态…');
        var hero = E('section', {'class': 'arthur-hero'}, [
            E('div', {}, [E('h2', {}, '你好，管理员 👋'), this.heroStatus]),
            E('div', {'class': 'arthur-uptime'}, [E('small', {}, '运行时间'), this.uptime, this.clock])
        ]);
        this.internetState = E('span', {'class': 'arthur-state'}, '正在读取');
        this.download = E('span', {'class': 'arthur-speed'}, '↓ —');
        this.upload = E('span', {'class': 'arthur-speed'}, '↑ —');
        this.internetNote = E('small', {}, 'WAN / USB 上联流量');
        var internet = E('section', {'class': 'arthur-card arthur-stat'}, [icon('globe'), E('div', {'class': 'arthur-stat-body'}, [E('h3', {}, '互联网'), this.internetState, this.download, this.upload, this.internetNote])]);
        this.devices = this.metric('已发现设备', 'devices');
        this.devices.meter.parentNode.style.display = 'none';
        this.cpu = this.metric('CPU', 'cpu', 'green');
        this.memory = this.metric('内存', 'memory', 'blue');
        this.storage = this.metric('系统存储', 'storage', 'purple');
        var stats = E('div', {'class': 'arthur-stats'}, [internet, this.devices.node, this.cpu.node, this.memory.node, this.storage.node]);
        var select = E('select', {'aria-label': '流量统计接口', 'class': 'arthur-pill'}, [E('option', {value: 'all'}, '全部上联'), E('option', {value: 'wan'}, 'WAN'), E('option', {value: 'f50'}, 'USB')]);
        select.addEventListener('change', function() {self.selection = select.value; self.history = []; self.chartDown.textContent = '—'; self.chartUp.textContent = '—'; self.chartMessage.textContent = '正在切换接口，等待下一次采样。'; self.updateChart();});
        this.chartDown = E('b', {}, '—'); this.chartUp = E('b', {}, '—');
        this.chart = svg('svg', {viewBox: '0 0 640 210', 'class': 'arthur-chart', role: 'img', 'aria-label': '上联实时下载与上传流量曲线'});
        this.chartMessage = E('div', {'class': 'arthur-chart-message'}, '正在采样，约 3 秒后显示实时速率');
        var flow = E('section', {'class': 'arthur-card'}, [this.head('网络流量', select),
            E('div', {'class': 'arthur-chart-legend'}, [E('span', {}, [E('i', {'class': 'arthur-legend-dot'}), '下载　', this.chartDown]), E('span', {}, [E('i', {'class': 'arthur-legend-dot green'}), '上传　', this.chartUp])]),
            this.chart, E('div', {'class': 'arthur-chart-caption'}, [E('span', {}, '最近 3 分钟'), E('span', {}, '实时 · 每 3 秒采样')]), this.chartMessage]);
        this.portList = E('div', {'class': 'arthur-port-list'});
        var portCard = E('section', {'class': 'arthur-card'}, [this.head('接口协商速率', E('a', {href: L.url('admin/network/arthur'), 'class': 'arthur-pill'}, '网络面板 ↗')), this.portList]);
        this.clientRows = E('tbody');
        this.clientCount = E('span', {'class': 'arthur-pill'}, '局域网邻居');
        var clients = E('section', {'class': 'arthur-card'}, [this.head('局域网设备', this.clientCount),
            E('div', {'class': 'arthur-device-scroll'}, [E('table', {'class': 'arthur-device-table'}, [E('thead', {}, [E('tr', {}, ['设备名称', 'IP 地址', '状态'].map(function(t) {return E('th', {}, t);}))]), this.clientRows])]),
            E('p', {'class': 'arthur-device-note'}, '基于 IPv4 邻居表，含缓存记录；显示最近发现的设备，不作为在线数量或单设备测速。')]);
        this.topologyUplink = E('strong', {}, '上联'); this.topologyState = E('span', {'class': 'arthur-muted'}, '读取中');
        this.topologyWan = E('span'); this.topologyUsb = E('span'); this.topologyLan = E('span');
        var router = E('div', {'class': 'arthur-router'}, [icon('wifi', 'green'), E('strong', {}, data[1].hostname || 'jdy-cookorz')]);
        var topology = E('section', {'class': 'arthur-card'}, [this.head('网络连接', E('a', {href: L.url('admin/network/arthur'), 'class': 'arthur-pill'}, '检测网络 ↗')),
            E('div', {'class': 'arthur-topology'}, [icon('globe'), this.topologyUplink, E('small', {}, this.topologyState), E('div', {'class': 'arthur-connector'}), router,
                E('div', {'class': 'arthur-topology-branches'}, [E('div', {}, [icon('globe'), E('strong', {}, 'WAN 宽带'), this.topologyWan]), E('div', {}, [icon('wifi', 'green'), E('strong', {}, '随身 WiFi'), this.topologyUsb]), E('div', {}, [icon('devices', 'purple'), E('strong', {}, '有线 LAN'), this.topologyLan])])]),
            E('p', {'class': 'arthur-device-note'}, '上联状态基于接口地址。外网可达性请运行网络质量检测。')]);
        var shortcuts = E('div', {'class': 'arthur-shortcuts'});
        this.addShortcuts(shortcuts, data[2]);
        this.proxyState = E('b'); this.bbrState = E('b'); this.nssState = E('b'); this.zramState = E('b');
        function service(title, state, note) {return E('div', {'class': 'arthur-service-row'}, [E('div', {}, [title, E('small', {}, note)]), state]);}
        var services = E('section', {'class': 'arthur-card'}, [this.head('加速与服务', E('a', {href: L.url('admin/network/arthur-performance'), 'class': 'arthur-pill'}, '管理 ↗')),
            service('OpenClash 保护', this.proxyState, '代理启用时暂停 NSS 与软件转发加速'), service('TCP 拥塞控制', this.bbrState, '显示内核当前算法'), service('转发加速', this.nssState, 'NSS / 软件模式互斥，规则状态不代表连接已命中'), service('ZRAM 压缩交换', this.zramState, '内存缓冲，状态实时读取')]);
        var columns = E('div', {'class': 'arthur-columns'}, [E('div', {'class': 'arthur-col'}, [flow, portCard, clients]), E('div', {'class': 'arthur-col'}, [topology, E('section', {'class': 'arthur-card'}, [this.head('常用功能'), shortcuts]), services])]);
        var root = E('div', {'class': 'arthur-dashboard'}, [this.error, hero, stats, columns]);
        this.update(data[0]);
        poll.add(function() {
            if (document.hidden) return Promise.resolve();
            return self.fetchData().then(function(result) {self.error.textContent = ''; self.update(result);}).catch(function() {
                self.error.textContent = '状态更新失败，以下为上次读取结果。请检查管理连接。';
                self.previous = null; self.history = [];
                self.download.textContent = '↓ —'; self.upload.textContent = '↑ —';
                self.updateChart();
            });
        }, 3);
        return root;
    },
    addShortcuts: function(container, tree) {
        var links = [];
        function walk(node, path) {ui.menu.getChildren(node).forEach(function(c) {var next = path ? path + '/' + c.name : c.name; links.push({path: next, title: c.title || ''}); walk(c, next);});}
        walk(tree, '');
        [
            ['上网设置', 'globe', 'admin/network/network'], ['无线设置', 'wifi', 'admin/network/wireless'],
            ['USB / 网络检测', 'check', 'admin/network/arthur'], ['加速与内存', 'bolt', 'admin/network/arthur-performance'],
            ['OpenClash', 'shield', 'openclash'], ['应用商店', 'box', 'store'],
            ['流量统计', 'devices', 'nlbw'], ['系统升级', 'arrow', 'admin/system/flash']
        ].forEach(function(item) {
            var entry = links.find(function(link) {return item[2].indexOf('admin/') === 0 ? link.path === item[2] : (link.path.includes(item[2]) || (item[2] === 'store' && /iStore|应用商店/i.test(link.title)));});
            if (entry) container.appendChild(E('a', {href: L.url(entry.path), 'class': 'arthur-shortcut'}, [icon(item[1], item[1] === 'wifi' || item[1] === 'bolt' ? 'green' : ''), E('span', {}, item[0])]));
        });
        if (!container.children.length) container.appendChild(E('p', {'class': 'arthur-muted'}, '请从侧栏打开管理功能'));
    },
    update: function(result) {
        var snapshot = result[0], ports = result[1], performance = result[2], info = result[3];
        var speed = sampleRates(this.previous, snapshot, this.selection);
        var aggregate = sampleRates(this.previous, snapshot, 'all');
        this.download.textContent = '↓ ' + rate(aggregate && aggregate.rx);
        this.upload.textContent = '↑ ' + rate(aggregate && aggregate.tx);
        var active = (snapshot.uplinks || []).filter(function(u) {return u.ready;});
        var names = active.map(function(u) {return u.name === 'f50' ? 'USB' : 'WAN';}).join(' + ');
        this.internetState.textContent = active.length ? '● 上联已就绪' : '● 等待上联';
        this.internetState.className = 'arthur-state ' + (active.length ? 'arthur-good' : 'arthur-warning');
        this.internetNote.textContent = active.length ? names + ' · 接口实际流量' : '连接宽带或随身 WiFi';
        this.heroStatus.textContent = active.length ? '网络管理，从容有序。' + names + ' 上联已获取地址。' : '管理中心已就绪，等待连接宽带或随身 WiFi。';
        this.uptime.textContent = duration(info.uptime);
        this.clock.textContent = snapshot.local_time ? snapshot.local_time + ' · 路由器时间' : '';
        var clients = snapshot.clients || [];
        this.devices.value.textContent = clients.length + ' 台';
        this.devices.note.textContent = 'IPv4 邻居记录，含缓存';
        var cpu = null;
        if (this.previous && snapshot.sample_time - this.previous.sample_time >= 1 && snapshot.sample_time - this.previous.sample_time <= 20 && snapshot.cpu && this.previous.cpu) {
            var total = snapshot.cpu.total - this.previous.cpu.total;
            var idle = snapshot.cpu.idle - this.previous.cpu.idle;
            if (finite(total) && total > 0 && finite(idle) && idle <= total) cpu = percent(total - idle, total);
        }
        this.cpu.value.textContent = cpu == null ? '—' : cpu + '%'; this.cpu.meter.style.width = (cpu || 0) + '%'; this.cpu.note.textContent = cpu == null ? '等待下一次采样' : '全部核心综合使用率';
        var memory = performance.memory || {};
        var memPct = finite(memory.total_kib) && finite(memory.available_kib) ? percent(Math.max(0, memory.total_kib - memory.available_kib), memory.total_kib) : null;
        this.memory.value.textContent = memPct == null ? '—' : memPct + '%'; this.memory.meter.style.width = (memPct || 0) + '%';
        this.memory.note.textContent = '可用 ' + capacity(memory.available_kib) + ' / ' + capacity(memory.total_kib);
        var storage = snapshot.storage || {}, storagePct = percent(storage.used_kib, storage.total_kib);
        this.storage.value.textContent = storagePct == null ? '—' : storagePct + '%'; this.storage.meter.style.width = (storagePct || 0) + '%';
        this.storage.note.textContent = capacity(storage.used_kib) + ' / ' + capacity(storage.total_kib) + ' · Overlay';
        if (!speed) this.history = [];
        if (speed) this.history.push({time: snapshot.sample_time, rx: speed.rx, tx: speed.tx});
        this.history = this.history.filter(function(p) {return snapshot.sample_time - p.time <= 180;}).slice(-61);
        this.chartDown.textContent = rate(speed && speed.rx); this.chartUp.textContent = rate(speed && speed.tx);
        this.chartMessage.textContent = speed ? '浏览器当前会话内采样，不保存历史流量。' : active.length ? '正在重新采样，约 3 秒后显示速率。' : '上联尚未就绪，连接后开始采样。';
        this.updateChart();
        this.portList.replaceChildren();
        (ports.ports || []).concat(ports.usb_port ? [ports.usb_port] : []).forEach(function(p) {
            var text = p.link ? finite(p.speed) && p.speed > 0 ? p.speed + ' Mbps' : '速率未知' : '未连接';
            this.portList.appendChild(E('div', {'class': 'arthur-port' + (p.link ? ' up' : '')}, [E('div', {'class': 'arthur-port-icon', 'aria-hidden': 'true'}), E('strong', {}, p.label), E('small', {}, text), E('small', {}, p.label === 'USB' ? '网卡协商' : p.duplex === 'full' ? '全双工' : p.duplex === 'half' ? '半双工' : '—')]));
        }, this);
        this.clientRows.replaceChildren(); this.clientCount.textContent = clients.length + ' 条邻居记录';
        clients.slice(0, 6).forEach(function(c) {
            this.clientRows.appendChild(E('tr', {}, [E('td', {}, [E('div', {}, c.hostname || '未命名设备'), E('span', {'class': 'arthur-mac'}, c.mac)]), E('td', {}, c.address), E('td', {'class': c.state === 'REACHABLE' ? 'arthur-good' : 'arthur-muted'}, c.state === 'REACHABLE' ? '可达' : c.state === 'STALE' ? '缓存记录' : c.state === 'PERMANENT' ? '静态记录' : '确认中')]));
        }, this);
        if (!clients.length) this.clientRows.appendChild(E('tr', {}, [E('td', {colspan: 3, 'class': 'arthur-muted'}, '暂未发现 IPv4 邻居设备')]));
        if (clients.length > 6) this.clientRows.appendChild(E('tr', {}, [E('td', {colspan: 3, 'class': 'arthur-muted'}, '首页显示前 6 条，完整记录请查看状态页面')]));
        this.topologyState.textContent = names || '等待连接'; this.topologyUplink.textContent = active.length ? '上联已获取地址' : '上联未就绪';
        this.topologyWan.textContent = active.some(function(u) {return u.name === 'wan';}) ? '已获地址' : '未就绪';
        this.topologyUsb.textContent = !ports.usb_enabled ? '已关闭' : active.some(function(u) {return u.name === 'f50';}) ? '已获地址' : ports.usb_present ? '正在连接' : '等待 USB';
        this.topologyLan.textContent = (ports.ports || []).filter(function(p) {return /^LAN/.test(p.label) && p.link;}).length + ' 个端口已连接';
        this.proxyState.textContent = performance.proxy_guard ? performance.error ? '请检查保护状态' : performance.software_flowtable || (performance.ecm_loaded && (performance.ecm_stop4 !== 1 || performance.ecm_stop6 !== 1)) ? '正在保护' : '代理保护中' : '未启用';
        this.proxyState.className = performance.error ? 'arthur-warning' : performance.proxy_guard ? 'arthur-good' : 'arthur-muted';
        this.bbrState.textContent = (performance.tcp_cc || '未知').toUpperCase();
        this.nssState.textContent = forwardingState(performance);
        this.nssState.className = performance.error ? 'arthur-warning' : 'arthur-muted';
        this.zramState.textContent = performance.zram_active ? capacity(performance.zram_size_kib) + ' 已启用' : '未启用';
        this.previous = snapshot;
    },
    updateChart: function() {
        this.chart.replaceChildren();
        var values = this.history || [], max = Math.max(1000000, ...values.map(function(p) {return Math.max(p.rx, p.tx);}));
        max = Math.ceil(max / 1000000) * 1000000;
        for (var i = 0; i <= 3; i++) {
            var y = 10 + i * 60;
            this.chart.appendChild(svg('line', {x1: 50, y1: y, x2: 635, y2: y, 'class': 'arthur-chart-grid'}));
            this.chart.appendChild(svg('text', {x: 42, y: y + 4, fill: 'var(--arthur-muted)', 'font-size': 10, 'text-anchor': 'end'}, (max * (3 - i) / 3 / 1000000).toFixed(max > 3000000 ? 0 : 1)));
        }
        this.chart.appendChild(svg('text', {x: 0, y: 207, fill: 'var(--arthur-muted)', 'font-size': 9}, 'Mbps'));
        if (values.length < 2) return;
        var now = values[values.length - 1].time;
        ['rx', 'tx'].forEach(function(direction) {
            var color = direction === 'rx' ? '#2675ff' : '#2dbf85';
            var points = values.map(function(p) {return [50 + Math.max(0, 180 - (now - p.time)) / 180 * 585, 190 - p[direction] / max * 180];});
            var path = points.map(function(p, i) {return (i ? 'L' : 'M') + p[0].toFixed(2) + ',' + p[1].toFixed(2);}).join(' ');
            this.chart.appendChild(svg('path', {d: path + ' L' + points[points.length - 1][0] + ',190 L' + points[0][0] + ',190 Z', fill: color, 'fill-opacity': '.1'}));
            this.chart.appendChild(svg('path', {d: path, fill: 'none', stroke: color, 'stroke-width': 2, 'stroke-linejoin': 'round'}));
        }, this);
    }
});
