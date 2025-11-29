import requests

class ODsayClient:
    def __init__(self, api_key):
        # [핵심 수정] 여기서 인코딩하지 않고 원본 키 그대로 저장
        self.api_key = api_key
        self.base_url = "https://api.odsay.com/v1/api"

    def search_path(self, sx, sy, ex, ey):
        """
        대중교통 경로 탐색 (버스/지하철)
        """
        # URL 대소문자 주의 (소문자 s)
        url = f"{self.base_url}/searchPubTransPathT"
        
        # 파라미터 딕셔너리 생성
        params = {
            "SX": sx, "SY": sy,
            "EX": ex, "EY": ey,
            "apiKey": self.api_key, # 원본 키 전달 (라이브러리가 알아서 인코딩함)
            "OPT": 0, 
            "SearchPathType": 0 
        }
        
        try:
            # requests.get이 params를 URL에 붙일 때 자동으로 인코딩 수행
            resp = requests.get(url, params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                if 'error' in data:
                    # 에러가 리스트로 올 경우 처리
                    error_info = data['error']
                    if isinstance(error_info, list):
                        error_info = error_info[0]
                    
                    print(f"   ⚠️ ODsay 거절: {error_info.get('message')}")
                    return None
                    
                return data.get('result', {})
            else:
                print(f"   ⚠️ ODsay API 호출 실패 (HTTP {resp.status_code})")
                return None
        except Exception as e:
            print(f"   ⚠️ ODsay 연결 오류: {e}")
            return None