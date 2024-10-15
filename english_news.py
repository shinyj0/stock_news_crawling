import os
from dotenv import load_dotenv  
from newsapi import NewsApiClient
from datetime import datetime
import json

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
news_api_key = os.getenv("NEWS_API_KEY")

# API 키가 제대로 로드되었는지 확인
if not news_api_key:
    raise ValueError("API key not found. Please check your .env file.")

# Init: .env 파일에서 로드한 API 키 사용
newsapi = NewsApiClient(api_key=news_api_key)

# 오늘 날짜 구하기
today = datetime.today().strftime('%Y-%m-%d')

# 영어 기사 검색 (최신 헤드라인)
all_en_articles = newsapi.get_everything(
    q='stock OR market OR investment OR finance',
    from_param='2024-09-15',
    to=today,
    language='en',
    sort_by='relevancy',
    page=1
)

# 현재 파일 경로 가져오기
current_file_directory = os.path.dirname(os.path.abspath(__file__))

# JSON 파일을 생성할 경로 지정 (현재 파일과 동일 위치)
json_filename = os.path.join(current_file_directory, "english_news_articles.json")

# Write the data to a JSON file
with open(json_filename, mode='w', encoding='utf-8') as json_file:
    json.dump(all_en_articles, json_file, ensure_ascii=False, indent=4)

# Output confirmation
print(f"Data has been written to {json_filename}")
# 결과 확인
print(all_en_articles)