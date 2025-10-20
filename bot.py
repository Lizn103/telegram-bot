# -*- coding: utf-8 -*-
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ------------------- 自动识别 Token -------------------
TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("BOTTOKEN")
    or os.getenv("TOKEN")
)

if not TOKEN:
    raise ValueError("❌ 未检测到 Telegram Bot Token,请在 Render 环境变量中设置 BOT_TOKEN 或 BOTTOKEN 或 TOKEN")

# ------------------- 小说爬虫核心 -------------------
def get_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text
    except Exception as e:
        print("请求失败:", e)
        return ""

def extract_title(html):
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if not title_tag:
        return "novel"
    title = title_tag.get_text()
    title = re.sub(r"[\n\r\t]", "", title)
    title = re.sub(r"(\s*最新章节.*|\s*目录.*|_.*|小说.*)", "", title)
    return title.strip() or "novel"

def extract_chapters(list_url, html):
    soup = BeautifulSoup(html, "html.parser")
    chapters = []
    exclude = re.compile(r"(上一章|下一章|目录|首页|尾页|推荐|阅读|返回)", re.I)
    for a in soup.find_all("a", href=True):
        name = (a.get_text() or "").strip()
        href = a["href"]
        if not name or exclude.search(name):
            continue
        full_url = urljoin(list_url, href)
        if full_url.startswith(("http://", "https://")):
            chapters.append((name, full_url))
    return chapters

def auto_sort(chapters):
    nums = [int(re.search(r"\d+", t).group()) for t, _ in chapters if re.search(r"\d+", t)]
    if len(nums) >= 2 and nums[0] > nums[-1]:
        print("检测到倒序,自动翻转目录...")
        chapters.reverse()
    return chapters

def clean_content(text):
    bad_words = ["上一章", "下一章", "目录", "推荐", "返回书页", "手机阅读", "会员", "充值"]
    for b in bad_words:
        text = text.replace(b, "")
    return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

def crawl_novel(list_url):
    list_html = get_html(list_url)
    if not list_html:
        return None, None

    novel_name = extract_title(list_html)
    out_file = f"{novel_name}.txt"

    chapters = extract_chapters(list_url, list_html)
    chapters = auto_sort(chapters)
    if not chapters:
        return None, None

    with open(out_file, "w", encoding="utf-8") as f:
        for i, (title, url) in enumerate(chapters, 1):
            print(f"[{i}/{len(chapters)}] 爬取: {title}")
            html = get_html(url)
            if not html:
                f.write(f"{'='*30}\n{title}\n{'='*30}\n【获取失败】\n\n")
                continue
            soup = BeautifulSoup(html, "html.parser")
            content = (
                soup.find("div", id=re.compile(r"content|chapter", re.I))
                or soup.find("div", class_=re.compile(r"content|chapter|read|text", re.I))
                or soup.body
            )
            text = content.get_text("\n", strip=True) if content else "【未提取到正文】"
            text = clean_content(text)
            f.write(f"{'='*30}\n{title}\n{'='*30}\n{text}\n\n")
            time.sleep(0.01)

    return out_file, novel_name

# ------------------- Telegram 机器人部分 -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 你好,我是小说爬虫机器人!\n请直接发送小说目录页网址给我~")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ 请发送正确的网址。")
        return

    await update.message.reply_text("🔍 正在爬取小说,请稍候,这可能需要几分钟...")

    file_path, novel_name = crawl_novel(url)
    if not file_path:
        await update.message.reply_text("❌ 爬取失败,请检查目录页是否可访问。")
        return

    await update.message.reply_text(f"✅ 小说《{novel_name}》爬取完成,正在发送文件...")
    await update.message.reply_document(InputFile(file_path, filename=f"{novel_name}.txt"))

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.run_polling()

if __name__ == "__main__":
    main()
