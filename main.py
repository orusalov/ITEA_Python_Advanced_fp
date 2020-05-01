from web_shop.bot.main import app, set_webhook, bot
from web_shop.bot.config import DEBUG

if __name__ == '__main__':

    if not DEBUG:
        set_webhook()
        app.run(port=8000)
    else:
        bot.polling()
