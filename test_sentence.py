from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_voice(chat_id=update.effective_chat.id, voice=r'files/speak.wav')
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=r'files/screenshot.png')


if __name__ == '__main__':
    TOKEN = '5882202891:AAFQZ-5YCZV7pJ6UyYXaSfx-yBggEU_pSw8'
    echo_handler = MessageHandler(filters.TEXT, test)
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(echo_handler)

    application.run_polling()
