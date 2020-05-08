from web_shop.bot.main import app, set_webhook, bot
from web_shop.bot.config import DEBUG, PORT
from web_shop.bot.check_activity import tl

if __name__ == '__main__':

    # tl.start() # block=True
    if not DEBUG:
        set_webhook()
        app.run(port=PORT)
    else:
        bot.polling()
