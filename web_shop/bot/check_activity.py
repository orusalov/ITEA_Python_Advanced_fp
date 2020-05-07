from web_shop.bot.main import bot
from telebot.apihelper import ApiException
from web_shop.db.models import Customer
from .config import CHECK_TIME_INTERVAL

from timeloop import Timeloop
from datetime import timedelta

tl = Timeloop()


@tl.job(interval=timedelta(seconds=CHECK_TIME_INTERVAL))
def job_del_customer_if_inactive():
    for customer in Customer.objects(is_archived=False):
        try:
            bot.send_chat_action(action='typing', chat_id=customer.user_id)
        except ApiException:
            customer.archive()
            print(f'Archived customer {customer.user_id}')

# tl.start() # block=True
