import requests

class WeatherAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, lat, lon):
        if not self.api_key: # 키 없으면 기본값
            return {'temp': 20.0, 'humidity': 50, 'condition': 'Unknown', 'is_wet': False}

        try:
            params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
            resp = requests.get(self.url, params=params, timeout=3)
            if resp.status_code == 200:
                d = resp.json()
                cond = d['weather'][0]['main']
                is_wet = cond in ['Rain', 'Snow', 'Drizzle', 'Thunderstorm']
                return {
                    'temp': d['main']['temp'],
                    'humidity': d['main']['humidity'],
                    'condition': cond,
                    'is_wet': is_wet
                }
        except:
            pass
        return {'temp': 20.0, 'humidity': 50, 'condition': 'Error', 'is_wet': False}