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
        const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error('Page error:',e.message);});
        page.on('console',m=>{if(m.type()==='error')console.error('Browser console:',m.text());});
        const dir=path.resolve('logs/ui');
        const open=async name=>page.goto(pathToFileURL(path.join(dir,name+'.html')).href);
        await open('dashboard');
        await page.waitForFunction(()=>window.previewReady===true || window.previewError);
        assert.equal(await page.evaluate(()=>window.previewError || ''),'');
        assert.equal(errors.length,0,errors.join('\n'));
        const version=fs.readFileSync('VERSION','utf8').trim();
        async function checkAvatar(selector) {
            const result=await page.locator(selector).first().evaluate(async element=>{
                const background=getComputedStyle(element).backgroundImage;
                const match=background.match(/^url\(["']?(.*?)["']?\)$/);
                if(!match)return {error:'Avatar background missing: '+background};
                const image=new Image();
                return await new Promise(resolve=>{
                    image.onload=()=>resolve({width:image.naturalWidth,height:image.naturalHeight,url:image.src});
                    image.onerror=()=>resolve({error:'Avatar failed to load'});
                    image.src=match[1];
                });
            });
            assert.ok(!result.error,JSON.stringify(result));
            assert.ok(result.url.includes('/arthur/avatar.jpg'),JSON.stringify(result));
            assert.ok(result.width>0&&result.height>0,JSON.stringify(result));
        }
        await checkAvatar('.arthur-mark');
        await checkAvatar('.arthur-avatar');
        assert.ok((await page.locator('.sidenav-header .brand').innerText()).includes('by-cookorz'));
        assert.ok((await page.locator('.arthur-side-footer').innerText()).includes('v'+version));
        await page.screenshot({path:path.join(dir,'dashboard-desktop.png'),fullPage:true});
        assert.ok((await page.locator('.arthur-hero').innerText()).includes('WAN + USB'));
        assert.equal(await page.locator('.arthur-port').count(),5);
        assert.ok((await page.locator('.arthur-device-table').innerText()).includes('缓存记录'));
        await page.getByRole('searchbox').fill('USB');
        assert.ok(await page.locator('.arthur-search-results a').count()>0);
        await page.getByRole('searchbox').press('Escape');
        await page.getByRole('button',{name:'切换深浅主题'}).click();
        assert.equal(await page.locator('html').getAttribute('data-arthur-theme'),'dark');
        const contrast=await page.locator('.arthur-stat strong').first().evaluate(el=>{
            function luminance(css) {const rgb=css.match(/[\d.]+/g).slice(0,3).map(Number).map(c=>{c/=255;return c<=.04045?c/12.92:Math.pow((c+.055)/1.055,2.4);});return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;}
            const fg=luminance(getComputedStyle(el).color),bg=luminance(getComputedStyle(el.closest('.arthur-card')).backgroundColor);
            return (Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05);
        });
        assert.ok(contrast>=4.5,'Dark metric contrast: '+contrast);
        await page.screenshot({path:path.join(dir,'dashboard-dark.png'),fullPage:true});
        await page.getByRole('button',{name:'切换深浅主题'}).click();
        const layout=[];
        for(const width of [1536,1024,768,390,320]) {
            await page.setViewportSize({width,height:1000});
            const result=await page.evaluate(()=>({width:innerWidth,overflow:document.querySelector('.main-right').scrollWidth-document.querySelector('.main-right').clientWidth,
                cards:[...document.querySelectorAll('.arthur-card')].filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+1||r.left<0;}).length}));
            layout.push(result);assert.ok(result.overflow<=1,JSON.stringify(result));assert.equal(result.cards,0,JSON.stringify(result));
            if(width===390) {
                assert.ok(await page.getByRole('button',{name:'打开导航菜单'}).isVisible());
                await page.screenshot({path:path.join(dir,'dashboard-mobile.png'),fullPage:true});
            }
        }
        await page.setViewportSize({width:1536,height:1000});
        await open('login');
        await checkAvatar('.arthur-mark');
        assert.ok((await page.locator('.arthur-login-footer').innerText()).includes('v'+version));
        assert.ok((await page.locator('.arthur-login-footer').innerText()).includes('by-cookorz'));
        assert.ok(!(await page.locator('body').innerText()).includes('@ARTHUR_VERSION@'));
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

