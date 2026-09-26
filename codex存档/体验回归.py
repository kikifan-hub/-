"""独立浏览器上下文验收确定性体验缺陷，不访问用户真实存档。"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        await page.goto((Path(__file__).resolve().parents[1] / 'index.html').as_uri())
        async def check(name, code):
            assert await page.evaluate(code), name
            print('PASS', name)
        await check('过期手势轻放', '''()=>{input.samples=[{x:0,y:0,t:performance.now()-900},{x:300,y:0,t:performance.now()-700}];return gestureVel().x===0}''')
        await check('即时用力甩出保留', '''()=>{const t=performance.now();input.samples=[{x:0,y:0,t:t-30},{x:90,y:0,t}];return gestureVel().x>280}''')
        await check('自由屋保险箱限额', '''()=>{startFree();G.items=[makeItem({t:'safe',x:100,s:'floor'})];for(let i=0;i<200;i++)spawnFree();return G.items.filter(i=>i.type.unbreakable).length===1}''')
        await check('自由屋清理失效对象', '''()=>{G.items.forEach(i=>i.state='gone');G.freeSpawnT=10;step(1/60,1/60);return G.items.length===0&&G.fragments.length<=150}''')
        await check('通关后退出保存新增收益', '''()=>{startLevel(0);G.items.slice(0,6).forEach(smash);G.panelCount=1;bankScore();const before=Save.data.score;smash(G.items.find(i=>i.state!=='gone'));const expected=G.score-G.banked;showLevelSelect();return Save.data.score===before+expected}''')
        await check('换关不串写星级记录', '''()=>{startLevel(0);G.items.slice(0,6).forEach(smash);G.panelCount=1;bankScore();const next=Save.data.best[1];startLevel(1);return Save.data.best[1]===next&&G.score===0}''')
        await check('重复结算不重复入账', '''()=>{startLevel(0);G.items.slice(0,6).forEach(smash);bankScore();const n=Save.data.score;bankScore();return n===Save.data.score}''')
        await check('异常存档安全恢复', '''()=>{localStorage.setItem(SAVE_KEY,JSON.stringify({score:'6000',stars:[99,-2,'1'],best:['bad'],vol:12,gifts:['invalid','chair','chair']}));Save.load();Save.addScore(10);return Save.data.score===10&&Save.data.stars.join(',')==='3,0,0,0,0,0'&&Save.data.vol===1&&Save.data.gifts.join(',')==='chair'}''')
        await check('保存失败有反馈', '''()=>{const original=Storage.prototype.setItem;try{Storage.prototype.setItem=()=>{throw Error('storage unavailable')};return Save.save()===false&&G.toast.includes('保存失败')}finally{Storage.prototype.setItem=original}}''')
        await page.evaluate("Save.data.gifts=GIFTS.map(g=>g.id);openScreen('hall')")
        await page.wait_for_timeout(300)
        await page.locator('canvas').screenshot(path='/tmp/zm_hall_fixed.png')
        await check('满收藏徽章不越界', '''()=>{const texts=[];const original=ctx.fillText;ctx.fillText=function(t,x,y,...rest){texts.push({t,x,y});return original.call(this,t,x,y,...rest)};try{drawHall(ctx,0)}finally{ctx.fillText=original}const badges=texts.filter(p=>String(p.t).startsWith('🏅 '));return badges.length===12&&badges.every(p=>p.y<830)}''')
        await page.evaluate('startLevel(0);pauseGame(true)')
        before = await page.evaluate('({time:G.comboT,items:G.items.map(i=>[i.x,i.y,i.state])})')
        await page.wait_for_timeout(500)
        assert before == await page.evaluate('({time:G.comboT,items:G.items.map(i=>[i.x,i.y,i.state])})'), '暂停冻结'
        print('PASS 暂停冻结物理')
        await check('恢复清除旧手势', '''()=>{pauseGame(false);return !G.paused&&input.samples.length===0&&!input.active}''')
        await check('小控件透明命中区', '''()=>inRect({x:31,y:9},{x:14,y:14,w:34,h:34})''')
        await page.set_viewport_size({'width':844,'height':390})
        await page.wait_for_timeout(100)
        await check('横屏暂停', '''()=>G.paused&&isLandscape()''')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(100)
        await check('竖屏后显式恢复', '''()=>{const paused=G.paused;pauseGame(false);return paused&&!G.paused}''')
        for i in range(6):
            await page.evaluate(f'startLevel({i});G.toastT=0')
            await page.wait_for_timeout(350)
            await page.locator('canvas').screenshot(path=f'/tmp/zm_unified_room_{i}.png')
        print('PASS 六场景绘制无异常')
        await check('每关增加4件独立真实陈设', '''()=>{G.suspendedRun=null;for(let i=0;i<6;i++){startLevel(i);if(G.items.length!==LEVELS[i].items.length+4||G.items.filter(it=>it.sceneProp).length!==4)return false}return true}''')
        await check('返回保留完整现场', '''()=>{startLevel(0);smash(G.items[0]);const items=G.items,score=G.score;suspendRun();const held=G.suspendedRun;resumeRun();return held.items===items&&G.items===items&&G.score===score&&!G.paused&&G.items[0].state==='gone'}''')
        await check('未通关现场不提前入账', '''()=>{startLevel(0);const saved=Save.data.score;smash(G.items[0]);suspendRun();const good=Save.data.score===saved;resumeRun();return good}''')
        await check('礼品试玩不消耗收藏且不给奖励', '''()=>{G.suspendedRun=null;Save.data.gifts=['duck'];startGiftTrial(GIFTS[0]);const it=G.items.find(i=>i.giftTrial);const saved=Save.data.score;it.source='chain';smash(it);return Save.data.score===saved&&Save.hasGift('duck')&&G.combo===0}''')
        await check('试玩期间保留原关卡现场', '''()=>{G.suspendedRun=null;startLevel(0);const items=G.items;suspendRun();startGiftTrial(GIFTS[0]);showLevelSelect();resumeRun();return G.level===0&&!G.free&&G.items===items}''')
        await check('礼品房隔离补货与解锁', '''()=>{G.suspendedRun=null;Save.data.stars[2]=0;startGiftTrial(GIFTS[0]);G.freeSpawnT=-1;for(let i=0;i<60;i++)step(1/60,1/60);return G.giftPractice==='duck'&&G.items.length===1&&!freeUnlocked()}''')
        await page.goto((Path(__file__).resolve().parents[1] / '视觉预览.html').as_uri())
        await page.wait_for_timeout(600)
        child = page.frames[1]
        assert await child.evaluate("SAVE_KEY==='zmt_preview_throw_v1'&&G.level===1"), '预览加载统一版并隔离存档'
        print('PASS 预览统一版本与存档隔离')
        assert not errors, errors
        print('23/23 体验回归通过；无页面脚本异常')
        await browser.close()

asyncio.run(main())
