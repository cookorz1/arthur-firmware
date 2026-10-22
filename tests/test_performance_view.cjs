const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../package/arthur/files/www/luci-static/resources/view/arthur/performance.js'), 'utf8');
let releaseResponse;
let releaseCalls = 0;
let options = [];
let callbacks = [];
const config = {zram_enabled: '1'};
const E = (tag, attrs, children) => ({tag, attrs: attrs || {}, children: children || []});
function MapStub() {}
MapStub.prototype.section = () => ({option: (type, name) => {
    const option = {name, values: [], value: function(key, label) { this.values.push({key, label}); }};
    options.push(option);
    return option;
}});
MapStub.prototype.render = async () => E('form');
const sample = {
    proxy_guard: true, nss_driver: true, ecm_loaded: true, ecm_stop4: 1, ecm_stop6: 1,
    wifi_nss: true, tcp_cc: 'bbr', default_qdisc: 'fq', accelerated_ipv4: 0, accelerated_ipv6: 0,
    reason: 'openclash', error: '', zram_active: true, zram_size_kib: 131072,
    zram_used_kib: 4096, proxy_rss_kib: 64000, build: 'abc123',
    memory: {total_kib: 416000, available_kib: 160000, cached_kib: 75000,
        swap_total_kib: 131072, swap_used_kib: 4096}
};
const context = {
    view: {extend: value => value},
    rpc: {declare: spec => async () => {
        if (spec.method === 'release_memory') { releaseCalls++; return releaseResponse; }
        return sample;
    }},
    form: {Map: MapStub, NamedSection: {}, Flag: {}, ListValue: {}},
    uci: {load: async () => true, get: (name, section, option) => config[option]},
    poll: {add: (fn, seconds) => callbacks.push({fn, seconds})},
    dom: {content: (node, children) => { node.children = children; }},
    L: {bind: (fn, owner) => fn.bind(owner)}, E, _: text => text, Promise
};
const view = vm.runInNewContext('(function(){\n' + code + '\n})()', context);
function text(node) {
    if (typeof node === 'string') return node;
    if (Array.isArray(node)) return node.map(text).join(' ');
    return node ? text(node.children) : '';
}
(async () => {
    const rendered = await view.render([true, sample]);
    assert.ok(text(rendered).includes('OpenClash 兼容保护中'));
    assert.ok(text(rendered).includes('bbr / fq'));
    assert.ok(text(rendered).includes('abc123'));
    assert.equal(callbacks[0].seconds, 5);
    assert.deepEqual(options.map(x => x.name), ['tcp_cc', 'nss_mode', 'usb_rps', 'zram_enabled']);
    assert.deepEqual(options[1].values.map(x => x.key), ['auto', 'software', 'off']);
    assert.equal(options[1].default, 'software');
    assert.equal(options[2].default, '1');
    view.updateStatus({...sample, software_flowtable: false, usb_rps: {
        state: 'active', device: 'usb0', queues: [{queue: 'rx-0', mask: 'b'}]
    }});
    assert.ok(text(view.statusRows).includes('OpenClash 兼容保护中'));
    assert.ok(text(view.statusRows).includes('OpenClash 运行时保留'));
    assert.ok(text(view.statusRows).includes('rx-0=b'));
    view.updateStatus({...sample, usb_rps: {state: 'waiting', queues: []}});
    assert.ok(text(view.statusRows).includes('等待连接随身 WiFi'));
    view.updateStatus({...sample, proxy_guard: false, reason: 'eligible', ecm_stop4: 0, ecm_stop6: 0});
    assert.ok(text(view.statusRows).includes('允许 NSS 转发加速'));
    view.updateStatus({...sample, proxy_guard: false, reason: 'eligible', mode: 'software',
        active_backend: 'software', software_flowtable: true, ecm_loaded: false});
    assert.ok(text(view.statusRows).includes('软件流量分载规则已启用'));
    assert.ok(text(view.statusRows).includes('不等于测速连接已命中'));
    view.updateStatus({...sample, software_flowtable: true});
    assert.ok(text(view.statusRows).includes('正在保护'));
    view.updateStatus({...sample, proxy_guard: false, reason: 'eligible', mode: 'software',
        active_backend: 'off', software_flowtable: false, error: 'nss_unload_failed'});
    assert.ok(text(view.statusRows).includes('ECM 未能退出'));
    assert.ok(!text(view.statusRows).includes('规则已启用'));
    view.updateStatus({...sample, proxy_guard: false, reason: 'qos'});
    assert.ok(text(view.statusRows).includes('保留整形效果'));
    config.zram_enabled = '0';
    view.updateStatus(sample);
    assert.ok(text(view.statusRows).includes('下次重启'));
    view.updateStatus({...sample, memory: {...sample.memory, available_kib: 16000}});
    assert.ok(text(view.memoryText).includes('可用内存偏低'));
    const button = {disabled: false};
    let finish;
    releaseResponse = new Promise(resolve => { finish = resolve; });
    const pending = view.releaseMemory({currentTarget: button});
    await view.releaseMemory({currentTarget: button});
    assert.equal(releaseCalls, 1);
    assert.equal(button.disabled, true);
    finish({ok: true, before: {available_kib: 100000}, after: {available_kib: 120000}});
    await pending;
    assert.equal(button.disabled, false);
    assert.ok(text(view.releaseMessage).includes('缓存回收完成'));
    releaseResponse = {ok: false, reason: 'cooldown'};
    await view.releaseMemory({currentTarget: button});
    assert.ok(text(view.releaseMessage).includes('60 秒'));
    releaseResponse = Promise.reject(new Error('RPC failed'));
    await view.releaseMemory({currentTarget: button});
    assert.equal(button.disabled, false);
    assert.ok(text(view.releaseMessage).includes('操作未完成'));
    console.log('Performance view: guarded NSS, BBR, deferred ZRAM, memory pressure and cache action checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
