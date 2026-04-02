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
            page.goto(list_url, wait_until="networkidle", timeout=30000)
            
            # 等待卡片加载
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
            
            # 2. 反向遍历（从旧到新抓取，确保插入 history 时最新的在最前）
            for info in reversed(cards_info):
                clean_date = info['date'].replace(' ', '') if info['date'] else datetime.date.today().isoformat()
                unique_guid = f"{clean_date}-{info['title']}"
                
                if unique_guid in existing_guids:
                    print(f"跳过已存在记录: {unique_guid}")
                    continue
                    
                print(f"正在抓取新文章: {unique_guid}")
                try:
                    # 🌟 核心修复 1：确保没有任何残留的对话框挡路
                    page.evaluate("() => { let btn = document.querySelector('.close-btn'); if(btn) btn.click(); }")
                    page.wait_for_timeout(500)

                    # 模拟点击卡片
                    page.evaluate(f"document.querySelectorAll('.article-meta')[{info['index']}].parentElement.click()")
                    
                    # 等待对话框内容加载
                    page.wait_for_timeout(3000)
                    
                    # 🌟 核心修复 2：在对话框内精准抓取并清洗内容
                    detail = page.evaluate("""
                        () => {
                            // 只在当前弹出的 dialog 里面找内容
                            let dialog = document.querySelector('.dialog') || document.body;
                            let titleEl = dialog.querySelector('h1') || dialog.querySelector('.dialog-title');
                            let title = titleEl ? titleEl.innerText.trim() : '';
                            
                            let metaSpans = dialog.querySelectorAll('.meta-info span');
                            let source = metaSpans.length >= 1 ? metaSpans[0].innerText.trim() : '';
                            let theme = metaSpans.length >= 2 ? metaSpans[1].innerText.trim() : '';
                            
                            let contentEl = dialog.querySelector('.answer-content') || dialog.querySelector('.content') || dialog.querySelector('.vp-doc');
                            let contentHtml = '';
                            
                            if(contentEl) {
                                let clone = contentEl.cloneNode(true);
                                // 清理所有垃圾元素
                                let junk = ['svg', '.dialog-overlay', '.back-button', '.el-pagination', '.meta-info', '.close-btn'];
                                junk.forEach(s => clone.querySelectorAll(s).forEach(el => el.remove()));
                                
                                // 清理免责声明
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
                        <div style="border-bottom: 1px dashed #ccc; padding-bottom: 10px; margin-bottom: 15px;">
                            <table width="100%" style="border: none;">
                                <tr>
                                    <td align="left" style="color: #666;">{detail['source']}</td>
                                    <td align="right" style="color: #666;">{detail['theme']}</td>
                                </tr>
                            </table>
                        </div>
                        <div style="line-height: 1.8;">{detail['contentHtml']}</div>
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
                    
                    # 🌟 核心修复 3：抓完后必须点击关闭按钮，回到列表状态
                    page.evaluate("() => { let btn = document.querySelector('.close-btn'); if(btn) btn.click(); }")
                    page.wait_for_timeout(1000)

                except Exception as inner_e:
                    print(f"处理单篇异常: {inner_e}")
                    
        except Exception as e:
            print(f"主流程异常: {e}")
        finally:
            browser.close()
            
    # 4. 保留最近 30 条记录并保存
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
