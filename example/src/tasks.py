import tokit
from tokit.orm import peewee_init

from posts import Posts
config = tokit.Config(__file__)
config.set_env('developement')
peewee_init(config)

def create_tables():
    Posts.create_table()