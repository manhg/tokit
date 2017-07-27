import peewee
from tokit.orm import Model, ORM
from tokit import Request


class Posts(Model):
    title = peewee.TextField()
    content = peewee.TextField()


class PostsIndex(Request):
    URL = '/posts'

    async def get(self):
        rows = await ORM.execute(Posts.select())
        self.render('index.html', rows=rows)
