import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
news_api_key = os.getenv("NEWS_API_KEY")

# Init: .env 파일에서 로드한 API 키 사용
newsapi = NewsApiClient(api_key=news_api_key)

# 오늘 날짜 구하기
today = datetime.today().strftime('%Y-%m-%d')

# 한달 전 날짜 구하기
one_month_ago = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

# 영어 기사 검색 (최신 헤드라인)
all_en_articles = newsapi.get_everything(
    q='stock OR market OR investment OR finance',
    from_param=one_month_ago,
    to=today,
    language='en',
    sources='bbc-news,the-verge,cnn',
    sort_by='relevancy',
    page=1
)

# Selenium WebDriver 설정 (헤드리스 모드)
def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저 창을 띄우지 않음
    chrome_options.add_argument("--disable-gpu")  # GPU 비활성화
    chrome_options.add_argument("--no-sandbox")  # 리눅스 환경에서 필요한 옵션
    chrome_options.add_argument("--disable-dev-shm-usage")  # 공유 메모리 사용 제한 해결
    chrome_options.add_argument("start-maximized")  # 창을 최대화
    chrome_options.add_argument("disable-infobars")  # 정보 바 비활성화
    chrome_options.add_argument("--disable-extensions")  # 확장 프로그램 비활성화
    chrome_options.add_argument("--disable-dev-shm-usage")  # /dev/shm 사용 비활성화
    chrome_options.add_argument("--remote-debugging-port=9222")  # 원격 디버깅

    # ChromeDriverManager를 사용하여 자동으로 크롬 드라이버 다운로드 및 설정
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# 기사 본문 크롤링 함수 (Selenium 사용)
def get_article_content_with_selenium(url):
    driver = get_selenium_driver()
    try:
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # <p> 태그를 찾아서 본문을 추출 (웹사이트 구조에 맞게 수정 가능)
        paragraphs = soup.find_all('p')
        article_content = ' '.join([p.get_text() for p in paragraphs])

        driver.quit()  # 드라이버 종료
        return article_content
    except Exception as e:
        print(f"Error crawling {url}: {e}")
        driver.quit()
        return None

# 모든 기사에 대해 본문 크롤링 (Selenium 사용)
for article in all_en_articles['articles']:
    url = article['url']
    print(f"Crawling URL: {url}")
    article_content = get_article_content_with_selenium(url)
    article['full_content'] = article_content  # 크롤링한 본문을 추가

# JSON 파일 저장
current_file_directory = os.getcwd()
json_filename = os.path.join(current_file_directory, "full_english_news_articles_selenium.json")

with open(json_filename, mode='w', encoding='utf-8') as json_file:
    json.dump(all_en_articles, json_file, ensure_ascii=False, indent=4)

# Output confirmation
print(f"Data with full content has been written to {json_filename}")
