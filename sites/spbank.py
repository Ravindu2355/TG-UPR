import json
import re
import requests
from bs4 import BeautifulSoup
import random
import string

# Generate a random string of 8 characters
random_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def extract(url):
    try:
        # Fetch the webpage
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-CH-UA": '"Not-A.Brand";v="99", "Chromium";v="124"',
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
            "Referer": url
        }
        response = requests.get(url, headers=headers, timeout=10)

        # Check for request failure
        if response.status_code != 200:
            return {"error": f"Failed to fetch page, status code: {response.status_code}"}

        # Parse the HTML
        #print(response.text)
        #with open(f"{random_filename}.html", "w") as file:
            #file.write(response.text)
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract JSON-LD data
        json_ld_script = soup.find("script", {"type": "application/ld+json"})
        json_ld_data = json.loads(json_ld_script.string) if json_ld_script else {}

        # Extract JavaScript variables (stream_data)
        script_tags = soup.find_all("script", {"type": "text/javascript"})
        stream_data = {}

        for script in script_tags:
            print(script.string)
            script_text = script.string
            if script_text and "var stream_data" in script_text:
                # Clean the JavaScript content to get valid JSON
                print(f"Mst: {script_text}")
                match = re.search(r"var stream_data = ({.*?});", script_text, re.DOTALL)
                if match:
                    print(f"match: {match.group(1)}")
                    # Try cleaning the JSON data to fix single quotes and other issues
                    json_data = match.group(1)
                    json_data = json_data.replace("'", '"')  # Replace single quotes with double quotes
                    #json_data = re.sub(r'(\w+):', r'"\1":', json_data)  # Add quotes around unquoted keys
                    print(f"end j: {json_data}\n type: {type(json_data)}")
                    try:
                        stream_data = json.loads(json_data)
                    except json.JSONDecodeError as e:
                        return {"error": f"JSON parsing error in stream_data: {str(e)}"}
                break  # Stop after finding the first match

        # Construct final JSON output
        final_json = {
            "name": json_ld_data.get("name", ""),
            "description": json_ld_data.get("description", ""),
            "duration": json_ld_data.get("duration", ""),
            "thumbnail": json_ld_data.get("thumbnailUrl", ""),
            "links":{
                "mp4": {k: v[0] for k, v in stream_data.items() if k.endswith("p") and v},
                "m3u8": {k: v[0] for k, v in stream_data.items() if k.startswith("m3u8") and v},
        }
        }

        return final_json

    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parsing error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# Example Usage
#url = "https://spankbang.com/9mvsj/video/sana+anzyu+performs+an+oral+hookup+act+on+her+fucking+partner+in+this+uncensored+japanese+adult+video"
#result = extract_video_data(url)
#print(json.dumps(result, indent=4, ensure_ascii=False))

