import requests
from bs4 import BeautifulSoup
import json, re

def extract_json_from_url(url):
    # Fetch the HTML content from the URL
    headers = {"User-Agent": "Mozilla/5.0"}  # To avoid bot detection
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"error": f"Failed to fetch page, status code: {response.status_code}"}

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the <script type="application/ld+json"> tag
    json_script = soup.find("script", {"type": "application/ld+json"})

    if json_script:
        try:
            # Load and parse the JSON data
            json_data = json.loads(json_script.string)
            return json_data  # Return as a Python dictionary
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format"}

    return {"error": "JSON data not found"}

# Example usage:
#url = "https://www.eporner.com/video-CllgqD27lfH/eden-ivy-couch-fuck-with-a-hot-guy/"  # Replace with actual URL
#parsed_json = extract_json_from_url(url)

# Print formatted JSON
#print(json.dumps(parsed_json, indent=4))

def get_download_links(url):
    # Fetch the HTML content from the URL
    response = requests.get(url)
    html = response.text

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    download_data = {"AV1": {}, "H264": {}}

    # Find all the quality sections (i.e., <u> tags for 240p, 360p, etc.)
    for tag in soup.find_all("u"):
        quality = tag.text.strip(":")  # Extract resolution (e.g., "240p")
        links = tag.find_next_siblings("span")  # Get both AV1 and H264 links

        # Loop through the links and extract relevant data
        for link_span in links:
            a_tag = link_span.find("a")
            if a_tag:
                format_type = "AV1" if "av1" in a_tag["href"] else "H264"
                file_info = a_tag.text.strip().split("(")  # Split to get the quality and file size
                print(a_tag.text)
                # Ensure that file_info has valid elements
                if len(file_info) > 1:
                    #file_size = file_info[1].replace(")", "")  # Clean file size
                    match = re.search(r'(\d+\.\d+\s?MB)', a_tag.text)

                    if match:
                       file_size = match.group(1)  # This will be '165.39 MB'
                       print(file_size)
                    else:
                       print("No file size found")
                       file_size = "Unknown"  # Default if file size is not found
                else:
                    file_size = "Unknown"  # Default if file size is not found
                # Construct the key by combining the resolution, format type (AV1 or H264), and file size
                quality = quality.split(' ')[0]
                print(file_size)
                
                key = f"{quality}☆{format_type}☆{file_size.replace(' ', '')}"
                print(key)

                # Store the download link in the corresponding section
                download_data[format_type][key] = "https://www.eporner.com" + a_tag["href"]

    # Return the JSON data
    return download_data

def extract(url):
  try:
     info = extract_json_from_url(url)
  except Exception as e:
     return {"error": f"Unexpected error on info extract: {str(e)}"}
  try:
     dls = get_download_links(url)
  except Exception as e:
     return {"error": f"Unexpected error on dl link extract: {str(e)}"}
  thumb = info.get("thumbnailUrl","")
  final_json = {
            "name": info.get("name", ""),
            "description": info.get("description", ""),
            "duration": info.get("duration", ""),
            "thumbnail": info.get("image",""),
            "links":dls
  }
  return final_json

 
  
# Example usage:
# Replace with the actual URL
#json_output = get_download_links(url)
#print(json_output)
