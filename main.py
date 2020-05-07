from web_shop.bot.main import app, set_webhook, bot
from web_shop.bot.config import DEBUG, PORT
from web_shop.bot.check_activity import tl

if __name__ == '__main__':

    if not DEBUG:
        tl.start()
        set_webhook()
        app.run(port=PORT)
    else:
        tl.start()  # block=True
        bot.polling()

