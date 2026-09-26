#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《砸个痛快》M5 视觉验证：截图 + PIL 像素采样（新配色断言）
视口 480×854 = 画布逻辑尺寸 → 画布铺满视口，截图即画布。
用法：python3 /tmp/zm_shots.py
"""
import asyncio, threading, io
from http.server import HTTPServer, SimpleHTTPRequestHandler
from playwright.async_api import async_playwright
from PIL import Image

DIR='/Volumes/AI_WORK/AI_OUTPUTS/项目总开关/游戏/发泄小游戏'
PORT=8124

class H(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=DIR,**kw)
    def log_message(self,*a): pass

results=[]
def ok(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('✅' if cond else '❌')+' '+name+(('  '+extra) if extra else ''))

def near(px,target,tol):
    return all(abs(a-b)<=tol for a,b in zip(px[:3],target))
def count(img,target,tol=40):
    n=0
    for p in img.getdata():
        if near(p,target,tol): n+=1
    return n

async def shot(page,name):
    data=await page.screenshot()
    img=Image.open(io.BytesIO(data)).convert('RGB')
    img.save(f'/tmp/zm5_{name}.png')
    return img

async def main():
    srv=HTTPServer(('127.0.0.1',PORT),H)
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page(viewport={'width':480,'height':854})
        page.on('pageerror', lambda e: print('  pageerror:', e))
        await page.goto(f'http://127.0.0.1:{PORT}/index.html')
        await page.wait_for_timeout(500)
        # 解锁前 3 关 + 发泄屋（用于视觉：4 个珊瑚开始钮 + 发泄屋入口）
        await page.evaluate("localStorage.setItem('zmt_save_v1',JSON.stringify({score:6000,stars:[1,1,1,0,0,0],best:[400,500,600,0,0,0],maxCombo:5,gifts:['duck','trophy'],vol:0.7,vib:true,sfx:true}));location.reload()")
        await page.wait_for_timeout(600)

        # ---- 1. 选关界面：夜幕背景 + 金色 + 珊瑚 ----
        img=await shot(page,'select')
        ok('选关：深紫夜幕背景', count(img,(43,36,64),50)>20000, str(count(img,(43,36,64),50)))
        ok('选关：金色高亮（积分/星星/导航）', count(img,(255,209,102),40)>300, str(count(img,(255,209,102),40)))
        ok('选关：珊瑚开始按钮', count(img,(255,122,89),45)>300, str(count(img,(255,122,89),45)))
        ok('选关：迷你预览暖色（客厅墙）', count(img,(248,236,210),30)>200, str(count(img,(248,236,210),30)))

        # ---- 2. 设置界面：绿色开关 + 珊瑚重置 + 金色滑杆 ----
        await page.evaluate("openScreen('settings')")
        await page.wait_for_timeout(300)
        img=await shot(page,'settings')
        ok('设置：绿色开关胶囊', count(img,(126,224,129),40)>500, str(count(img,(126,224,129),40)))
        ok('设置：珊瑚重置按钮', count(img,(255,122,89),45)>800, str(count(img,(255,122,89),45)))
        ok('设置：金色滑杆/文字', count(img,(255,209,102),40)>300, str(count(img,(255,209,102),40)))

        # ---- 3. 礼品馆：珊瑚领取按钮（富玩家人人有） ----
        await page.evaluate("Save.data.score=150000;Save.save();openScreen('shop')")
        await page.wait_for_timeout(900)   # 等卡片入场动画放完（全 alpha）
        img=await shot(page,'shop')
        ok('礼品馆：珊瑚领取按钮群', count(img,(255,122,89),45)>3000, str(count(img,(255,122,89),45)))
        ok('礼品馆：绿色已领取', count(img,(126,224,129),40)>300, str(count(img,(126,224,129),40)))

        # ---- 4. 游戏内：客厅房间渲染 + 金色通关线 ----
        await page.evaluate("startLevel(0)")
        await page.wait_for_timeout(400)
        img=await shot(page,'play')
        ok('游戏内：客厅暖墙渲染', count(img,(248,236,210),30)>20000, str(count(img,(248,236,210),30)))
        ok('游戏内：金色通关线', count(img,(255,209,102),40)>30, str(count(img,(255,209,102),40)))

        # ---- 5. 结算面板：金色星星 + 彩带 ----
        await page.evaluate("G.items.filter(i=>!i.type.unbreakable).forEach(i=>{if(i.state!=='gone')smash(i)})")
        await page.wait_for_timeout(2200)
        img=await shot(page,'panel')
        ok('结算：金色星星', count(img,(255,209,102),40)>600, str(count(img,(255,209,102),40)))
        ok('结算：珊瑚主按钮', count(img,(255,122,89),45)>800, str(count(img,(255,122,89),45)))

        # ---- 6. 发泄屋：空投物品可见 ----
        await page.evaluate("showLevelSelect();startFree()")
        await page.wait_for_timeout(800)
        img=await shot(page,'free')
        ok('发泄屋：玻璃物品可见', count(img,(196,233,247),30)>300, str(count(img,(196,233,247),30)))

        # ---- 7. 横屏提示：暗色遮罩覆盖全屏 + 明亮文字 ----
        await page.evaluate('showLevelSelect()')
        await page.wait_for_timeout(300)
        await page.set_viewport_size({'width':844,'height':390})
        await page.wait_for_timeout(300)
        img=await shot(page,'landscape')
        ok('横屏：暗色遮罩覆盖', count(img,(10,8,20),30)>200000, str(count(img,(10,8,20),30)))
        bright=count(img,(255,255,255),70)   # 宽松容差拾取缩放后的抗锯齿文字
        ok('横屏：明亮提示文字', bright>300, str(bright))

    srv.shutdown()
    npass=sum(1 for _,c in results if c)
    print(f'\n===== 视觉验证 {npass}/{len(results)} 项通过 =====')
    raise SystemExit(0 if npass==len(results) else 1)

asyncio.run(main())
