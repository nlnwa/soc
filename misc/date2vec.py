# Trying to convert date to periodic values between -1 and 1 for model input purposes
import time
from datetime import datetime, timedelta
import numpy as np


def date2vec(date: datetime):
    first_of_year = datetime(date.year, 1, 1)
    first_of_next_year = datetime(date.year + 1, 1, 1)

    year_fraction_done = (date - first_of_year) / (first_of_next_year - first_of_year)

    first_of_month = datetime(date.year, date.month, 1)
    first_of_next_month = datetime(date.year, date.month + 1, 1)

    month_fraction_done = (date - first_of_month) / (first_of_next_month - first_of_month)

    first_of_week = (date - timedelta(days=date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    first_of_next_week = first_of_week + timedelta(days=7)
    week_fraction_done = (date - first_of_week) / (first_of_next_week - first_of_week)

    day_fraction_done = (date.hour + (date.minute + (date.second + date.microsecond / 1000000) / 60) / 60) / 24

    return tuple(np.cos(2 * np.pi * fd) for fd in
                 [year_fraction_done, month_fraction_done, week_fraction_done, day_fraction_done])


if __name__ == '__main__':
    while True:
        print(date2vec(datetime.now()))
        time.sleep(60)
