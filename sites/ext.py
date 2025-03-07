import sys
import importlib
import urllib.parse

# Dictionary to map domains to extractor scripts
EXTRACTORS = {
    'spankbang.com': 'sites.spbank',
    'eporner': 'sites.epr',
}

def get_domain(url):
    """Extract the domain from a URL."""
    parsed_url = urllib.parse.urlparse(url)
    return parsed_url.netloc.lower()

def find_s(domain):
    for k in EXTRACTORS:
        if k in domain:
            return k
    return None

    
def run_extractor(url):
    """Run the corresponding extractor script based on the domain."""
    domain = get_domain(url)
    key = find_s(domain)
    if key:
        script_name = EXTRACTORS[key]
        # Dynamically import the module based on the domain
        extractor = importlib.import_module(script_name)
        # Assuming each script has an `extract_data(url)` function to extract data
        data = extractor.extract(url)
        return data
    else:
        print(f"No extractor found for domain: {domain}")
        return {"error":"Sorry!,\nI'm not supporting for extract data from that site😓"}

