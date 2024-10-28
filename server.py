import asyncio

import tornado


class MainHandler(tornado.web.RequestHandler):
    def post(self):
        self.write(self.request.body)


async def main():
    tornado.web.Application([(r"/", MainHandler)]).listen(8000)
    await asyncio.Event().wait()


asyncio.run(main())
