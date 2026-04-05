import datetime

def get_current_date():
    return datetime.date.today().strftime('%Y-%m-%d')

def get_current_time():
    return datetime.datetime.now().strftime('%H:%M:%S')

def format_datetime(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')

