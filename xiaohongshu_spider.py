import asyncio
import json
import time
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

KEYWORD = "咖啡馆"
SEARCH_URL = f"https://www.xiaohongshu.com/search_result?keyword={KEYWORD}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
OUTPUT_JSON = "notes.json"
OUTPUT_CSV = "notes.csv"
SCROLL_TIMES = 3  # 加载3页

# 如需登录，设置你的cookie字符串
COOKIES_JSON_PATH = "cookies.json"  # 可选，见下文说明

async def main():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=USER_AGENT)
        
        # 如需登录，导入cookie
        try:
            with open(COOKIES_JSON_PATH, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print("已导入cookie")
        except FileNotFoundError:
            print("未检测到cookie文件，继续以游客身份访问")
        
        page = await context.new_page()
        try:
            await page.goto(SEARCH_URL, timeout=60000)
            await asyncio.sleep(5)  # 等待页面渲染
            # 调试：保存页面源码
            content = await page.content()
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(content)
            # 你可以先注释掉下面这行，手动查看 debug.html 里的真实元素
            # await page.wait_for_selector('div.note-item', timeout=20000)
        except PlaywrightTimeoutError:
            print("页面加载超时，可能被反爬。")
            await browser.close()
            return

        # 模拟滚动加载
        for i in range(SCROLL_TIMES):
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(2 + i)  # 增加等待时间，模拟真实用户
            print(f"已滚动第{i+1}页")

        # 提取笔记信息
        note_cards = await page.query_selector_all('div.note-item')
        print(f"共检测到{len(note_cards)}条笔记")
        for card in note_cards:
            try:
                title = await card.query_selector_eval('div.title', 'el => el.innerText')  # 标题
            except Exception:
                title = ""
            try:
                link = await card.query_selector_eval('a', 'el => el.href')  # 链接
            except Exception:
                link = ""
            try:
                like = await card.query_selector_eval('span.like-count', 'el => el.innerText')
            except Exception:
                like = ""
            try:
                author = await card.query_selector_eval('div.author-info span.name', 'el => el.innerText')
            except Exception:
                author = ""
            results.append({
                "title": title.strip(),
                "link": link,
                "like": like,
                "author": author.strip(),
            })

        # 保存为JSON和CSV
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        print(f"已保存为 {OUTPUT_JSON} 和 {OUTPUT_CSV}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())