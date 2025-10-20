import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 从 Render 环境变量中安全读取 Token
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好,我是机器人!🤖")

def main():
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN 未设置,请在 Render 环境变量中添加!")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
