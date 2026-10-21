import requests

url = "http://localhost:2358/languages"

response = requests.get(url, timeout=5)
response.raise_for_status()

for language in response.json():
    if "python" in language["name"].lower():
        print(language)