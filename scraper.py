import re
import html
import requests

BASE = "https://tvwatch.app"
OUT = "tvwatch_all.m3u"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# Indian Bangla priority order
PRIORITY = [
    "Star Jalsha",
    "Star Jalsha HD",
    "Zee Bangla",
    "Zee Bangla HD",
    "Colors Bangla",
    "Colors Bangla HD",
    "Sun Bangla",
    "Sun Bangla HD",
    "Sony Aath",
    "Aakash Aath",
    "Ruposhi Bangla",
    "Enterr10 Bangla",
    "DD Bangla",
    "DD Tripura",
    "R Plus",
    "R Plus Gold",
    "Rongeen TV",
    "Zee Bangla Sonar",
    "Jalsha Movies",
    "Jalsha Movies HD",
    "Colors Bangla Cinema",
    "Zee Bangla Cinema",
    "Khushboo Bangla",
    "ABP Ananda",
    "News18 Bangla",
    "Zee 24 Ghanta",
    "TV9 Bangla",
    "Republic Bangla",
    "Kolkata TV",
    "Calcutta News",
    "News Time",
    "RCTV Sangbad",
    "High News",
    "Sangeet Bangla",
    "Dhoom Music",
    "ON TV",
    "Tara News",
    "Tara Newz",
    "Bangla Time",
    "Mahuaa Khobor",
    "Artage News",
    "ETV News Bangla",
    "Woman TV",
    "Bangla Talkies",
    "Sananda TV",
    "Mahuaa Bangla",
    "Aamar Cinema",
    "Music F Fatafati",
    "Channel 8",
    "24 Ghanta",
    "Zee Bangla Sonar Movies"
]


def clean(x):
    if not x:
        return ""

    x = html.unescape(x)

    x = x.replace(r'\/', '/')
    x = x.replace(r'\u0026', '&')
    x = x.replace(r'\"', '"')

    return x.strip()


def normalize(name):
    return re.sub(
        r'[^a-z0-9]+',
        '',
        name.lower()
    )


def find_logo(block):
    """
    TvWatch channel block থেকে logo খোঁজে।

    বিভিন্ন সম্ভাব্য field:
    logo
    logo_url
    image
    image_url
    thumbnail
    thumbnail_url
    poster
    icon
    """

    logo_fields = [
        "logo",
        "logo_url",
        "logoUrl",
        "image",
        "image_url",
        "imageUrl",
        "thumbnail",
        "thumbnail_url",
        "thumbnailUrl",
        "poster",
        "poster_url",
        "posterUrl",
        "icon",
        "icon_url",
        "iconUrl"
    ]

    for field in logo_fields:

        pattern = (
            r'"'
            + re.escape(field)
            + r'"\s*:\s*"([^"]+)"'
        )

        match = re.search(
            pattern,
            block,
            re.I
        )

        if match:

            logo = clean(
                match.group(1)
            )

            if re.match(
                r'https?://',
                logo,
                re.I
            ):
                return logo

    return ""


print("Getting country list...")

home_response = session.get(
    BASE + "/",
    timeout=30
)

home = home_response.text

countries = sorted(set(
    x.lower()
    for x in re.findall(
        r'/country/([a-z]{2})(?:["\'/?#])',
        home,
        re.I
    )
))

print(
    "Countries found:",
    len(countries)
)

all_channels = []

logo_count = 0

for number, country in enumerate(
    countries,
    1
):

    try:

        url = f"{BASE}/country/{country}"

        response = session.get(
            url,
            timeout=30
        )

        if response.status_code != 200:

            print(
                f"[{number}/{len(countries)}] "
                f"{country.upper()} "
                f"HTTP {response.status_code}"
            )

            continue

        data = clean(
            response.text
        )

        blocks = re.split(
            r'"channel"\s*:\s*\{',
            data
        )[1:]

        count = 0

        for block in blocks:

            # ---------------------------
            # Channel name
            # ---------------------------

            name_match = re.search(
                r'"name"\s*:\s*"([^"]+)"',
                block
            )

            if not name_match:
                continue

            name = clean(
                name_match.group(1)
            )

            # ---------------------------
            # Channel logo
            # ---------------------------

            logo = find_logo(block)

            if logo:
                logo_count += 1

            # ---------------------------
            # Streams
            # ---------------------------

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

                stream_url = clean(
                    stream_url
                )

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

                all_channels.append({

                    "country": country.upper(),

                    "name": name,

                    "logo": logo,

                    "url": stream_url
                })

                count += 1

        print(
            f"[{number}/{len(countries)}] "
            f"{country.upper()} : {count}"
        )

    except Exception as e:

        print(
            f"[{number}/{len(countries)}] "
            f"{country.upper()} ERROR: {e}"
        )


# -------------------------------
# Remove duplicate URLs
# -------------------------------

seen = set()
unique = []

for item in all_channels:

    if item["url"] in seen:
        continue

    seen.add(
        item["url"]
    )

    unique.append(
        item
    )

all_channels = unique


# -------------------------------
# Bangladesh FIRST
# -------------------------------

bd = [
    x for x in all_channels
    if x["country"] == "BD"
]


# -------------------------------
# Indian Bangla PRIORITY
# -------------------------------

india = [
    x for x in all_channels
    if x["country"] == "IN"
]


priority_map = {
    normalize(name): position
    for position, name in enumerate(
        PRIORITY
    )
}


def priority_index(item):

    name = normalize(
        item["name"]
    )

    # Exact match
    if name in priority_map:
        return priority_map[name]

    # Partial match
    for p_name, position in priority_map.items():

        if (
            p_name in name
            or name in p_name
        ):
            return position

    return 999999


india_priority = sorted(
    india,
    key=priority_index
)


# -------------------------------
# Other India channels
# -------------------------------

priority_urls = set(
    x["url"]
    for x in india_priority
)

india_other = [
    x for x in india
    if x["url"] not in priority_urls
]


# -------------------------------
# Other countries
# -------------------------------

others = [
    x for x in all_channels
    if x["country"]
    not in ("BD", "IN")
]


# -------------------------------
# Final order
# -------------------------------

final_channels = (
    bd
    + india_priority
    + india_other
    + others
)


print()
print("==============================")
print("FINAL ORDER")
print("Bangladesh :", len(bd))
print("India      :", len(india))
print("Priority   :", len(india_priority))
print("Other India:", len(india_other))
print("Other      :", len(others))
print("TOTAL      :", len(final_channels))
print("LOGOS      :", logo_count)
print("==============================")


# -------------------------------
# Write M3U
# -------------------------------

with open(
    OUT,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "#EXTM3U\n"
    )

    for item in final_channels:

        name = item["name"].replace(
            '"',
            "'"
        )

        logo = item.get(
            "logo",
            ""
        ).replace(
            '"',
            "'"
        )

        # --------------------------------
        # M3U EXTINF
        # --------------------------------

        if logo:

            file.write(
                f'#EXTINF:-1 '
                f'tvg-country="{item["country"]}" '
                f'tvg-name="{name}" '
                f'tvg-logo="{logo}",'
                f'{name}\n'
            )

        else:

            file.write(
                f'#EXTINF:-1 '
                f'tvg-country="{item["country"]}" '
                f'tvg-name="{name}",'
                f'{name}\n'
            )

        file.write(
            item["url"]
            + "\n"
        )


print()
print("DONE")
print("File:", OUT)
print(
    "Channels:",
    len(final_channels)
)
print(
    "Channels with logo:",
    sum(
        1
        for x in final_channels
        if x.get("logo")
    )
)
