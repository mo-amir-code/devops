import requests,time,logging

urls=[
"http://www.example.com/nonexistentpage",
"http://httpstat.us/404",
"http://httpstat.us/500",
"https://www.google.com/"
]

logging.basicConfig(filename="uptime log.txt",level=logging.INFO)

def check_url_status(url):
    try:
        response=requests.get(url,timeout=5)
        code=response.status_code

        print("Checking URL:",url)
        print("Status Code:",code,response.reason)

        logging.info(f"{url} {code} {response.reason}")

        if 400<=code<500:
            print("ALERT: 4xx error encountered for URL:",url)
        elif 500<=code<600:
            print("ALERT: 5xx error encountered for URL:",url)
        else:
            print("The website is UP and running.")

        print()

    except:
        print("Error accessing",url)

def monitor_urls():
    while True:
        for url in urls:
            check_url_status(url)
        time.sleep(10)

monitor_urls()