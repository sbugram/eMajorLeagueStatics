import requests

def save_html():
    url = "https://www.emajorleague.com/statistics/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers)
    with open("page.html", "w", encoding="utf-8") as f:
        f.write(response.text)

if __name__ == "__main__":
    save_html()
