"""
Default Django config settings for ping-server project
"""


# IMPORTANT: change the secret key to something random
SECRET_KEY = 'pingpingpingpingpingpingpingpingpingpingpingpingpi'

# Set this to a list of strings, each a valid hostname for this server.
# only use '*' in development - it may leave you vulnerable to attack
# ALLOWED_HOSTS = ['localhost', 'www.example.com', 'www']
ALLOWED_HOSTS = ['*']

# you may want to change database credentials
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ping',
        'USER': 'ping',
        'PASSWORD': 'ping',
        'HOST': 'ping_mariadb',
        'PORT': '3306',
    }
}
