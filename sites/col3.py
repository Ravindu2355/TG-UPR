import requests
import subprocess
import re
from urllib.parse import urlparse, parse_qs


def ex_col3(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    video_id = params.get("id", [None])[0]
    u = f"https://col3negoriginal.tv/embed.php?id={video_id}&autoplay=1"
    html = requests.get(u).text
    match = re.search(r'<iframe[^>]+src=[\'"]([^\'"]+)[\'"]', html)
    if match:
        src = match.group(1)
        return src
    return None

def get_video_id(url):
    return url.split("/")[-1]

def get_metadata(video_id):
    headers = {
      "Accept": "*/*",
      "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
      "Sec-CH-UA": "\"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
      "Sec-CH-UA-Mobile": "?1",
      "Sec-CH-UA-Platform": "\"Android\"",
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-site",
      "Referer": "https://geo.dailymotion.com/",
      "Origin": "https://geo.dailymotion.com",
      "User-Agent": "Mozilla/5.0 (Linux; Android 11; CPH2001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
    }
    api = f"https://www.dailymotion.com/player/metadata/video/{video_id}?embedder=https%3A%2F%2Fwww.dailymotion.com%2Fvideo%2F{video_id}&geo=1&is_native_app=0&app=com.dailymotion.neon&client_type=webapp"
    return requests.get(api,headers= headers).json()

def get_m3u8_url(metadata):
    return metadata["qualities"]["auto"][0]["url"]

def parse_m3u8(m3u8_url):
    print(m3u8_url)
    headers = {
    "Accept": "*/*",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Sec-CH-UA": "\"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
    "Sec-CH-UA-Mobile": "?1",
    "Sec-CH-UA-Platform": "\"Android\"",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Referer": "https://geo.dailymotion.com/",
    "Origin": "https://geo.dailymotion.com",
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; CPH2001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
    }
    res = requests.get(m3u8_url, headers=headers).text
    print(res)
    qualities = {}
    lines = res.split("\n")

    for i, line in enumerate(lines):
        if "RESOLUTION" in line:
            match = re.search(r"RESOLUTION=\d+x(\d+)", line)
            if match:
                quality = match.group(1)
                stream_url = lines[i+1]
                qualities[quality] = stream_url

    return qualities

def download(stream_url, quality):
    print(f"\n⬇️ Downloading {quality}p...\n")

    cmd = [
        "ffmpeg",
        "-referer", "https://geo.dailymotion.com/",
        "-user_agent", "Mozilla/5.0",
        "-i", stream_url,
        "-c", "copy",
        f"output_{quality}p.mp4"
    ]

    subprocess.run(cmd)

def extract(url):
    
    if "col3" in url:
        url = ex_col3(url)
    
    if "?" in url:
        url = url.split("?")[0]
    
    video_id = get_video_id(url)

    print("🔍 Fetching metadata...")
    metadata = get_metadata(video_id)

    if "error" in metadata:
        er = metadata.get("error",{})
        return {"error": f"Err: {er.get('code')}\nErr: {er.get('message')}" }
    
    json = {
        "name":metadata.get("title"),
        "thumbnail":metadata.get("thumbnails",{}).get("1080"),
        "description":"No Data!",
        "links":{
            "m3u8":{}
        },
        "duration":metadata.get("duration")
    }
    
    m3u8_url = get_m3u8_url(metadata)
    print("✄1�7 M3U8 URL found")

    print("📡 Fetching qualities...")
    qualities = parse_m3u8(m3u8_url)

    if not qualities:
        print("❄1�7 No qualities found")
        return {"error": f"Selection error: ❄1�7 No qualities found"}

    print("\nAvailable qualities:")
    for q in qualities:
        json["links"]["m3u8"][f"{q}p"] = qualities[q]
        print(f"- {q}p")
    
    print(json)
    
    return json
