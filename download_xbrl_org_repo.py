import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def download_file(url, target_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"Downloaded: {target_path}")
    else:
        print(f"Failed to download: {url}")

def get_links_from_page(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
        return [link for link in links if urlparse(link).path and not link.endswith('/')]
    return []

def download_xbrl_files(target_directory):
    valid_extensions = ('.xsd', '.dtd', '.xml')  # Define valid file extensions
    for year in range(2001, 2024):  # Loop through years 2001 to 2023
        base_url = f"https://www.xbrl.org/{year}/"
        links = get_links_from_page(base_url)
        for link in links:
            filename = os.path.basename(urlparse(link).path)
            if not filename:
                continue  # Skip invalid links
            # Check if file has a valid extension
            if not filename.lower().endswith(valid_extensions):
                continue  # Skip files that don't match desired extensions
            year_folder = os.path.join(target_directory, 'resources', 'http', 'www.xbrl.org', str(year))
            target_path = os.path.join(year_folder, filename)
            download_file(link, target_path)

# Example usage
download_xbrl_files("./")