# -*- coding: utf-8 -*-
"""
email_novel_bot for Render (Gmail-ready)

ENV required (set in Render Environment):
  EMAIL_ACCOUNT  - your bot Gmail address (e.g. yourbot@gmail.com)
  EMAIL_PASSWORD - app password (16-char) for that Gmail account
  CHECK_INTERVAL - (optional) seconds between mailbox checks, default 25

Usage:
  - Upload this project to Render (or any VPS)
  - Set the environment variables above in Render
  - Start command: python bot.py
  - Send an email to EMAIL_ACCOUNT with the novel directory URL in the subject or body
  - The bot will crawl and reply to the sender with the TXT attached
"""

import os
import time
import re
import imaplib
import email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# read env
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "25"))
MAX_CHAPTERS = int(os.getenv("MAX_CHAPTERS", "2000"))

if not EMAIL_ACCOUNT or not EMAIL_PASSWORD:
    raise SystemExit("Missing EMAIL_ACCOUNT or EMAIL_PASSWORD environment variables. Please set them in Render.")

# IMAP/SMTP servers (Gmail)
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15"
}

def safe_get(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text
    except Exception as e:
        print(f"[WARN] Request failed: {url}  -> {e}")
        return None

def extract_title_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not title_tag:
        possible = soup.find(["h1","h2"])
        if possible and possible.get_text(strip=True):
            title_tag = possible.get_text(strip=True)
        else:
            meta = soup.find("meta", attrs={"property":"og:title"}) or soup.find("meta", attrs={"name":"title"})
            if meta and meta.get("content"):
                title_tag = meta.get("content")
            else:
                title_tag = "novel"
    title_tag = re.sub(r"[\r\n\t]", " ", title_tag).strip()
    title_tag = re.sub(r'[\\/:*?"<>|]', "_", title_tag)
    return title_tag or "novel"

def extract_chapters(list_url, html):
    soup = BeautifulSoup(html, "html.parser")
    exclude = re.compile(r"(上一章|下一章|目录|首页|尾页|推荐|阅读|返回|作者|章节列表)", re.I)
    chapters = []
    for a in soup.find_all("a", href=True):
        name = (a.get_text() or "").strip()
        href = a["href"]
        if not name or exclude.search(name):
            continue
        full = urljoin(list_url, href)
        if full.startswith(("http://","https://")):
            chapters.append((name, full))
    # dedupe preserve order
    seen = set(); uniq = []
    for t,u in chapters:
        if u not in seen:
            seen.add(u); uniq.append((t,u))
    return uniq

def auto_sort(chapters):
    nums = []
    for t,_ in chapters:
        m = re.search(r"\d+", t)
        if m:
            try: nums.append(int(m.group()))
            except: pass
    if len(nums)>=2 and nums[0] > nums[-1]:
        chapters.reverse()
    return chapters

def clean_text(text):
    bad = ["上一章","下一章","目录","推荐","返回书页","手机阅读","会员","充值"]
    for b in bad:
        text = text.replace(b, "")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def crawl_novel(list_url, max_chapters=MAX_CHAPTERS):
    html = safe_get(list_url)
    if not html:
        return None, None
    title = extract_title_from_html(html)
    chapters = extract_chapters(list_url, html)
    chapters = auto_sort(chapters)
    if not chapters:
        return None, None
    if len(chapters) > max_chapters:
        chapters = chapters[:max_chapters]
    filename = f"{title}.txt"
    with open(filename, "w", encoding="utf-8") as fw:
        for idx, (t, link) in enumerate(chapters, 1):
            print(f"[{idx}/{len(chapters)}] {t} -> {link}")
            page = safe_get(link)
            if not page:
                fw.write(f"{'='*30}\n{t}\n{'='*30}\n[获取失败]\n\n")
                continue
            soup = BeautifulSoup(page, "html.parser")
            content = (soup.find("div", id=re.compile(r"content|chapter", re.I))
                       or soup.find("div", class_=re.compile(r"content|chapter|read|text", re.I))
                       or soup.body)
            text = content.get_text("\n", strip=True) if content else "[未提取到正文]"
            text = clean_text(text)
            fw.write(f"{'='*30}\n{t}\n{'='*30}\n{text}\n\n")
            time.sleep(0.02)
    return filename, title

def send_reply(to_addr, subject, body, attachment_path=None):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ACCOUNT
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as s:
        s.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        s.send_message(msg)
    print(f"[INFO] replied to {to_addr} with attachment={attachment_path}")

URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.I)

def decode_message_payload(msg):
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    try:
                        text += payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except:
                        text += payload.decode("utf-8", errors="ignore")
            elif ctype == "text/html" and not text:
                payload = part.get_payload(decode=True)
                if payload:
                    try:
                        html = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except:
                        html = payload.decode("utf-8", errors="ignore")
                    text += BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            try:
                text = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
            except:
                text = payload.decode("utf-8", errors="ignore")
    return text

def process_unseen():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            mail.logout(); return
        ids = data[0].split()
        if not ids:
            mail.logout(); return
        for num in ids:
            try:
                status, mdata = mail.fetch(num, "(RFC822)")
                if status != "OK": continue
                raw = mdata[0][1]
                msg = email.message_from_bytes(raw)
                frm = email.utils.parseaddr(msg.get("From"))[1]
                subj = msg.get("Subject") or ""
                body = decode_message_payload(msg)
                text = subj + "\n" + body
                urls = URL_RE.findall(text)
                if not urls:
                    send_reply(frm, "未找到链接", "未在邮件中检测到可用链接，格式示例: https://...")
                    mail.store(num, "+FLAGS", "\\Seen")
                    continue
                target = urls[0]
                print(f"[TASK] from={frm} url={target}")
                filename, title = crawl_novel(target)
                if filename:
                    send_reply(frm, f"小说《{title}》已完成", f"小说已爬取完成，见附件。", filename)
                else:
                    send_reply(frm, "爬取失败", "未能成功解析或爬取该链接，请确认链接为小说目录页。")
                mail.store(num, "+FLAGS", "\\Seen")
            except Exception as e:
                print("处理单邮件时出错:", e)
        mail.logout()
    except Exception as e:
        print("检查邮件失败:", e)

def main():
    print("Email novel bot running. Poll interval:", CHECK_INTERVAL, "seconds")
    while True:
        process_unseen()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
