import feedparser
import os
import requests
import datetime
import sys
from deep_translator import GoogleTranslator
from openai import OpenAI
from newspaper import Article
try:
    from dotenv import load_dotenv
    # 加载当前目录下的 .env
    load_dotenv()
except ImportError:
    pass

# 添加 common 目录到路径 (已移除)
# sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# from common.notifier import send
from utils.notifier import send

# 初始化翻译器
# 确保 newspaper 库已正确安装
translator = GoogleTranslator(source='auto', target='zh-CN')

# 配置：RSS 源列表
RSS_FEEDS = [
    {
        "name": "Hacker News (Tech)",
        "url": "https://news.ycombinator.com/rss",
        "max_items": 3,
        "translate": True
    },
    {
        "name": "少数派 (效率/生活)",
        "url": "https://sspai.com/feed",
        "max_items": 3,
        "translate": False
    },
    {
        "name": "36氪 (科技/创投)",
        "url": "https://36kr.com/feed",
        "max_items": 3,
        "translate": False
    },
    {
        "name": "机器之心 (AI深度)",
        "url": "https://www.jiqizhixin.com/rss",
        "max_items": 2,
        "translate": False
    },
    {
        "name": "OpenAI Blog (官方动态)",
        "url": "https://openai.com/blog/rss.xml",
        "max_items": 1,
        "translate": True
    },
    {
        "name": "V2EX (技术社区)",
        "url": "https://www.v2ex.com/index.xml",
        "max_items": 3,
        "translate": False
    },
    {
        "name": "IT之家 (数码)",
        "url": "https://www.ithome.com/rss/",
        "max_items": 3,
        "translate": False
    },
    {
        "name": "阮一峰日志 (技术思考)",
        "url": "http://www.ruanyifeng.com/blog/atom.xml",
        "max_items": 2,
        "translate": False
    },
    {
        "name": "Farnam Street (思维模型)",
        "url": "https://fs.blog/feed/",
        "max_items": 1,
        "translate": True
    },
    {
        "name": "Paul Graham (创业/哲学)",
        "url": "http://www.paulgraham.com/rss.html",
        "max_items": 1,
        "translate": True
    },
    {
        "name": "财新网 (财经)",
        "url": "http://corp.caixin.com/rss/",
        "max_items": 3,
        "translate": False
    },
    {
        "name": "知乎精选",
        "url": "https://www.zhihu.com/rss",
        "max_items": 3,
        "translate": False
    }
]

# 环境变量配置
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
AI_API_KEY = os.environ.get("AI_API_KEY")
# 星火 API (v1api) 地址 - 保持原样，确保 Key 能用
# 使用 or 确保如果环境变量为空字符串也能回退到默认值
AI_BASE_URL = os.environ.get("AI_BASE_URL") or "https://api.gemai.cc/v1"
# 用户指定模型
AI_MODEL = os.environ.get("AI_MODEL") or "[福利]gemini-3-flash-preview" 

