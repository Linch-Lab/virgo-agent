"""Virgo Agent self-verification — opens browser, captures console + screenshot + DOM state."""
import asyncio, sys, os
from datetime import datetime
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'https://virgo.billlinch.com/app/'
SCREENSHOT = 'C:/Users/satb0/virgo-agent/test_screenshot.png'

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        
        console_msgs = []
        page.on('console', lambda msg: console_msgs.append(f'[{msg.type}] {msg.text[:200]}'))
        page.on('pageerror', lambda err: console_msgs.append(f'[PAGE_ERROR] {err}'))
        
        print(f'Loading {URL}...')
        await page.goto(URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(4000)
        
        # Screenshot
        await page.screenshot(path=SCREENSHOT, full_page=False)
        print(f'Screenshot: {SCREENSHOT}')
        
        # Debug banner
        banner = await page.query_selector('#debugBanner')
        visible = await banner.is_visible() if banner else False
        if visible:
            text = await banner.inner_text()
            print(f'DEBUG BANNER (visible): {text[:300]}')
        else:
            print('DEBUG BANNER: hidden (init ran successfully)')
        
        # Sidebar content
        tree = await page.query_selector('#sidebarTree')
        if tree:
            items = await page.query_selector_all('#sidebarTree .tree-section, #sidebarTree .tree-item')
            print(f'SIDEBAR: {len(items)} items')
            for item in items[:10]:
                text = (await item.inner_text()).strip()[:60]
                cls = await item.get_attribute('class') or ''
                print(f'  {cls[:30]:<30} {text}')
        else:
            print('SIDEBAR: NOT FOUND')
        
        # Phase tabs
        tabs = await page.query_selector_all('.phase-tab')
        for t in tabs:
            text = (await t.inner_text()).strip()
            cls = await t.get_attribute('class') or ''
            locked = 'locked' in cls
            active = 'active' in cls
            status = 'LOCKED' if locked else ('ACTIVE' if active else 'unlocked')
            print(f'PHASE TAB: {text:<25} {status}')
        
        # Console summary
        errors = [m for m in console_msgs if 'error' in m.lower() or 'ERROR' in m]
        warns = [m for m in console_msgs if 'warn' in m.lower()]
        print(f'CONSOLE: {len(console_msgs)} msgs, {len(errors)} errors, {len(warns)} warnings')
        for e in errors[:8]:
            print(f'  {e[:250]}')
        
        # Auth modal
        auth = await page.query_selector('#authOverlay')
        if auth:
            print(f'AUTH MODAL: visible={await auth.is_visible()}')
        
        await browser.close()
        return len(errors) == 0

if __name__ == '__main__':
    ok = asyncio.run(verify())
    sys.exit(0 if ok else 1)
