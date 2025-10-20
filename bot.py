from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 直接写上你的 Token(或用环境变量)
TOKEN = "8241808907:AAH6cTJQf59bLsxKEnYCTckO2m3wu9XiLug"

# 当用户发送 /start 时,回复一条消息
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好,我是机器人 🤖")

def main():
    # 新版用 Application.builder(),不是 Updater!
    app = Application.builder().token(TOKEN).build()

    # 添加命令处理器
    app.add_handler(CommandHandler("start", start))

    # 开始监听消息
    app.run_polling()

if __name__ == "__main__":
    main()
