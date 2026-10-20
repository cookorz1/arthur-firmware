/* Browser QA of the real dashboard view, shell and login template with labelled fixture data. */
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
    const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
    try {
        const page=await browser.newPage({viewport:{width:1536,height:1100},deviceScaleFactor:1});
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        const dir=path.resolve('logs/ui');
        const open=async name=>page.goto(pathToFileURL(path.join(dir,name+'.html')).href);
        await open('dashboard');
        await page.waitForFunction(()=>window.previewReady===true);
        assert.equal(errors.length,0,errors.join('\n'));
        await page.locator('.arthur-dashboard').screenshot({path:path.join(dir,'dashboard-content.png')});
        await page.screenshot({path:path.join(dir,'dashboard-desktop.png'),fullPage:true});
        assert.ok((await page.locator('.arthur-hero').innerText()).includes('WAN + USB'));
        assert.equal(await page.locator('.arthur-port').count(),5);
        assert.ok((await page.locator('.arthur-device-table').innerText()).includes('缓存记录'));
        await page.getByRole('searchbox').fill('USB');
        assert.ok(await page.locator('.arthur-search-results a').count()>0);
        await page.getByRole('searchbox').press('Escape');
        await page.getByRole('button',{name:'切换深浅主题'}).click();
        assert.equal(await page.locator('html').getAttribute('data-arthur-theme'),'dark');
        await page.screenshot({path:path.join(dir,'dashboard-dark.png'),fullPage:true});
        await page.getByRole('button',{name:'切换深浅主题'}).click();
        const layout=[];
        for(const width of [1536,1024,768,390,320]) {
            await page.setViewportSize({width,height:1000});
            const result=await page.evaluate(()=>({width:innerWidth,overflow:document.querySelector('.main-right').scrollWidth-document.querySelector('.main-right').clientWidth,
                cards:[...document.querySelectorAll('.arthur-card')].filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+1||r.left<0;}).length}));
            layout.push(result);assert.ok(result.overflow<=1,JSON.stringify(result));assert.equal(result.cards,0,JSON.stringify(result));
            if(width===390) await page.screenshot({path:path.join(dir,'dashboard-mobile.png'),fullPage:true});
        }
        await page.setViewportSize({width:1536,height:1000});
        await open('login');
        assert.equal(await page.locator('form').getAttribute('method'),'post');
        await page.getByLabel('管理密码',{exact:true}).fill('preview-only');
        await page.getByRole('button',{name:'显示密码',exact:true}).click();
        assert.equal(await page.locator('[name=luci_password]').getAttribute('type'),'text');
        await page.getByRole('button',{name:'隐藏密码',exact:true}).click();
        await page.getByLabel('管理密码',{exact:true}).fill('');
        await page.screenshot({path:path.join(dir,'login-desktop.png'),fullPage:true});
        await page.setViewportSize({width:390,height:844});
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
        await page.screenshot({path:path.join(dir,'login-mobile.png'),fullPage:true});
        assert.equal(errors.length,0,errors.join('\n'));
        fs.writeFileSync(path.join(dir,'layout-checks.json'),JSON.stringify({layout,page_errors:errors,fixture_data:true},null,2));
        console.log('Theme rendering, WAN/USB cards, real view execution, dark toggle, menu search, login form and five viewport checks passed.');
    } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
