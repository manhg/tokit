import datetime

class ApiError(Exception):
    pass


def str_now():
    return str(datetime.datetime.now())
