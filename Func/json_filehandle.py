import json
import os
import random
import string
import tempfile

# Define the special directory path for JSON files
SPECIAL_DIR = os.path.join(tempfile.gettempdir(), "json_files")

# Ensure the directory exists
os.makedirs(SPECIAL_DIR, exist_ok=True)

def save_json(json_obj, filename=None):
    """Saves a given JSON object to a file within the special directory. 
    If no filename is provided, a random name will be used."""
    
    # If no filename is provided, generate a random filename
    if filename is None:
        filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + '.json'
    
    # Full path to the special directory
    temp_file_path = os.path.join(SPECIAL_DIR, filename)
    
    # Write the JSON object to the file
    with open(temp_file_path, 'w') as temp_file:
        json.dump(json_obj, temp_file, indent=4)
    
    print(f"JSON data saved to: {temp_file_path}")
    return filename

def read_json_from_file(filename):
    """Reads a JSON file from the special directory and returns the parsed JSON object."""
    
    file_path = os.path.join(SPECIAL_DIR, filename)  # Get the full file path
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    # Read the file and parse the JSON content
    with open(file_path, 'r') as json_file:
        json_data = json.load(json_file)
    
    return json_data

def delete_json(filename):
    """Deletes a JSON file from the special directory using the given filename."""
    
    file_path = os.path.join(SPECIAL_DIR, filename)  # Get the full file path
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    # Delete the file
    os.remove(file_path)
    print(f"File {filename} has been deleted.")

# Example usage
def get_json(filename):
    try:
        json_data = read_json_from_file(filename)  # Use the path returned from save_json
        print(json_data)
        return json_data
    except FileNotFoundError as e:
        print(e)
        return {"error": "Json not found!"}

# Example usage of saving and reading JSON data
json_data = {
    "name": "Sana Anzyu",
    "description": "A sample description for the video",
    "duration": "PT00H05M04S",
    "thumbnail": "https://example.com/thumbnail.jpg",
}

# Save the JSON data
#json_file_path = save_json(json_data)

# Read the saved JSON data
#get_json(os.path.basename(json_file_path))

# Now delete the JSON file
#delete_json_file(os.path.basename(json_file_path))
