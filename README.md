# 自动新闻推文发送器 (Daily News Bot)

这是一个简单的 Python 脚本，配合 GitHub Actions 使用，每天自动抓取 RSS 新闻并推送到你指定的 Webhook (如飞书、钉钉、Telegram 等)。

## 📁 目录结构

- `main.py`: 主程序，负责抓取 RSS 和发送消息。
- `requirements.txt`: Python 依赖库。
- `.github/workflows/daily_news.yml`: GitHub Actions 配置文件，定义了定时任务。

## 🚀 如何使用

### 1. 准备工作

1.  **Fork 或 Clone** 此代码库到你的 GitHub 账号。
2.  获取你的 **Webhook URL** (例如飞书机器人的 Webhook 地址)。

### 2. 配置 GitHub Secrets

为了安全起见，不要直接在代码中写 Webhook URL。请在 GitHub 仓库中配置 Secret：

1.  进入你的 GitHub 仓库页面。
2.  点击 **Settings** (设置) -> **Secrets and variables** -> **Actions**。
3.  点击 **New repository secret**。
4.  **Name**: 输入 `WEBHOOK_URL`。
5.  **Secret**: 粘贴你的 Webhook 地址。
6.  点击 **Add secret**。

### 3. 测试运行

- **手动触发**: 进入 **Actions** 标签页 -> 选择 **Daily News Sender** -> 点击 **Run workflow**。
- **自动运行**: 默认设置为每天北京时间早上 8:00 (UTC 0:00) 自动运行。

## ⚙️ 自定义配置

- **修改 RSS 源**: 打开 `main.py`，修改 `RSS_URL` 变量即可。
- **修改定时时间**: 打开 `.github/workflows/daily_news.yml`，修改 `cron` 表达式。

## 📦 本地运行

如果你想在本地测试：

```bash
pip install -r requirements.txt
python main.py
```
"# DailyNewsBot" 