def fetch_full_content(url):
    """抓取网页正文内容"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text, article.top_image
    except Exception as e:
        print(f"    ⚠️ 正文抓取失败: {e}")
        return "", ""

def summarize_with_ai(news_items):
    """利用 AI 对新闻进行深度整合和点评 (分批处理以防偷懒)"""
    if not AI_API_KEY:
        print("⚠️ 未配置 AI_API_KEY，跳过 AI 总结，使用普通列表模式。")
        return None

    print("🤖 正在呼叫 AI 进行新闻整合...")
    
    # === 分批策略 ===
    # 为了防止 AI 偷懒或输出截断，我们将新闻按数量分批
    # 每批处理 5 条新闻，这样 AI 的压力较小，输出质量更高
    BATCH_SIZE = 5
    batches = [news_items[i:i + BATCH_SIZE] for i in range(0, len(news_items), BATCH_SIZE)]
    
    full_summary = ""
    
    # 初始化客户端
    client = OpenAI(
        api_key=AI_API_KEY, 
        base_url=AI_BASE_URL,
        timeout=900.0 
    )

    for i, batch in enumerate(batches):
        print(f"  ⚡ 正在处理第 {i+1}/{len(batches)} 批新闻 ({len(batch)}条)...")
        
        # 构造当前批次的内容
        batch_content = ""
        # 注意：这里的序号需要接续上一批
        start_idx = i * BATCH_SIZE + 1
        
        for idx, item in enumerate(batch, start_idx):
            content_to_use = item.get('full_content', '')
            if len(content_to_use) < 100:
                content_to_use = item.get('summary', '无摘要')
            content_to_use = content_to_use[:1000] 
            
            batch_content += f"{idx}. [{item['source']}] {item['title']}\n   内容: {content_to_use}\n   链接: {item['link']}\n\n"

        # 构造 Prompt
        prompt = f"""
        你是我的私人新闻助理。今天是 {datetime.datetime.now().strftime('%Y-%m-%d')}。
        请根据以下新闻列表写一份**深度简报**。
        
        要求：
        1. **客观陈述**：直接陈述事实，不要废话。
        2. **内容详实**：每条新闻写 **150-200字**。详细还原事件经过、背景。
        3. **包含评论**：如有网友评论或观点请保留。
        4. **禁止省略**：必须把列表里的每一条都写出来！
        5. **格式统一**：
           - **标题**：{start_idx}. [来源] 原标题
           - **核心事实**：...
           - **背景/评论**：...
           - **链接**：[链接]
        
        待处理新闻列表：
        {batch_content}
        """

        try:
            response = client.chat.completions.create(
                model=AI_MODEL, 
                messages=[
                    {"role": "system", "content": "You are a professional news analyst. Please respond in Chinese."},
                    {"role": "user", "content": prompt},
                ],
                stream=False 
            )
            batch_result = response.choices[0].message.content
            full_summary += batch_result + "\n\n---\n\n" # 用分割线连接
            
        except Exception as e:
            print(f"  ❌ 第 {i+1} 批总结失败: {e}")
            # 如果这一批失败了，至少把原始标题拼进去，不至于完全丢失
            for item in batch:
                full_summary += f"⚠️ [AI处理失败] {item['title']}\n🔗 {item['link']}\n\n"

    return full_summary

def get_latest_news():
    """获取所有 RSS 源的最新新闻"""
    all_news = []
    
    for feed_conf in RSS_FEEDS:
        print(f"正在获取 {feed_conf['name']} ...")
        try:
            feed = feedparser.parse(feed_conf['url'])
            if not feed.entries:
                continue
            
            # 取前 N 条
            for entry in feed.entries[:feed_conf['max_items']]:
                title = entry.title
                # 尝试获取摘要 (description 或 summary)
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                # 清理 HTML 标签 (简单处理)
                summary = summary.replace('<p>', '').replace('</p>', '').replace('<br>', '\n')

                # 如果是英文源，先简单翻译一下标题方便 AI 理解（虽然 AI 懂英文，但翻译一下更稳）
                if feed_conf.get('translate'):
                    try:
                        translated_title = translator.translate(title)
                        title = f"{translated_title} ({title})"
                    except:
                        pass
                
                # 尝试抓取正文
                print(f"    正在抓取正文: {title[:20]}...")
                full_content, top_image = fetch_full_content(entry.link)
                
                item = {
                    "source": feed_conf['name'],
                    "title": title,
                    "link": entry.link,
                    "summary": summary,  # 存入摘要
                    "full_content": full_content, # 存入正文
                    "image": top_image # 存入图片
                }
                all_news.append(item)
        except Exception as e:
            print(f"  ❌ 获取 {feed_conf['name']} 失败: {e}")
            
    return all_news

def format_message_fallback(news_items):
    """(备用) 普通列表格式化"""
    if not news_items:
        return "今日无重要新闻。"
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    msg_lines = [f"📅 {current_date} 每日新闻 (普通版)：\n"]
    for idx, item in enumerate(news_items, 1):
        title = item['title'].replace('\n', ' ').strip()
        msg_lines.append(f"{idx}. [{item['source']}] {title}")
        msg_lines.append(f"   🔗 {item['link']}\n")
    return "\n".join(msg_lines)

# def send_notification(content):
#     """发送通知"""
#     if not WEBHOOK_URL:
#         print("⚠️ 未配置 WEBHOOK_URL，打印到控制台：\n" + "-"*20 + f"\n{content}\n" + "-"*20)
#         return
#
#     # 钉钉格式
#     payload = {"msgtype": "text", "text": {"content": content}}
#     try:
#         requests.post(WEBHOOK_URL, json=payload)
#         print("✅ 消息已推送")
#     except Exception as e:
#         print(f"❌ 推送失败: {e}")

def main():
    print("🚀 自动推文发送器 (AI 增强版) 启动...")
    news = get_latest_news()
    
    if not news:
        print("📭 今天没有抓取到任何新闻。")
        return

    # 尝试用 AI 总结
    message = summarize_with_ai(news)
    
    # 如果 AI 失败 (比如没配 Key)，回退到普通列表
    if not message:
        message = format_message_fallback(news)
        
    # 提取第一张有效图片作为封面
    cover_image = None
    main_link = None
    if news:
        main_link = news[0]['link']
        for item in news:
            if item.get('image') and item['image'].startswith('http'):
                cover_image = item['image']
                break

    send("每日新闻", message, image_url=cover_image, action_url=main_link)
    print("🏁 任务完成。")

if __name__ == "__main__":
    main()
