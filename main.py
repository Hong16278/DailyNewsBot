import feedparser
import os
import requests
import datetime
import sys
from deep_translator import GoogleTranslator
from openai import OpenAI
from newspaper import Article
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
    },
    {
        "name": "豆瓣书评",
        "url": "https://www.douban.com/feed/review/book",
        "max_items": 2,
        "translate": False
    }
]

# 环境变量配置
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
AI_API_KEY = os.environ.get("AI_API_KEY")
# 星火 API (v1api) 地址
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://xh.v1api.cc/v1") 
# 换用 DeepSeek-R1 (推理模型)，适合深度分析和长文本，不容易偷懒
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-ai/DeepSeek-R1") 

def fetch_full_content(url):
    """抓取网页正文内容"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"    ⚠️ 正文抓取失败: {e}")
        return ""

def summarize_with_ai(news_items):
    """利用 AI 对新闻进行深度整合和点评"""
    if not AI_API_KEY:
        print("⚠️ 未配置 AI_API_KEY，跳过 AI 总结，使用普通列表模式。")
        return None

    print("🤖 正在呼叫 AI 进行新闻整合 (这可能需要几十秒)...")
    
    # 构造给 AI 的提示词 (Prompt)
    # 为了让 AI 能看到更多内容，我们尝试提取 description (摘要)
    news_content = ""
    for idx, item in enumerate(news_items, 1):
        # 优先使用抓取到的正文，如果太短则使用摘要，截取前 1000 字
        content_to_use = item.get('full_content', '')
        if len(content_to_use) < 100:
            content_to_use = item.get('summary', '无摘要')
        
        content_to_use = content_to_use[:1000] # 截取前 1000 字，避免 Token 爆炸
        
        news_content += f"{idx}. [{item['source']}] {item['title']}\n   内容: {content_to_use}\n   链接: {item['link']}\n\n"

    prompt = f"""
    你是我的私人新闻助理。今天是 {datetime.datetime.now().strftime('%Y-%m-%d')}。
    请根据以下新闻列表写一份**深度简报**。
    
    要求：
    1. **客观陈述，拒绝废话**：不需要你扮演"科技博主"或"幽默大师"，请直接陈述事实。
    2. **内容详实 (重要)**：每条新闻必须写够 **200字** 以上。基于提供的正文内容，详细还原事件经过、背景和各方观点。
    3. **包含评论**：如果原文中包含网友评论或观点，请务必保留。
    4. **全部输出，禁止省略**：
       - **绝对不要**出现"（其他新闻因篇幅限制略）"、"（...）"这种话。
       - 我提供给你的每一条新闻，你都要按照下面的格式写出来，哪怕内容很长也要写完。
       - 如果内容太长，你可以分段写，但不要省略新闻条目。
    5. **结构清晰**：
       - **标题**：[来源] 原标题
       - **核心事实**：详细描述发生了什么（100字+）。
       - **背景/评论/影响**：补充背景信息或观点（100字+）。
       - **链接**：[链接]
    6. 分类整理（科技/财经/生活）。

    待处理新闻列表：
    {news_content}
    """

    try:
        # 使用 SiliconFlow 兼容的 client
        client = OpenAI(
            api_key=AI_API_KEY, 
            base_url=AI_BASE_URL,
            timeout=900.0 # 既然用 R1，超时时间直接拉到 15 分钟
        )
        response = client.chat.completions.create(
            # 换用 gpt-4o 或 deepseek-v3，这些模型生成长文能力更强
            # 如果 AI_MODEL 环境变量没变，这里会沿用之前设置的 deepseek-v3
            model=AI_MODEL, 
            messages=[
                {"role": "system", "content": "You are a professional news analyst. Please respond in Chinese."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ AI 总结失败 (Error): {e}")
        # 如果是 Authentication Error，提示检查 Key
        if "401" in str(e):
            print("💡 提示: 请检查 GitHub Secrets 中的 AI_API_KEY 是否正确，且是否有额度。")
        # 如果是 404，提示检查模型名称
        if "404" in str(e):
             print(f"💡 提示: 模型 {AI_MODEL} 可能不存在，请尝试更换为 gpt-3.5-turbo 或其他模型。")
        return None

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
                full_content = fetch_full_content(entry.link)
                
                item = {
                    "source": feed_conf['name'],
                    "title": title,
                    "link": entry.link,
                    "summary": summary,  # 存入摘要
                    "full_content": full_content # 存入正文
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
        
    send("每日新闻", message)
    print("🏁 任务完成。")

if __name__ == "__main__":
    main()
