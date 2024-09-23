def get_current_time():
  import datetime
  return datetime.datetime.now().strftime("%H:%M:%S")

def get_current_date():
  import datetime
  return datetime.date.today().strftime("%Y-%m-%d")

def get_user_name():
  return "John Doe"

def greet_user(name):
  return f"Hello, {name}!"
