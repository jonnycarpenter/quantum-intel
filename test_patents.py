import requests
import json

def test_google_patents():
    url = "https://patents.google.com/xhr/query?url=q=(assignee:(Rigetti))&exp="
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    doc = data["results"]["cluster"][0]["result"][0]
    with open("test_patents.json", "w") as f:
        json.dump(doc, f, indent=2)

if __name__ == "__main__":
    test_google_patents()
