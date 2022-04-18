from aiohttp import web
import asyncio
import aiohttp
import aiofiles
import aiosqlite
import shutil
import os

async def get_connection() -> aiosqlite.Connection:
    try:
        conn = await aiosqlite.connect("service_database.db")
        cursor = await conn.cursor()
        
        await cursor.execute("""CREATE TABLE IF NOT EXISTS files_table(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            status TEXT,
            files TEXT);
            """)
        
        await conn.commit()
        await cursor.close()
        
        return conn
    except Exception as e:
        print(e)
        await conn.close()


async def download_archive(url: str, id: str, conn: aiosqlite.Connection) -> None:
    start = url.rfind("/")
    archive_filename = url[start:]

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                os.mkdir(f"files/{id}")
                async with aiofiles.open(f"files/{id}/{archive_filename}", mode="wb") as f:
                    await f.write(await response.read())
    
    async with conn.cursor() as cursor:
        await cursor.execute("UPDATE files_table SET status='unpacking';") 
        await conn.commit()

        shutil.unpack_archive(f"files/{id}/{archive_filename}", f'files/{id}/unpack')
        await cursor.execute("UPDATE files_table SET status='ok', files='{}';".format(', '.join(os.listdir(f'files/{id}/unpack'))))
        await conn.commit()

async def post_handler(request: web.Request) -> web.json_response:
    
    request_json = await request.json()
    request_json: dict
    url = request_json["url"]

    conn = request.app['db']
    conn: aiosqlite.Connection

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with conn.cursor() as cursor:
                        await cursor.execute("INSERT INTO files_table(status) VALUES ('downloading')")
                        await conn.commit()
                        id = cursor.lastrowid
                else:
                    res = web.json_response({"error_status":response.status})
                    return res

        res = web.json_response({"archive_id": id})
        await res.prepare(request)
        await res.write_eof()
        
        asyncio.create_task(download_archive(url, id, conn))
        
        return res
    except Exception as e:
        print(e)            
    
    
async def get_handler(request: web.Request) -> web.Response:
    
    id = request.match_info['id']
    conn = request.app['db']
    conn: aiosqlite.Connection

    async with conn.cursor() as cursor:
        await cursor.execute(f"SELECT status, files FROM files_table WHERE id='{id}'")
        row = await cursor.fetchone()

        if row:
            if row[0] == 'ok': 
                return web.json_response({"status": row[0], "files": row[1].split(", ")})
            return web.json_response({"status": row[0]})
        return web.json_response({"error": "incorrect input"})
        
    
async def delete_handler(request: web.Request) -> web.Response:

    id = request.match_info['id']
    conn = request.app['db']
    conn: aiosqlite.Connection

    async with conn.cursor() as cursor:
        await cursor.execute(f"SELECT status, files FROM files_table WHERE id='{id}'")
        row = await cursor.fetchone()

    if row:
        response = web.json_response({"status": "deleted"})
        await response.prepare(request)
        await response.write_eof()

        asyncio.create_task(delete_files(conn, id))
        
        return response
    else:
        return web.json_response({"error": "incroccect input"})

async def delete_files(conn: aiosqlite.Connection, id: str):
    async with conn.cursor() as cursor:
        await cursor.execute(f"SELECT status, files FROM files_table WHERE id='{id}'")
        row = await cursor.fetchone()

        while row[0] != "ok":
            await asyncio.sleep(3)
            await cursor.execute(f"SELECT status, files FROM files_table WHERE id='{id}'")
            row = await cursor.fetchone()

        await cursor.execute(f"DELETE FROM files_table WHERE id={id}")
        await conn.commit()

    shutil.rmtree(f"files/{id}")
    

async def main(app: web.Application):
    print("Starting http service!")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=8080)
    await site.start()

    await asyncio.Event().wait() 


async def init_app(conn: aiosqlite.Connection) -> web.Application:
    app = web.Application()
    app.add_routes([web.get('/archive/{id}', get_handler),
                    web.post('/archive', post_handler),
                    web.delete('/archive/{id}', delete_handler)]
    )
    app['db'] = conn
    
    return app

if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    
    try:
        conn = loop.run_until_complete(get_connection())
        app = loop.run_until_complete(init_app(conn))
        asyncio.run(main(app))
    except KeyboardInterrupt:
        print("Off http service!")
    except Exception as ex:
        print(ex)
    finally:
        loop.run_until_complete(app['db'].close())