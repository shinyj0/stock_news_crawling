import os
import requests
from bs4 import BeautifulSoup
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import time
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# .env 파일 로드
load_dotenv()

# 네이버 API 키 가져오기
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# 주식 관련 키워드 리스트
stock_prediction_keywords_kr = [
    "주식", "증권", "투자", "경제", "주가",
    "금융", "시장", "코스피", "코스닥", "배당",
    "인플레이션", "금리", "성장", "채권", "분석",
    "상장", "매도", "매수", "공매도", "IPO", "유동성",
    "ETF", "기업", "실적", "재무", "수익률", "차트",
    "포트폴리오", "리스크", "리밸런싱", "배당금"
]

# 텍스트 정제 함수
def clean_text(text):
    if text is None:
        return ""
    clean = BeautifulSoup(text, "html.parser").get_text()
    clean = re.sub(r'[■▲▶●]', '', clean)
    clean = re.sub(r'[\n\r\t]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'[^\w\s]', '', clean)
    return clean

# 네이버 뉴스 API 호출 함수
def get_naver_news(query, start=1, display=10, sort='sim'):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display={display}&start={start}&sort={sort}"
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Selenium 크롤링 함수
def get_article_content_dynamic(url):
    """
    Selenium을 이용하여 기사 URL에서 제목과 본문을 크롤링합니다.
    """
    # ChromeDriver 경로 설정
    driver_path = r"C:\Users\yejin\Downloads\chromedriver-win64(130.0.6723.31)\chromedriver-win64\chromedriver.exe"  # 올바른 경로 설정
    
    # Chrome 옵션 설정
    options = Options()
    options.add_argument("--headless")  # 브라우저 창을 표시하지 않음
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # WebDriver 초기화
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # URL 접속
        driver.get(url)
        
        # 크롤링 대기 시간
        driver.implicitly_wait(3)

        # 제목 크롤링
        try:
            title_element = driver.find_element(By.CSS_SELECTOR, 'div#ct > div.media_end_head.go_trans > div.media_end_head_title > h2')
            title = title_element.text.strip()
        except:
            title = "No Title Found"

        # 본문 크롤링
        try:
            content_element = driver.find_element(By.CSS_SELECTOR, 'div#dic_area')  # 기본 본문 태그
            content = content_element.text.strip()
        except:
            content = "No Content Found"

        return {
            'title': clean_text(title),
            'content': clean_text(content)
        }
    except Exception as e:
        print(f"Error during Selenium crawling: {e}")
        return None
    finally:
        # WebDriver 종료
        driver.quit()

# 뉴스 데이터 수집 및 저장 함수
def collect_relevant_stock_news_kr_with_selenium():
    json_file = 'stock_news.json'  # JSON 파일 이름
    articles = set()  # 중복 확인을 위한 링크 저장

    # JSON 파일 초기화
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            articles.update([article['link'] for article in existing_data])
    else:
        existing_data = []

    # 기존 데이터의 마지막 번호 계산
    start_index = len(existing_data) + 1

    for keyword in stock_prediction_keywords_kr:
        print(f"Processing keyword: {keyword}")
        news_result = get_naver_news(keyword, start=1, display=10, sort='sim')

        if not news_result.get('items'):
            print(f"No articles found for keyword: {keyword}")
            continue

        for item in news_result.get('items', []):
            link = item['link']
            if link in articles:
                print(f"Skipping duplicate article: {link}")
                continue

            article_data = get_article_content_dynamic(link)
            if not article_data or article_data['content'] == "No Content Found":
                print(f"Failed to crawl content for link: {link}")
                continue

            new_article = {
                'id': start_index,  # 뉴스 번호 추가
                'keyword': keyword,
                'title': article_data['title'],
                'content': article_data['content'],
                'link': link,
                'description': clean_text(item['description']),
                'pub_date': item['pubDate']
            }

            # 순서 번호 증가
            start_index += 1

            # 실시간으로 파일 업데이트
            existing_data.append(new_article)
            articles.add(link)  # 중복 확인을 위해 링크 저장
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

            print(f"Saved article: {new_article['title']} with ID: {new_article['id']}")

# 실행
collect_relevant_stock_news_kr_with_selenium()


