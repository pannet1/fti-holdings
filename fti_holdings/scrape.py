import requests


referer_url = "https://kite.zerodha.com/chart/web/ciq/NSE/GABRIEL/277761?theme=dark"
url = "https://kite.zerodha.com/static/build/chart-beta.html?v=3.2.6#token=277761&symbol=GABRIEL&segment=NSE&volume=true&enctoken=E2gD%2BCjgOh2dO%2F5nkz1XMf2gfbMqaYkqOUmSJJrZeuAUhD2gMDFrISV9c0jX9zxEop9KDDnt0qb2sLQ%2FQtUg9Mxuirsj7Y9oJaX%2F20vOLWWfq9jqMEm8jQ%3D%3D&user_id=DK4219&access_token=&api_key=&source=&sdk=&theme=dark&chart_type=&build_version=&exchange=NSE&nice_name=&tick_size=0.05&inapp=true"


agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.9999.999 Safari/537.36"

# Define the Referer URL (the URL of the referring page)

# Define any other headers or data you want to include in the request
headers = {
    'User-Agent': agent,  # Optional user-agent header
    'Referer': referer_url  # Include the Referer header with the referrer URL
}

# Make the HTTP GET request with headers
response = requests.get(url, headers=headers)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    print("Request was successful.")
    print(response.text)
    # Process the response content as needed
else:
    print(f"Request failed with status code {response.status_code}.")
