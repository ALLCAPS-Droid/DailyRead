import datetime
import json
import os
from playwright.sync_api import sync_playwright

def get_articles_and_update_history():
    print("正在启动虚拟浏览器……")
    history_file = "history.json"
    
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
            
    existing_guids = {item.get('guid', '') for item in history}
    new_items_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            list_url = "https://saduck.top/my/dailyRead.html"
            print(f"正在访问文章列表页……")
            # 使用 domcontentloaded 加快访问速度，防止超时
            page.goto(list_url, wait_until="domcontentloaded", timeout=60000)
            
            page.wait_for_selector(".article-meta", timeout=15000)

            # 获取所有卡片的基本信息
            cards_info = page.evaluate("""
                () => {
                    let results = [];
                    let metas = document.querySelectorAll('.article-meta');
                    metas.forEach((meta, index) => {
                        let card = meta.parentElement;
                        let dateText = meta.querySelector('.article-date')?.innerText.trim() || '';
                        let titleText = card.querySelector('.title, h2, h3, h4, .text-lg')?.innerText.trim() || `文章_${index}`;
                        results.push({ index: index, date: dateText, title: titleText });
                    });
                    return results;
                }
            """)
            
            print(f"列表页共发现 {len(cards_info)} 篇文章。")
            
            for info in reversed(cards_info):
                clean_date = info['date'].replace(' ', '') if info['date'] else datetime.date.today().isoformat()
                unique_guid = f"{clean_date}-{info['title']}"
                
                if unique_guid in existing_guids:
                    print(f"跳过已存在记录: {unique_guid}")
                    continue
                    
                print(f"正在抓取新文章: {unique_guid}")
                try:
                    # 确保弹窗全关掉（如果有的话）
                    page.evaluate("() => { let btn = document.querySelector('.close-btn'); if(btn) btn.click(); }")
                    page.wait_for_timeout(500)

                    # 点击列表上的卡片
                    page.evaluate(f"document.querySelectorAll('.article-meta')[{info['index']}].parentElement.click()")
                    
                    # 等待正文容器渲染出来
                    page.wait_for_selector('.article-container', timeout=10000)
                    page.wait_for_timeout(1000)
                    
                    # 提取排版好的 HTML
                    detail = page.evaluate("""
                        () => {
                            let titleEl = document.querySelector('h1') || document.querySelector('.title');
                            let title = titleEl ? titleEl.innerText.trim() : '';
                            
                            let metaSpans = document.querySelectorAll('.meta-info span');
                            let source = metaSpans.length >= 1 ? metaSpans[0].innerText.trim() : '';
                            let theme = metaSpans.length >= 2 ? metaSpans[1].innerText.trim() : '';
                            
                            // 准确锁定正文，避开导航栏
                            let contentEl = document.querySelector('.answer-content') || document.querySelector('.article-container .content');
                            let contentHtml = '';
                            
                            if(contentEl) {
                                let clone = contentEl.cloneNode(true);
                                let junk = ['svg', '.dialog-overlay', '.back-button', '.el-pagination', '.meta-info', '.close-btn', '.vitepress-backTop-main'];
                                junk.forEach(s => clone.querySelectorAll(s).forEach(el => el.remove()));
                                
                                clone.querySelectorAll('div, p').forEach(el => {
                                    if(el.innerText.includes('信息来源于网络') || el.innerText.includes('版权问题')) el.remove();
                                });
                                contentHtml = clone.innerHTML.trim();
                            }
                            return { title, source, theme, contentHtml };
                        }
                    """)
                    
                    if detail['contentHtml'] and len(detail['contentHtml']) > 20:
                        now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
                        
                        beautiful_html = f"""
                        <div style="padding-bottom: 10px; margin-bottom: 15px;">
                            <table width="100%" style="width: 100%; border: none; border-collapse: collapse;">
                                <tr>
                                    <td align="left" style="color: #666; font-size: 14px; text-align: left;">{detail['source']}</td>
                                    <td align="right" style="color: #666; font-size: 14px; text-align: right;">{detail['theme']}</td>
                                </tr>
                            </table>
                        </div>
                        <div style="line-height: 1.8; font-size: 16px;">{detail['contentHtml']}</div>
                        """
                        
                        history.insert(0, {
                            "title": f"[{clean_date}] {detail['title'] or info['title']}",
                            "link": f"{list_url}?guid={unique_guid}",
                            "description": beautiful_html,
                            "pubDate": now,
                            "guid": unique_guid
                        })
                        new_items_count += 1
                        existing_guids.add(unique_guid)
                    
                    # 🌟 破局关键：抓完文章后，模拟点击底部的“返回列表”按钮！
                    page.evaluate("""
                        () => {
                            let btns = document.querySelectorAll('.back-button');
                            for(let b of btns) {
                                if(b.innerText.includes('返回列表')) {
                                    b.click();
                                    break;
                                }
                            }
                        }
                    """)
                    # 等待列表页重新出现，再进行下一次循环
                    page.wait_for_selector('.article-meta', timeout=10000)

                except Exception as inner_e:
                    print(f"处理单篇异常: {inner_e}")
                    
        except Exception as e:
            print(f"主流程异常: {e}")
        finally:
            browser.close()
            
    if len(history) > 0:
        history = history[:30] 
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    return history, new_items_count

def make_rss(history):
    print(f"正在生成 RSS，共 {len(history)} 篇文章……")
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    items_xml = ""
    for item in history:
        items_xml += f"""
  <item>
    <title><![CDATA[{item['title']}]]></title>
    <link>{item['link']}</link>
    <description><![CDATA[{item['description']}]]></description>
    <pubDate>{item['pubDate']}</pubDate>
    <guid>{item['guid']}</guid>
  </item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>SaDuck 每日晨读</title>
  <link>https://saduck.top/my/dailyRead.html</link>
  <description>纯净版公考晨读</description>
  <lastBuildDate>{now}</lastBuildDate>{items_xml}
</channel>
</rss>"""
    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss)

if __name__ == "__main__":
    h, count = get_articles_and_update_history()
    if h:
        make_rss(h)
        print(f"✅ 完成！新增 {count} 篇。")
