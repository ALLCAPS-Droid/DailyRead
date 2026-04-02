import datetime
import json
import os
from playwright.sync_api import sync_playwright

def get_articles_and_update_history():
    print("正在启动虚拟浏览器……")
    history_file = "history.json"
    
    # 1. 安全加载本地历史记录
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []
            
    existing_guids = {item.get('guid', '') for item in history}
    new_items_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            list_url = "https://saduck.top/my/dailyRead.html"
            print(f"正在访问文章列表页: {list_url}")
            page.goto(list_url, wait_until="networkidle", timeout=30000)
            
            try:
                page.wait_for_selector(".article-meta", timeout=15000)
            except:
                print("未能找到文章卡片，页面可能加载缓慢。")
                return history, 0

            # 获取列表上的卡片
            cards_info = page.evaluate("""
                () => {
                    let results = [];
                    let metas = document.querySelectorAll('.article-meta');
                    metas.forEach((meta, index) => {
                        let card = meta.parentElement;
                        let dateEl = meta.querySelector('.article-date');
                        let dateText = dateEl ? dateEl.innerText.trim() : '';
                        
                        let titleEl = card.querySelector('.title, h2, h3, h4, .text-lg');
                        let titleText = titleEl ? titleEl.innerText.trim() : `每日晨读_${index}`;
                        
                        results.push({ index: index, date: dateText, title: titleText });
                    });
                    return results;
                }
            """)
            
            # 2. 遍历新文章
            for info in reversed(cards_info):
                clean_date = info['date'].replace(' ', '') if info['date'] else datetime.date.today().isoformat()
                unique_guid = f"{clean_date}-{info['title']}"
                
                if unique_guid in existing_guids:
                    continue
                    
                print(f"正在抓取新文章: {unique_guid}")
                try:
                    if page.url != list_url:
                        page.goto(list_url, wait_until="networkidle")
                        page.wait_for_selector(".article-meta", timeout=10000)
                    
                    # 模拟点击
                    page.evaluate(f"""
                        (idx) => {{
                            let meta = document.querySelectorAll('.article-meta')[idx];
                            if(meta && meta.parentElement) meta.parentElement.click();
                        }}
                    """, info['index'])
                    
                    page.wait_for_timeout(3000)
                    current_link = page.url
                    
                    # 🌟 核心：精准提取与深度 DOM 清洗
                    detail = page.evaluate("""
                        () => {
                            let titleEl = document.querySelector('h1') || document.querySelector('.title');
                            let title = titleEl ? titleEl.innerText.trim() : '';
                            
                            // 精确提取「来源」和「主题」let sourceText = '';
                            let themeText = '';
                            let metaSpans = document.querySelectorAll('.meta-info span');
                            if (metaSpans.length >= 2) {
                                sourceText = metaSpans[0].innerText.trim();
                                themeText = metaSpans[1].innerText.trim();
                            }
                            
                            // 精确定位最核心的正文区，避开外围的喇叭、按钮和版权声明
                            let contentEl = document.querySelector('.content') || document.querySelector('.answer-content') || document.querySelector('.vp-doc');
                            let contentHtml = '';
                            
                            if(contentEl) {
                                let clone = contentEl.cloneNode(true);
                                
                                // 黑名单：无情清除混入正文的垃圾元素
                                let junkSelectors = [
                                    'svg',                   // 干掉喇叭图案
                                    '.dialog-overlay',       // 干掉收藏弹窗
                                    '.back-button',          // 干掉底部按钮
                                    '.el-pagination',        // 干掉翻页器
                                    '.meta-info'             // 避免正文重复出现来源
                                ];
                                junkSelectors.forEach(selector => {
                                    clone.querySelectorAll(selector).forEach(el => el.remove());
                                });
                                
                                // 干掉免责声明文字
                                clone.querySelectorAll('div, p').forEach(el => {
                                    let txt = el.innerText || '';
                                    if(txt.includes('信息来源于网络搜集') || txt.includes('不涉及商业盈利目的')) {
                                        el.remove();
                                    }
                                });
                                
                                contentHtml = clone.innerHTML.trim();
                            }
                            return { title, sourceText, themeText, contentHtml };
                        }
                    """)
                    
                    final_title = detail['title'] if detail['title'] else info['title']
                    
                    if detail['contentHtml'] and len(detail['contentHtml'].strip()) > 10:
                        now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
                        
                        # 🌟 核心排版：利用 table 实现左右分栏，干掉不需要的内容
                        beautiful_html = f"""
                        <div style="border-bottom: 1px dashed #ccc; padding-bottom: 10px; margin-bottom: 15px;">
                            <table width="100%" style="border: none; border-collapse: collapse;">
                                <tr>
                                    <td align="left" style="color: #666; font-size: 14px;">{detail['sourceText']}</td>
                                    <td align="right" style="color: #666; font-size: 14px;">{detail['themeText']}</td>
                                </tr>
                            </table>
                        </div>
                        <div style="font-size: 16px; line-height: 1.8; color: #333;">
                            {detail['contentHtml']}
                        </div>
                        """
                        
                        history.insert(0, {
                            "title": f"[{clean_date}] {final_title}",
                            "link": current_link,
                            "description": beautiful_html,
                            "pubDate": now,
                            "guid": unique_guid
                        })
                        new_items_count += 1
                        existing_guids.add(unique_guid)
                        
                except Exception as inner_e:
                    print(f"处理第 {info['index']} 篇文章时发生异常: {inner_e}")
                    
        except Exception as e:
            print(f"抓取主流程发生异常: {e}")
        finally:
            browser.close()
            
    if len(history) > 0:
        history = history[:30] 
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    return history, new_items_count

def make_rss(history):
    print("开始生成 atom.xml 订阅源……")
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

    rss_template = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>SaDuck 每日晨读</title>
  <link>https://saduck.top/my/dailyRead.html</link>
  <description>自动抓取的公考晨读，纯净排版</description>
  <lastBuildDate>{now}</lastBuildDate>{items_xml}
</channel>
</rss>"""

    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)

if __name__ == "__main__":
    history, new_count = get_articles_and_update_history()
    
    if history and len(history) > 0:
        make_rss(history)
        print(f"✅ 任务完成！本次新增 {new_count} 篇。")
    else:
        print("❌ 未获取到任何文章，跳过 XML 生成。")
