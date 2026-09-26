"""全清空白点击/恢复、等待超时、暂停和重复入账专项。"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch();page=await b.new_page(viewport={'width':480,'height':854})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto((Path(__file__).resolve().parents[1]/'index.html').as_uri())
  count=0
  async def check(name,code):
   nonlocal count
   assert await page.evaluate(code),name
   count+=1;print('PASS',name)
  for i in range(6):
   await page.evaluate(f'G.suspendedRun=null;startLevel({i});G.items.filter(i=>!i.type.unbreakable).forEach(smash)')
   await page.wait_for_timeout(1300)
   await check(f'第{i+1}关全清有结算',"G.panel&&G.smashed===G.total&&starsFor()===3")
   await page.mouse.click(240,750);await page.wait_for_timeout(100)
   await check(f'第{i+1}关空白不能关闭全清结算',"G.panel&&G.state==='won'")
   await check(f'第{i+1}关异常回到play仍可恢复结算',"""()=>{const saved=Save.data.score;G.panel=false;G.panelShown=false;G.state='play';G.passed=false;for(let j=0;j<65;j++)step(0,1/60);return G.panel&&Save.data.score===saved}""")
  await check('不完全清场仍可继续砸',"""()=>{startLevel(0);G.smashed=Math.ceil(G.total*PASS_RATE);checkPass();for(let j=0;j<65;j++)step(0,1/60);render(0);return G.panel&&starsFor()<3}""")
  await page.mouse.click(240,750)
  await check('通关后点击空白继续',"!G.panel&&G.state==='play'")
  await check('全清后保险箱不停飞也能结算',"""()=>{startLevel(5);G.items.filter(i=>!i.type.unbreakable).forEach(smash);const safe=G.items.find(i=>i.type.unbreakable);safe.state='fly';safe.vy=-200;for(let j=0;j<65;j++)step(0,1/60);return G.panel}""")
  await check('有未停稳物品3秒兜底结算',"""()=>{startLevel(0);G.smashed=Math.ceil(G.total*PASS_RATE);checkPass();G.items[0].state='fly';for(let j=0;j<190;j++)step(0,1/60);return G.panel&&G.settleT<3.2}""")
  await check('遗留held输入不会无限等待',"""()=>{startLevel(0);G.smashed=Math.ceil(G.total*PASS_RATE);checkPass();input.held=G.items[0];input.active=true;G.items[0].state='held';for(let j=0;j<190;j++)step(0,1/60);return G.panel&&!input.active&&!input.held}""")
  await check('孤立held物品可释放恢复',"""()=>{startLevel(0);G.smashed=Math.ceil(G.total*PASS_RATE);checkPass();input.held=null;input.active=false;G.items[0].state='held';for(let j=0;j<190;j++)step(0,1/60);return G.panel&&G.items[0].state!=='held'}""")
  await page.evaluate('startLevel(4);G.items.forEach(smash);pauseGame(true)')
  before=await page.evaluate('G.settleT')
  await page.wait_for_timeout(700)
  await check('暂停不推进结算倒计时',f'G.settleT==={before}&&!G.panel')
  await page.evaluate('pauseGame(false)');await page.wait_for_timeout(1300)
  await check('恢复后正常结算', 'G.panel')
  await check('结算不重复入账',"""()=>{const score=Save.data.score;for(let j=0;j<300;j++)step(0,1/60);bankScore();return Save.data.score===score}""")
  assert not errors,errors
  print(f'{count}/{count} 项结算防卡回归通过，无脚本异常')
  await b.close()
asyncio.run(main())
