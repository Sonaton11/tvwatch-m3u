import re
import requests
import concurrent.futures
import threading
import time

SRC = "tvwatch_all.m3u"
OUT = "tvwatch_live.m3u"

WORKERS = 50
TIMEOUT = 6
RETRIES = 2

lock = threading.Lock()

done = 0
live = 0
dead = 0

with open(SRC, "r", encoding="utf-8", errors="ignore") as f:
    data = f.read()

streams = re.findall(
    r'(#EXTINF:[^\n]*\nhttps?://[^\s]+)',
    data,
    re.I
)

print("Streams found:", len(streams))
print("Checking streams...")

def check(item):

    global done, live, dead

    lines = item.splitlines()

    if len(lines) < 2:
        return None

    url = lines[-1].strip()

    working = False

    for attempt in range(RETRIES + 1):

        try:

            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "*/*"
                },
                timeout=TIMEOUT,
                allow_redirects=True,
                stream=True
            )

            if 200 <= response.status_code < 400:

                try:
                    next(
                        response.iter_content(
                            chunk_size=1024
                        ),
                        None
                    )
                except:
                    pass

                working = True
                break

        except:
            pass

        if attempt < RETRIES:
            time.sleep(0.3)

    with lock:

        done += 1

        if working:
            live += 1
        else:
            dead += 1

        print(
            f"\rChecked: {done}/{len(streams)} | "
            f"LIVE: {live} | DEAD: {dead}",
            end="",
            flush=True
        )

    if working:
        return item

    return None


live_streams = []

with concurrent.futures.ThreadPoolExecutor(
    max_workers=WORKERS
) as executor:

    for result in executor.map(check, streams):

        if result:
            live_streams.append(result)


with open(
    OUT,
    "w",
    encoding="utf-8"
) as f:

    f.write("#EXTM3U\n")

    for item in live_streams:
        f.write(item + "\n")


print()
print()
print("==============================")
print("CHECK COMPLETE")
print("Total :", len(streams))
print("LIVE  :", live)
print("DEAD  :", dead)
print("File  :", OUT)
print("==============================")
