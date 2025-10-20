from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = " 8241808907:AAFKZBbp0bgFjpMzv60QRm-WgFpFD_N2qaE"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好,我是机器人!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
