const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const file = path.join(__dirname, '../package/arthur/files/www/luci-static/resources/view/arthur/network.js');
const code = fs.readFileSync(file, 'utf8');
let flags = [];
let polling = [];
let diagnoseCalls = 0;
let diagnoseResponse;
const E = (tag, attrs, children) => ({tag, attrs: attrs || {}, children: children || []});
function MapStub(name) { this.config = name; }
MapStub.prototype.section = function() {
    return {option: function(type, name) { const flag = {name}; flags.push(flag); return flag; }};
};
MapStub.prototype.render = async function() { return E('form', {config: this.config}); };
const context = {
    view: {extend: value => value}, rpc: {declare: spec => async () => {
        if (spec.method === 'diagnose') { diagnoseCalls++; return diagnoseResponse; }
        return {ports: []};
    }},
    form: {Map: MapStub, NamedSection: {}, Flag: {}}, uci: {load: async () => true},
    poll: {add: (fn, seconds) => polling.push({fn, seconds})},
    dom: {content: (node, children) => { node.children = children; }},
    L: {bind: (fn, owner) => fn.bind(owner)}, E, _: text => text, Promise
};
const view = vm.runInNewContext('(function(){\n' + code + '\n})()', context);
const data = {ports: [
    {label: 'WAN', device: 'wan', present: true, link: true, speed: 1000, duplex: 'full'},
    {label: 'LAN1', device: 'lan1', present: true, link: true, speed: 100, duplex: 'half'},
    {label: 'LAN2', device: 'lan2', present: true, link: false, speed: null},
    {label: 'LAN3', device: 'lan3', present: true, link: true, speed: null}
], usb_enabled: true, usb_present: true, usb_device: 'usb0', usb_bus_speed: 5000,
usb_port: {label: 'USB', device: 'usb0', present: true, link: true, speed: 480, duplex: 'unknown'}};
function allText(node) {
    if (typeof node === 'string') return node;
    if (Array.isArray(node)) return node.map(allText).join(' ');
    return node ? allText(node.children) : '';
}
(async () => {
    const rendered = await view.render([true, data]);
    const text = allText(rendered);
    for (const expected of ['WAN', 'LAN1', 'LAN2', 'LAN3', 'USB', '1000 Mbps', '100 Mbps', '480 Mbps', '5000 Mbps', '未连接', '无法读取'])
        assert.ok(text.includes(expected), expected);
    assert.equal(flags.length, 1);
    assert.equal(flags[0].name, 'enabled');
    assert.equal(flags[0].rmempty, false);
    assert.equal(flags[0].default, '1');
    assert.equal(polling[0].seconds, 3);
    view.updateStatus({...data, usb_enabled: false});
    assert.ok(allText(view.usbStatus).includes('已关闭'));
    assert.ok(allText(view.usbSpeed).includes('5000 Mbps'));
    view.updateStatus({...data, usb_present: false, usb_bus_speed: null});
    assert.ok(allText(view.usbSpeed).includes('未连接'));
    assert.ok(allText(view.usbStatus).includes('等待连接随身 WiFi'));
    view.updateStatus({...data, usb_bus_speed: null});
    assert.ok(allText(view.usbSpeed).includes('无法读取'));
    view.updateStatus({...data, usb_enabled: true, usb_present: true, usb_up: true, usb_device: 'usb0'});
    assert.ok(allText(view.usbStatus).includes('usb0'));
    assert.ok(!allText(rendered).includes('F50'));
    assert.ok(allText(rendered).includes('网络质量检测'));
    const sample = {timestamp: 1792488000, uplinks: [
        {interface: 'wan', up: true, ready: true, address: '192.0.2.2',
            probes: [{target: '223.5.5.5', loss: 0, latency: 12.5}], https: [{reachable: true}]},
        {interface: 'f50', up: true, ready: true, address: '192.0.2.3',
            probes: [{target: '119.29.29.29', loss: 0, latency: 40}], https: [{reachable: false}]}
    ]};
    const button = {disabled: false};
    let finish;
    diagnoseResponse = new Promise(resolve => { finish = resolve; });
    const pending = view.runDiagnosis({currentTarget: button});
    assert.equal(button.disabled, true);
    await view.runDiagnosis({currentTarget: button});
    assert.equal(diagnoseCalls, 1);
    finish(sample);
    await pending;
    assert.equal(button.disabled, false);
    assert.ok(allText(view.healthRows).includes('本次外网检测可达'));
    assert.ok(allText(view.healthRows).includes('IP 可达，HTTPS 检测未通过'));
    assert.ok(allText(view.healthRows).includes('12.5 ms'));
    assert.ok(allText(view.healthRows).includes('随身 WiFi（USB）'));
    // ICMP blocking alone must not turn a successful HTTPS check into an outage.
    view.showDiagnosis({uplinks: [{...sample.uplinks[0], probes: [{loss: 100, latency: null}]}]});
    assert.ok(allText(view.healthRows).includes('本次外网检测可达'));
    view.showDiagnosis({uplinks: [{...sample.uplinks[0], up: false, ready: false, address: '', probes: [], https: []}]});
    assert.ok(allText(view.healthRows).includes('接口未连接'));
    diagnoseResponse = Promise.reject(new Error('RPC failed'));
    await view.runDiagnosis({currentTarget: button});
    assert.ok(allText(view.healthStatus).includes('本次检测失败'));
    assert.equal(button.disabled, false);
    console.log('LuCI rendering, USB labels, diagnostics, duplicate prevention and failure recovery passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
