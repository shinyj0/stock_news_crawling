import os
import sys
import urllib.request
import datetime
import time
import json
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 네이버 API의 client_id와 client_secret을 환경 변수에서 가져옴
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# 네이버 API 요청 함수 [CODE 1]
def getRequestUrl(url):
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)

    try:
        response = urllib.request.urlopen(req)
        if response.getcode() == 200:
            print("[%s] Url Request Success" % datetime.datetime.now())
            return response.read().decode('utf-8')
    except Exception as e:
        print(e)
        print("[%s] Error for URL : %s" % (datetime.datetime.now(), url))
        return None

# 네이버 검색 API 호출 [CODE 2]
def getNaverSearch(node, srcText, start, display):
    base = "https://openapi.naver.com/v1/search"
    node = "/%s.json" % node
    parameters = "?query=%s&start=%s&display=%s" % (urllib.parse.quote(srcText), start, display)

    url = base + node + parameters
    responseDecode = getRequestUrl(url)  # [CODE 1]

    if responseDecode is None:
        return None
    else:
        return json.loads(responseDecode)

# 검색된 게시글 정보 가져오기 [CODE 3]
def getPostData(post, jsonResult, cnt):
    title = post['title']
    description = post['description']
    org_link = post['originallink']
    link = post['link']

    pDate = datetime.datetime.strptime(post['pubDate'], '%a, %d %b %Y %H:%M:%S +0900')
    pDate = pDate.strftime('%Y-%m-%d %H:%M:%S')

    jsonResult.append({'cnt': cnt, 'title': title, 'description': description,
                       'org_link': org_link, 'link': org_link, 'pDate': pDate})
    return

# 메인 함수 [CODE 0]
def main():
    node = 'news'  # 검색 대상 설정
    srcText = input('검색어를 입력하세요: ')
    cnt = 0
    jsonResult = []

    jsonResponse = getNaverSearch(node, srcText, 1, 100)  # [CODE 2]
    total = jsonResponse['total']

    while jsonResponse is not None and jsonResponse['display'] != 0:
        for post in jsonResponse['items']:
            cnt += 1
            getPostData(post, jsonResult, cnt)  # [CODE 3]

        start = jsonResponse['start'] + jsonResponse['display']
        jsonResponse = getNaverSearch(node, srcText, start, 100)  # [CODE 2]

    print('전체 검색 결과: %d 건' % total)

    # 전체 기사 100개 출력
    for article in jsonResult[:100]:
        print("\n기사 번호:", article['cnt'])
        print("제목:", article['title'])
        print("요약:", article['description'])
        print("원본 링크:", article['org_link'])
        print("출판 날짜:", article['pDate'])

    # JSON 파일 저장
    with open('%s_naver_%s.json' % (srcText, node), 'w', encoding='utf8') as outfile:
        jsonFile = json.dumps(jsonResult, indent=4, sort_keys=True, ensure_ascii=False)
        outfile.write(jsonFile)

    print("가져온 데이터: %d 건" % cnt)
    print('%s_naver_%s.json 저장 완료' % (srcText, node))


if __name__ == '__main__':
    main()
