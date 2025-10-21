import time
import os
import shutil
import asyncio

async def safe_download(message, dest):
    temp_file = await message.download(file_name=dest + ".temp")
    retries = 5
    while retries > 0:
        try:
            if os.path.exists(dest):
                os.remove(dest)
            shutil.move(temp_file, dest)
            return dest
        except PermissionError:
            await asyncio.sleep(0.3)
            retries -= 1
    final_dest = dest.replace(".", f"_{int(time.time())}.")
    shutil.move(temp_file, final_dest)
    return final_dest
