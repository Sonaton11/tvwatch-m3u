import re
import html
import requests

BASE = "https://tvwatch.app"
OUT = "tvwatch_all.m3u"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

print("Getting country list...")

home = session.get(BASE + "/", timeout=30).text

countries = sorted(set(
    x.lower()
    for x in re.findall(
        r'/country/([a-z]{2})(?:["\'/?#])',
        home,
        re.I
    )
))

# Bangladesh → India → Other countries
countries = (
    [x for x in countries if x == "bd"] +
    [x for x in countries if x == "in"] +
    [x for x in countries if x not in ("bd", "in")]
)

print("Countries:", len(countries))

seen = set()
items = []

def clean(x):
    x = html.unescape(x)
    x = x.replace(r'\/', '/')
    x = x.replace(r'\u0026', '&')
    x = x.replace(r'\"', '"')
    return x.strip()

for number, country in enumerate(countries, 1):

    try:
        url = f"{BASE}/country/{country}"

        response = session.get(url, timeout=30)

        if response.status_code != 200:
            print(
                f"[{number}/{len(countries)}] "
                f"{country.upper()} HTTP {response.status_code}"
            )
            continue

        data = clean(response.text)

        blocks = re.split(
            r'"channel"\s*:\s*\{',
            data
        )[1:]

        count = 0

        for block in blocks:

            name_match = re.search(
                r'"name"\s*:\s*"([^"]+)"',
                block
            )

            if not name_match:
                continue

            channel_name = clean(
                name_match.group(1)
            )

            stream_match = re.search(
                r'"streams"\s*:\s*\[(.*?)(?="channel"\s*:\s*\{|$)',
                block,
                re.S
            )

            if not stream_match:
                continue

            urls = re.findall(
                r'"url"\s*:\s*"([^"]+)"',
                stream_match.group(1),
                re.I
            )

            for stream_url in urls:

                stream_url = clean(stream_url)

                if not re.match(
                    r'https?://',
                    stream_url,
                    re.I
                ):
                    continue

                if not re.search(
                    r'(m3u8|/live/|/play/|/stream|playlist)',
                    stream_url,
                    re.I
                ):
                    continue

                if stream_url in seen:
                    continue

                seen.add(stream_url)

                safe_name = channel_name.replace('"', "'")

                items.append(
                    f'#EXTINF:-1 '
                    f'tvg-country="{country.upper()}" '
                    f'tvg-name="{safe_name}",'
                    f'{safe_name}\n'
                    f'{stream_url}'
                )

                count += 1

        print(
            f"[{number}/{len(countries)}] "
            f"{country.upper()} : {count}"
        )

    except Exception as error:

        print(
            f"[{number}/{len(countries)}] "
            f"{country.upper()} ERROR: {error}"
        )

with open(
    OUT,
    "w",
    encoding="utf-8"
) as file:

    file.write("#EXTM3U\n")
    file.write("\n".join(items))
    file.write("\n")

print()
print("==============================")
print("DONE")
print("Countries :", len(countries))
print("Streams   :", len(items))
print("File      :", OUT)
print("==============================")
