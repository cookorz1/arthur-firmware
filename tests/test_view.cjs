const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const file = path.join(__dirname, '../package/arthur/files/www/luci-static/resources/view/arthur/network.js');
const code = fs.readFileSync(file, 'utf8');
let flags = [];
let polling = [];
const E = (tag, attrs, children) => ({tag, attrs: attrs || {}, children: children || []});
function MapStub(name) { this.config = name; }
MapStub.prototype.section = function() {
    return {option: function(type, name) { const flag = {name}; flags.push(flag); return flag; }};
};
MapStub.prototype.render = async function() { return E('form', {config: this.config}); };
const context = {
    view: {extend: value => value}, rpc: {declare: () => async () => ({ports: []})},
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
], usb_enabled: true, usb_present: false, usb_device: ''};
function allText(node) {
    if (typeof node === 'string') return node;
    if (Array.isArray(node)) return node.map(allText).join(' ');
    return node ? allText(node.children) : '';
}
(async () => {
    const rendered = await view.render([true, data]);
    const text = allText(rendered);
    for (const expected of ['WAN', 'LAN1', 'LAN2', 'LAN3', '1000 Mbps', '100 Mbps', '未连接', '无法读取', '等待连接 F50'])
        assert.ok(text.includes(expected), expected);
    assert.equal(flags.length, 1);
    assert.equal(flags[0].name, 'enabled');
    assert.equal(flags[0].rmempty, false);
    assert.equal(flags[0].default, '1');
    assert.equal(polling[0].seconds, 3);
    view.updateStatus({...data, usb_enabled: false});
    assert.ok(allText(view.usbStatus).includes('已关闭'));
    view.updateStatus({...data, usb_enabled: true, usb_present: true, usb_up: true, usb_device: 'usb0'});
    assert.ok(allText(view.usbStatus).includes('usb0'));
    console.log('LuCI view rendering, link labels, USB states and polling checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
