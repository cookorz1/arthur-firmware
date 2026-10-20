'use strict';
'require view';
'require rpc';
'require form';
'require uci';
'require poll';
'require dom';

var callPerformance = rpc.declare({object: 'arthur', method: 'performance', expect: {'': {}}});
var callRelease = rpc.declare({object: 'arthur', method: 'release_memory', expect: {'': {}}});

function mib(value) {
    return typeof value === 'number' ? (value / 1024).toFixed(1) + ' MiB' : '—';
}

return view.extend({
    load: function() {
        return Promise.all([uci.load('arthur'), callPerformance()]);
    },

    updateStatus: function(data) {
        var protectionError = ['flowtable_conflict', 'nss_controls_missing', 'nss_drain_failed'].indexOf(data.error) !== -1;
        var stopped = (!data.ecm_loaded || (data.ecm_stop4 === 1 && data.ecm_stop6 === 1)) && !protectionError;
        var allowed = data.ecm_loaded && data.ecm_stop4 === 0 && data.ecm_stop6 === 0;
        var nss;
        if (data.proxy_guard)
            nss = stopped ? _('OpenClash 兼容保护中：暂停 NSS 转发加速') : _('正在保护，请稍候；若持续出现请查看错误提示');
        else if (data.reason === 'off')
            nss = _('已选择关闭 NSS 转发加速');
        else if (data.reason === 'qos')
            nss = _('检测到 SQM/QoS：暂停 NSS，保留整形效果');
        else if (data.reason === 'steering')
            nss = _('软件包分载已开启：暂停 NSS，避免叠加；使用 NSS 时请关闭接口全局设置中的软件包分载');
        else
            nss = allowed ? _('允许 NSS 转发加速；实际命中取决于流量与驱动') : _('NSS 转发加速未就绪');
        var errors = {
            flowtable_conflict: _('fw4 流量卸载未能关闭，兼容保护未完成'),
            nss_controls_missing: _('ECM 控制节点不可用，无法确认暂停状态'),
            nss_drain_failed: _('旧加速连接清退失败，OpenClash 启动保护会阻止继续'),
            nss_load_failed: _('ECM 模块未加载，请查看系统日志'),
            tcp_algorithm_unavailable: _('选定的 TCP 拥塞算法不可用，当前算法保持原值')
        };
        var count4 = typeof data.accelerated_ipv4 === 'number' ? data.accelerated_ipv4 : '—';
        var count6 = typeof data.accelerated_ipv6 === 'number' ? data.accelerated_ipv6 : '—';
        var desiredZram = uci.get('arthur', 'performance', 'zram_enabled') !== '0';
        var zram = data.zram_active ? _('已启用') + ' · ' + mib(data.zram_used_kib) + ' / ' + mib(data.zram_size_kib) : _('未启用');
        if (desiredZram !== !!data.zram_active)
            zram += _('（设置将在下次重启后生效）');
        var fields = [
            [_('TCP 拥塞控制 / 默认队列'), (data.tcp_cc || '—') + ' / ' + (data.default_qdisc || '—')],
            [_('NSS 驱动'), data.nss_driver ? _('已加载') : _('未加载')],
            [_('NSS 转发状态'), nss],
            [_('NSS 加速连接数（全机）'), 'IPv4: ' + count4 + ' · IPv6: ' + count6],
            [_('无线 NSS 驱动'), data.wifi_nss ? _('已启用，独立于路由转发开关') : _('未启用或无法读取')],
            [_('ZRAM 压缩交换'), zram],
            [_('代理进程物理内存'), mib(data.proxy_rss_kib)],
            [_('构建版本'), data.build || '—']
        ];
        if (data.error)
            fields.push([_('需要关注'), errors[data.error] || _('未知错误，请查看系统日志')]);
        dom.content(this.statusRows, fields.map(function(field) {
            return E('tr', {'class': 'tr'}, [E('td', {'class': 'td'}, [field[0]]), E('td', {'class': 'td'}, [field[1]])]);
        }));
        var memory = data.memory || {};
        var available = memory.available_kib || 0;
        var total = memory.total_kib || 0;
        this.memoryBar.max = total || 1;
        this.memoryBar.value = Math.max(0, total - available);
        var warning = total && available < 32768 ? _(' · 可用内存偏低，请检查大规则集或高占用应用；缓存清理不能释放进程占用。') : '';
        dom.content(this.memoryText, [
            _('可用 ') + mib(memory.available_kib) + ' / ' + _('总内存 ') + mib(memory.total_kib) +
            ' · ' + _('缓存参考 ') + mib(memory.cached_kib) + ' · ' +
            _('交换已用 ') + mib(memory.swap_used_kib) + ' / ' + mib(memory.swap_total_kib) + warning
        ]);
    },

    releaseMemory: function(event) {
        if (this.releasing)
            return Promise.resolve();
        var button = event.currentTarget;
        this.releasing = true;
        button.disabled = true;
        dom.content(this.releaseMessage, [_('正在同步数据并回收缓存，请稍候……')]);
        return callRelease().then(L.bind(function(result) {
            var reasons = {
                busy: _('另一次清理正在进行'), cooldown: _('请间隔至少 60 秒再清理'),
                sync_failed: _('数据同步未完成，已取消清理'), unavailable: _('系统未提供缓存回收接口')
            };
            if (!result.ok) {
                dom.content(this.releaseMessage, [reasons[result.reason] || _('清理未完成，请查看系统日志')]);
                return;
            }
            var before = (result.before || {}).available_kib;
            var after = (result.after || {}).available_kib;
            dom.content(this.releaseMessage, [_('缓存回收完成，可用内存：') + mib(before) + ' → ' + mib(after) + _('。实际变化取决于缓存和正在运行的应用。')]);
            return callPerformance().then(L.bind(this.updateStatus, this));
        }, this)).catch(L.bind(function() {
            dom.content(this.releaseMessage, [_('操作未完成或连接中断，请稍后刷新状态，不要连续点击。')]);
        }, this)).finally(L.bind(function() {
            this.releasing = false;
            button.disabled = false;
        }, this));
    },

    render: function(data) {
        var m = new form.Map('arthur', _('优化设置'), _('保存并应用后生效；ZRAM 的开启或关闭需要重启路由器。'));
        var s = m.section(form.NamedSection, 'performance', 'performance');
        s.anonymous = true;
        var o = s.option(form.ListValue, 'tcp_cc', _('TCP 拥塞控制'));
        o.value('bbr', _('BBR（默认）'));
        o.value('cubic', _('Cubic'));
        o.default = 'bbr';
        o.rmempty = false;
        o.description = _('影响路由器本机及代理出口的内核 TCP 连接，不改变终端设备的拥塞算法，也不为 UDP/QUIC 提速；新连接生效。');
        o = s.option(form.ListValue, 'nss_mode', _('NSS 转发加速'));
        o.value('auto', _('自动兼容（默认）'));
        o.value('off', _('关闭'));
        o.default = 'auto';
        o.rmempty = false;
        o.description = _('OpenClash 已启用、进程仍运行或 SQM/QoS 工作时暂停 NSS 转发；关闭代理及整形后恢复。fw4 软件/硬件流量卸载保持关闭，不叠加加速。');
        o = s.option(form.Flag, 'zram_enabled', _('开启 ZRAM 压缩交换'));
        o.default = '1';
        o.rmempty = false;
        o.description = _('全新安装默认 128 MiB 逻辑交换空间，按需使用压缩内存，不是额外物理内存。更改下次重启生效，不会强制换出或结束应用。');

        this.statusRows = E('tbody');
        this.memoryBar = E('progress', {'style': 'width:100%;height:20px', 'max': 1, 'value': 0});
        this.memoryText = E('p');
        this.releaseMessage = E('p', {'class': 'cbi-section-descr'});
        this.updateStatus(data[1]);
        poll.add(L.bind(function() {
            return callPerformance().then(L.bind(this.updateStatus, this));
        }, this), 5);
        return m.render().then(L.bind(function(formNode) {
            return E('div', {}, [
                E('h2', {}, [_('加速与内存')]),
                E('div', {'class': 'cbi-section'}, [
                    E('h3', {}, [_('运行状态')]),
                    E('table', {'class': 'table'}, [this.statusRows]),
                    E('p', {'class': 'cbi-section-descr'}, [_('NSS 不能替代 OpenClash 的代理加解密。USB 流量能否被 NSS 加速由驱动和连接类型决定，连接数是全机统计，不代表 USB 已被加速。默认 FQ 只影响新建队列，保留现有 SQM/CAKE/HTB。')])
                ]),
                E('div', {'class': 'cbi-section'}, [
                    E('h3', {}, [_('内存状态与手动回收')]),
                    this.memoryBar, this.memoryText,
                    E('p', {'class': 'cbi-section-descr'}, [_('Linux 会按需回收缓存，可用内存比空闲内存更有参考价值。手动回收仅清理干净缓存，不会结束 OpenClash、删除临时文件或清空连接；频繁清理可能降低性能。')]),
                    E('button', {'class': 'cbi-button cbi-button-action', 'type': 'button',
                        'click': L.bind(this.releaseMemory, this)}, [_('释放缓存内存')]),
                    this.releaseMessage
                ]), formNode
            ]);
        }, this));
    }
});
