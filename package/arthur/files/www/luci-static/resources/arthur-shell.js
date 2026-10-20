'use strict';
'require baseclass';
'require ui';

return baseclass.extend({
    __init__: function() {
        var header = document.querySelector('header .flex1');
        var sidebar = document.querySelector('#mainmenu');
        if (!header || !sidebar) return;
        var brand = sidebar.querySelector('.brand');
        if (brand) {
            brand.prepend(E('span', {'class': 'arthur-mark', 'aria-hidden': 'true'}));
            brand.href = L.url('admin', 'overview');
        }
        var search = E('input', {type: 'search', placeholder: '搜索功能，例如 USB、无线、OpenClash…',
            'aria-label': '搜索管理功能', autocomplete: 'off', 'aria-expanded': 'false', 'aria-controls': 'arthur-search-results'});
        var results = E('div', {id: 'arthur-search-results', 'class': 'arthur-search-results'});
        header.appendChild(E('div', {'class': 'arthur-search-wrap'}, [search, results]));
        var entries = [];
        var draw = function() {
            results.replaceChildren();
            var query = search.value.trim().toLocaleLowerCase();
            if (!query) { search.setAttribute('aria-expanded', 'false'); return; }
            var found = entries.filter(function(item) {return item.label.toLocaleLowerCase().includes(query) || item.path.includes(query);}).slice(0, 10);
            found.forEach(function(item) {results.appendChild(E('a', {href: L.url(item.path)}, item.label));});
            if (!found.length) results.appendChild(E('span', {}, '没有找到对应功能'));
            search.setAttribute('aria-expanded', 'true');
        };
        ui.menu.load().then(function(tree) {
            function walk(node, path, parent) {
                ui.menu.getChildren(node).forEach(function(child) {
                    var next = path ? path + '/' + child.name : child.name;
                    var title = _(child.title || child.name);
                    if (path && next.indexOf('admin/') === 0 && child.name !== 'logout') entries.push({path: next, label: parent ? parent + ' / ' + title : title});
                    walk(child, next, title);
                });
            }
            walk(tree, '', '');
            draw();
        }).catch(function() { entries = []; });
        search.addEventListener('input', draw);
        search.addEventListener('focus', draw);
        search.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') { results.replaceChildren(); search.setAttribute('aria-expanded', 'false'); search.blur(); }
            if (event.key === 'ArrowDown' && results.querySelector('a')) {event.preventDefault(); results.querySelector('a').focus();}
            if (event.key === 'Enter' && results.querySelector('a')) {event.preventDefault(); location.href = results.querySelector('a').href;}
        });
        document.addEventListener('click', function(event) {
            if (!event.target.closest('.arthur-search-wrap')) {results.replaceChildren(); search.setAttribute('aria-expanded', 'false');}
        });
        var toggle = E('button', {type: 'button', 'class': 'arthur-theme-toggle', title: '切换深浅主题', 'aria-label': '切换深浅主题'});
        function refreshToggle() { toggle.textContent = document.documentElement.dataset.arthurTheme === 'dark' ? '☾' : '☼'; }
        refreshToggle();
        toggle.addEventListener('click', function() {
            var theme = document.documentElement.dataset.arthurTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.dataset.arthurTheme = theme;
            try {localStorage.setItem('arthur-theme', theme);} catch (e) {}
            refreshToggle();
        });
        var logout = E('a', {href: L.url('admin', 'logout'), 'class': 'arthur-account', title: '退出登录'}, [
            E('span', {'class': 'arthur-avatar', 'aria-hidden': 'true'}, 'J'),
            E('span', {}, ['管理中心', E('small', {}, '退出登录 ↗')])
        ]);
        document.querySelector('header .container').appendChild(E('div', {'class': 'arthur-top-actions'}, [toggle, logout]));
        var footer = E('div', {'class': 'arthur-side-footer'});
        footer.innerHTML = '<svg viewBox="0 0 140 70" aria-hidden="true"><defs><linearGradient id="arthur-router-body" x2="0" y2="1"><stop stop-color="#50637a"/><stop offset="1" stop-color="#1a2738"/></linearGradient></defs><path d="M27 37V7M114 37V7" stroke="#7e91a9" stroke-width="3" stroke-linecap="round"/><path d="M18 38L31 28H110L124 38V56H18Z" fill="url(#arthur-router-body)" stroke="#60748f"/><path d="M18 39H124M29 48H52" stroke="#192d45" stroke-width="3"/><path d="M31 48H36M41 48H46" stroke="#3c9cff" stroke-width="2"/><circle cx="112" cy="48" r="2" fill="#37ca99"/></svg>';
        footer.appendChild(E('b', {}, 'jdy-cookorz'));
        footer.appendChild(E('span', {}, '京东云亚瑟 · AX1800 Pro'));
        footer.appendChild(E('span', {}, [E('i', {'class': 'arthur-dot'}), '管理会话已连接']));
        sidebar.appendChild(footer);
    }
});
