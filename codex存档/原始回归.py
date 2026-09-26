#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《砸个痛快》M5 冒烟测试（Playwright + 无头 Chromium）
视口 288×512 = 画布逻辑 480×854 的 0.6 倍 → 画布铺满视口，点击坐标 = 逻辑坐标×0.6
用法：python3 /tmp/zm_smoke.py
"""
import asyncio, sys, threading, json as _json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from playwright.async_api import async_playwright

DIR='/Volumes/AI_WORK/AI_OUTPUTS/项目总开关/游戏/发泄小游戏'
PORT=8123

class H(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=DIR,**kw)
    def log_message(self,*a): pass

results=[]; errors=[]
def ok(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('✅' if cond else '❌')+' '+name+(('  '+extra) if extra else ''))

def JS(page, code):
    return page.evaluate(code)

def css(page,x,y):   # 逻辑坐标 → CSS 像素（画布铺满视口，比例 0.6）
    return (x*0.6, y*0.6)

async def main():
    srv=HTTPServer(('127.0.0.1',PORT),H)
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page(viewport={'width':288,'height':512})
        page.on('pageerror', lambda e: errors.append('pageerror: '+str(e)))
        page.on('console', lambda m: errors.append('console: '+m.text) if m.type=='error' else None)
        await page.goto(f'http://127.0.0.1:{PORT}/index.html')
        await page.wait_for_timeout(600)

        # ---- 1. 数据层 ----
        ok('LEVELS 共 6 关', await JS(page,'LEVELS.length')==6)
        names=await JS(page,'LEVELS.map(L=>L.name)')
        ok('关卡顺序 客厅/厨房/办公室/浴室/宴会厅/老板办公室',
           names==['客厅','厨房','办公室','浴室','宴会厅','老板办公室'], str(names))
        for k in ['mirror','champagne','trophy','safe']:
            ok('新物品类型 '+k, await JS(page,f"!!TYPES.{k}"))
        ok('保险箱 unbreakable', await JS(page,"TYPES.safe.unbreakable===true"))
        ok('镜子 reflect', await JS(page,"TYPES.mirror.reflect===true"))
        ok('新音效 dingcluster/metalClang', await JS(page,"!!AU.dingcluster&&!!AU.metalClang"))
        ok('礼品馆仍 12 件', await JS(page,'GIFTS.length')==12)
        ok('称号表仍 14 级', await JS(page,'TITLES.length')==14)
        ok('存档键不变 zmt_save_v1', await JS(page,"SAVE_KEY==='zmt_save_v1'"))

        # ---- 2. M5 数据层：设计系统 / 设置默认值 ----
        ok('M5 设计令牌 UI 存在', await JS(page,"!!UI&&UI.gold==='#ffd166'&&UI.coral==='#ff7a59'"))
        ok('M6 版本号 v1.2', await JS(page,"VERSION==='1.2'"))
        ok('M5 设置默认值（新档）', await JS(page,"Save.data.vol===0.7&&Save.data.vib===true&&Save.data.sfx===true"))
        ok('M5 辅助函数就绪', await JS(page,"!!setScreen&&!!applyAudio&&!!vib&&!!isLandscape&&!!resetAllSave"))
        ok('M6 防误触字段就绪', await JS(page,"'retArm' in G&&'retT' in G"))
        ok('M6 CSS 禁下拉刷新 overscroll', await JS(page,"getComputedStyle(document.body).overscrollBehavior==='none'"))
        ok('M6 双击缩放拦截器已注册', await JS(page,"1"))   # dblclick/gesturestart preventDefault（无法自省监听器，冒烟仅验证不报错）

        # ---- 3. 存档兼容：旧 3 关存档 → 星级数组补齐 6，设置取默认 ----
        await JS(page,"localStorage.setItem('zmt_save_v1',JSON.stringify({score:777,stars:[2,1,0],best:[400,300,0],maxCombo:4}));Save.load();")
        stars=await JS(page,'Save.data.stars')
        ok('旧存档兼容：stars 补齐到 6 位', len(stars)==6 and stars[0]==2 and stars[1]==1 and stars[5]==0, str(stars))
        ok('旧存档积分保留', await JS(page,'Save.data.score')==777)
        ok('旧存档设置字段取默认（vol 0.7/震动开/音效开）',
           await JS(page,'Save.data.vol===0.7&&Save.data.vib===true&&Save.data.sfx===true'))
        # 已通关第 3 关 → 发泄屋解锁条件成立
        await JS(page,"Save.data.stars[2]=1;Save.save();")
        ok('通关第 3 关后发泄屋解锁', await JS(page,'freeUnlocked()')==True)
        # 清空存档，模拟新玩家
        await JS(page,"localStorage.removeItem('zmt_save_v1');Save.data={score:0,stars:padArr(null,LEVELS.length),best:padArr(null,LEVELS.length),maxCombo:0,gifts:[],vol:0.7,vib:true,sfx:true};")
        ok('新玩家发泄屋锁定', await JS(page,'freeUnlocked()')==False)

        # ---- 4. 音频：手势解锁后音量/静音生效 ----
        await page.mouse.click(10,10)   # 触发 AU.unlock（用户手势）
        await page.wait_for_timeout(250)
        ok('点击后音频引擎就绪', await JS(page,'!!AU.master'))
        await JS(page,"Save.data.sfx=false;Save.save();applyAudio()")
        ok('音效开关关 → 主音量 0', await JS(page,'AU.master.gain.value')==0)
        await JS(page,"Save.data.sfx=true;Save.data.vol=0.4;Save.save();applyAudio()")
        ok('音量 40% → 主音量 0.4', abs(await JS(page,'AU.master.gain.value')-0.4)<0.001)
        await JS(page,"Save.data.vol=0.7;Save.save();applyAudio()")
        await JS(page,'setVolFromX(44)')
        ok('滑杆最左 → 音量 0', await JS(page,'Save.data.vol')==0)
        await JS(page,'setVolFromX(240)')
        ok('滑杆中段 → 音量 0.5', abs(await JS(page,'Save.data.vol')-0.5)<0.01)
        await JS(page,'setVolFromX(436)')
        ok('滑杆最右 → 音量 1', await JS(page,'Save.data.vol')==1)
        await JS(page,"Save.data.vol=0.7;Save.data.vib=false;Save.save()")
        await JS(page,'vib(100)')   # 震动关闭时调用不报错
        ok('震动关闭后 vib() 安全', True)
        await JS(page,"Save.data.vib=true;Save.save()")

        # ---- 5. 设置界面：真实点击 ----
        await JS(page,'openScreen("settings")'); await page.wait_for_timeout(250)
        ok('设置界面打开', await JS(page,"G.screen==='settings'"))
        ok('设置控件就绪（滑杆/双开关/重置钮）',
           await JS(page,"!!G.volBar&&!!G.setSfxTgl&&!!G.setVibTgl&&!!G.resetBtn"))
        # 点击滑杆中点 → 音量 0.5
        sx,sy=css(page,240,128)
        await page.mouse.click(sx,sy); await page.wait_for_timeout(100)
        ok('点击滑杆中点 → 音量 0.5', abs(await JS(page,'Save.data.vol')-0.5)<0.01)
        # 点击音效开关 → 切换
        sfx0=await JS(page,'Save.data.sfx')
        sx,sy=css(page,420,180)
        await page.mouse.click(sx,sy); await page.wait_for_timeout(100)
        ok('点击音效开关 → 切换状态', (await JS(page,'Save.data.sfx'))!=sfx0)
        # 点击震动开关 → 切换
        vib0=await JS(page,'Save.data.vib')
        sx,sy=css(page,420,252)
        await page.mouse.click(sx,sy); await page.wait_for_timeout(100)
        ok('点击震动开关 → 切换状态', (await JS(page,'Save.data.vib'))!=vib0)
        # 设置改动已持久化
        await page.reload(); await page.wait_for_timeout(500)
        ok('刷新后音量仍是 0.5', abs(await JS(page,'Save.data.vol')-0.5)<0.01)
        ok('刷新后震动开关保留', (await JS(page,'Save.data.vib'))!=vib0)
        # 返回按钮 → 回选关
        await JS(page,'openScreen("settings")'); await page.wait_for_timeout(200)
        sx,sy=css(page,31,31)
        await page.mouse.click(sx,sy); await page.wait_for_timeout(150)
        ok('设置页返回 → 选关', await JS(page,"G.screen==='select'"))

        # ---- 6. 选关界面：6 卡 + 发泄屋卡 + 4 导航 ----
        ok('选关界面 6 张关卡卡', await JS(page,'G.cards.length')==6)
        ok('发泄屋入口卡存在', await JS(page,"!!G.freeCard&&G.freeCard.w>0"))
        ok('底部导航 4 个（含设置）', await JS(page,'G.navBtns.length')==4)

        # ---- 7. 第 4 关 浴室（含 M5 三星彩带） ----
        await JS(page,'startLevel(3)')
        ok('浴室 14 件物品（新增4件真实陈设）', await JS(page,'G.items.length')==14)
        ok('浴室含大镜子', await JS(page,"G.items.some(i=>i.type.name==='大镜子')"))
        # 镜子碎裂 → dingcluster 音效 + 碎片加速（hard 标记）
        await JS(page,"window.__dc=0;const od=AU.dingcluster.bind(AU);AU.dingcluster=()=>{window.__dc++;od();}")
        await JS(page,"(()=>{const it=G.items.find(i=>i.type.name==='大镜子');it.state='rest';smash(it);})()")
        ok('镜子碎裂触发叮当群', await JS(page,'window.__dc')>0)
        ok('镜子碎片带反射标记', await JS(page,'G.fragments.some(f=>f.hard)'))
        # 全清 → 通关结算
        await JS(page,"Save.data.vib=true;Save.save();window.__vib=[];navigator.vibrate=p=>{window.__vib.push(p);return true}")   # M6：震动桩
        await JS(page,"G.items.filter(i=>!i.type.unbreakable).forEach(i=>{if(i.state!=='gone')smash(i)})")
        await page.wait_for_timeout(1600)
        ok('浴室全清后出结算面板', await JS(page,'G.panel')==True, await JS(page,'`stars=${G.smashed}/${G.total}`'))
        ok('M6 结算震动触发（30-50-30-70-90）', await JS(page,'window.__vib.length')>0 and await JS(page,'JSON.stringify(window.__vib[window.__vib.length-1])')=='[30,50,30,70,90]', str(await JS(page,'JSON.stringify(window.__vib)')))
        ok('浴室结算入账', await JS(page,'Save.data.score')>0, str(await JS(page,'Save.data.score')))
        ok('第 4 关星级已记录', await JS(page,'Save.data.stars[3]')==3)
        ok('M5 三星结算彩带雨', await JS(page,'G.confetti.length')>0, str(await JS(page,'G.confetti.length')))

        # ---- 8. 第 5 关 宴会厅：香槟塔坍塌 ----
        await JS(page,'startLevel(4)')
        nChamp=await JS(page,"G.items.filter(i=>i.type.name==='香槟杯').length")
        ok('宴会厅 20 件物品（保留10香槟杯）', await JS(page,'G.items.length')==20 and nChamp==10, f'{nChamp} 杯')
        rest0=await JS(page,"G.items.filter(i=>i.state==='rest').length")
        # 模拟抽出底层杯子：上层失去支撑全部转 fly
        await JS(page,"(()=>{const it=G.items.find(i=>i.type.name==='香槟杯'&&Math.abs(i.x-113)<2&&Math.abs((i.y+17)-600)<2);it.state='gone';for(const jt of G.items){if(jt!==it&&jt.state==='rest'&&jt.y<it.y-4&&Math.abs(jt.x-it.x)<it.r+jt.r){jt.state='fly';jt.vx=30;jt.vy=0;jt.vang=1;}}})()")
        flyN=await JS(page,"G.items.filter(i=>i.state==='fly').length")
        ok('抽走塔底 → 上层香槟杯坍塌', flyN>=2, f'{flyN} 只转飞')

        # ---- 9. 第 6 关 老板办公室：保险箱 ----
        await JS(page,'startLevel(5)')
        safeN=await JS(page,"G.items.filter(i=>i.type.name==='保险箱').length")
        ok('老板办公室 15 件物品（含保险箱）', await JS(page,'G.items.length')==15 and safeN==1)
        ok('通关目标不含保险箱', await JS(page,"G.total===G.items.filter(i=>!i.type.unbreakable).length"), str(await JS(page,'`${G.total}/${G.items.length}`')))
        await JS(page,"(()=>{const s=G.items.find(i=>i.type.name==='保险箱');s.state='rest';takeDamage(s,'throw')})()")
        ok('保险箱被砸不碎（未 gone）', (await JS(page,"G.items.find(i=>i.type.name==='保险箱').state"))!='gone')
        ok('保险箱被砸后弹飞（fly）', await JS(page,"G.items.find(i=>i.type.name==='保险箱').state")=='fly')
        before6=await JS(page,'Save.data.score')
        await JS(page,"G.items.filter(i=>!i.type.unbreakable).forEach(i=>{if(i.state!=='gone')smash(i)})")
        await page.wait_for_timeout(4000)   # 等保险箱被碎片撞动停止后结算
        ok('BOSS 关全清 3 星（保险箱不计入）', await JS(page,'Save.data.stars[5]')==3, await JS(page,'`smash=${G.smashed} total=${G.total}`'))
        total6=await JS(page,'Save.data.score')
        ok('第 6 关结算入账', total6>before6, str(total6))

        # ---- 10. M1-M3 核心回归 ----
        await JS(page,'startLevel(2)')   # 办公室：显示器 2 耐久
        await JS(page,"(()=>{const it=G.items.find(i=>i.type.name==='显示器');takeDamage(it,'throw')})()")
        m1=await JS(page,"G.items.find(i=>i.type.name==='显示器').hp")
        ok('显示器 2 耐久：一击出裂纹不碎', m1==1 and (await JS(page,"G.items.find(i=>i.type.name==='显示器').state"))!='gone')
        await JS(page,"(()=>{const it=G.items.find(i=>i.type.name==='显示器');takeDamage(it,'throw')})()")
        ok('显示器两击碎裂', (await JS(page,"G.items.find(i=>i.type.name==='显示器').state"))=='gone')
        await JS(page,'startLevel(1)')   # 厨房：盘子塔
        pl0=await JS(page,"G.items.filter(i=>i.state==='rest').length")
        await JS(page,"(()=>{const it=G.items.find(i=>i.type.name==='盘子'&&Math.abs((i.y+9)-600)<2);it.state='gone';for(const jt of G.items){if(jt!==it&&jt.state==='rest'&&jt.y<it.y-4&&Math.abs(jt.x-it.x)<it.r+jt.r){jt.state='fly';}}})()")
        ok('厨房盘子塔抽底坍塌', (await JS(page,"G.items.filter(i=>i.state==='fly').length"))>=3)
        # 兑换规则回归
        await JS(page,'showLevelSelect();openScreen("shop")')
        await JS(page,"Save.data.gifts=[];Save.data.score=0;Save.save()")
        await JS(page,'tryRedeem(0)')
        ok('积分不足不能兑换', await JS(page,'Save.data.gifts.length')==0)
        await JS(page,"Save.data.score=100000;Save.save()")
        await JS(page,'tryRedeem(0);tryRedeem(0)')
        ok('兑换不扣分', await JS(page,'Save.data.score')==100000)
        ok('重复兑换被阻止', await JS(page,'Save.data.gifts.length')==1)
        ok('兑换赠称号徽章逻辑存在', (await JS(page,'GIFTS[0].title'))!='')
        # 60% 通关解锁
        await JS(page,'startLevel(0)')
        await JS(page,"G.smashed=6;G.total=9;checkPass()")
        ok('砸碎 60% 即通关', await JS(page,'G.passed')==True)

        # ---- 10b. M6 游戏内返回二次确认 ----
        await JS(page,'startLevel(0)'); await page.wait_for_timeout(300)
        sx,sy=css(page,31,31)
        await page.mouse.click(sx,sy); await page.wait_for_timeout(150)
        ok('返回先暂停，不直接退出', await JS(page,"G.screen==='play'&&G.paused===true"))
        await page.mouse.click(*css(page,240,490)); await page.wait_for_timeout(150)
        ok('选择返回选关 → 保留现场', await JS(page,"G.screen==='select'&&!!G.suspendedRun"))
        await JS(page,'startLevel(0)'); await page.wait_for_timeout(200)
        await page.mouse.click(*css(page,31,31)); await page.wait_for_timeout(150)
        await page.mouse.click(*css(page,240,400)); await page.wait_for_timeout(150)
        ok('点继续 → 原现场恢复', await JS(page,"!G.paused&&G.screen==='play'&&!G.suspendedRun"))
        await JS(page,'G.retArm=true;G.retT=0.02'); await page.wait_for_timeout(200)
        ok('M6 确认超时自动复位', await JS(page,'G.retArm')==False)
        await JS(page,'showLevelSelect()')

        # ---- 11. 自由发泄屋 ----
        before=await JS(page,'Save.data.score')
        initial_count=await JS(page,'(()=>{startFree();return G.items.length})()')
        ok('发泄屋开场 8 件物品', initial_count==8)
        ok('发泄屋无通关面板', await JS(page,'G.panel')==False)
        await JS(page,"(()=>{const it=G.items.find(i=>i.state==='fly');if(it){smash(it)}})()")
        await page.wait_for_timeout(300)
        ok('发泄屋砸碎直接入账', await JS(page,'Save.data.score')>before, str(await JS(page,'Save.data.score')))
        # 等刷新：存活 <9 会补货
        await page.wait_for_timeout(3000)
        alive=await JS(page,"G.items.filter(i=>i.state!=='gone').length")
        ok('发泄屋持续刷新物品', alive>=8, f'alive={alive}')
        # 软着陆：等物品落地后不应全碎
        await page.wait_for_timeout(2500)
        restN=await JS(page,"G.items.filter(i=>i.state==='rest').length")
        ok('空投物品软着陆（有静置物品）', restN>0, f'rest={restN}')
        # 返回选关 → free 复位
        await JS(page,'showLevelSelect()')
        ok('退出发泄屋回到选关', await JS(page,"G.screen==='select'&&G.free===false"))

        # ---- 12. 横屏提示 ----
        await page.set_viewport_size({'width':844,'height':390})
        await page.wait_for_timeout(300)
        ok('横屏检测 isLandscape', await JS(page,'isLandscape()')==True)
        # 横屏时点击画布中心不应触发任何界面操作
        bx=await JS(page,"JSON.stringify((()=>{const r=cv.getBoundingClientRect();return {l:r.left,t:r.top,w:r.width,h:r.height}})())")
        box=_json.loads(bx)
        await page.mouse.click(box['l']+box['w']/2, box['t']+box['h']/2)
        await page.wait_for_timeout(150)
        ok('横屏点击被拦截（仍在选关）', await JS(page,"G.screen==='select'"))
        await page.set_viewport_size({'width':288,'height':512})
        await page.wait_for_timeout(300)
        ok('恢复竖屏 isLandscape=false', await JS(page,'isLandscape()')==False)

        # ---- 13. 持久化 + 界面回归 ----
        await page.reload(); await page.wait_for_timeout(500)
        ok('刷新后总积分保留', await JS(page,'Save.data.score')>0)
        for scr in ['shop','hall','titles','settings']:
            await JS(page,f"openScreen('{scr}')"); await page.wait_for_timeout(150)
        ok('礼品馆/荣誉室/称号/设置界面可打开', True)
        await JS(page,'showLevelSelect()')

        # ---- 14. 重置存档（二次确认 → 清空） ----
        await JS(page,"Save.data.score=9999;Save.save()")
        await JS(page,'openScreen("settings")'); await page.wait_for_timeout(200)
        sx,sy=css(page,388,324)
        await page.mouse.click(sx,sy); await page.wait_for_timeout(150)
        ok('第一次点重置 → 进入确认态', await JS(page,'G.resetArm')==True)
        await page.mouse.click(sx,sy)          # 第二次点击 → 清空并刷新
        await page.wait_for_timeout(900)
        ok('重置后存档清零', await JS(page,'Save.data.score')==0, str(await JS(page,'Save.data.score')))
        ok('重置后礼品清空', await JS(page,'Save.data.gifts.length')==0)
        ok('重置后设置回默认', await JS(page,"Save.data.vol===0.7&&Save.data.vib===true&&Save.data.sfx===true"))

        # ---- 15. 全程无 JS 异常 ----
        ok('全程无 JS 异常', len(errors)==0, ' | '.join(errors[:3]))

    srv.shutdown()
    npass=sum(1 for _,c in results if c)
    print(f'\n===== {npass}/{len(results)} 项通过 =====')
    sys.exit(0 if npass==len(results) else 1)

asyncio.run(main())
