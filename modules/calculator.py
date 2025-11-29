import math

class CarbonCalculator:
    def __init__(self):
        self.emission_map = {
            0: 0.20, 1: 0.75, 
            2: 1.40, 3: 2.10, 4: 2.90, 5: 3.80,
            6: 4.80, 7: 5.90, 8: 7.10, 9: 8.40, 10: 9.80,
            11: 11.50, 12: 13.50, 13: 16.00, 14: 19.50, 15: 25.00
        }

    def get_weather_factors(self, weather_data):
        temp_c = weather_data.get('temp', 20.0)
        humidity = weather_data.get('humidity', 50.0)
        is_wet = weather_data.get('is_wet', False)

        k_air = (273.15 + 20) / (273.15 + temp_c)
        rolling_coeff = 0.018 if is_wet else 0.015

        aux_kw_ton = 0.0
        if temp_c > 24:
            base_ac_load = (temp_c - 24) * 0.05
            if humidity > 60:
                humid_factor = 1 + ((humidity - 60) * 0.01) 
                base_ac_load *= humid_factor
            aux_kw_ton += min(base_ac_load, 1.5)
        elif is_wet or humidity > 90:
            aux_kw_ton += 0.2 
        elif temp_c < 10:
            aux_kw_ton += (10 - temp_c) * 0.02
        if is_wet:
            aux_kw_ton += 0.1 

        return k_air, rolling_coeff, aux_kw_ton

    def get_vsp_scientific(self, speed, accel, grade, k_air, c_r, aux, drag_term):
        v = speed / 3.6 
        grade_dec = grade / 100
        term1 = v * (1.1 * accel + 9.81 * grade_dec + c_r)
        term2 = (drag_term * k_air) * (v ** 3)
        term3 = aux
        return term1 + term2 + term3

    def get_bin(self, vsp, speed):
        if speed < 1.0: return 1
        if vsp < 0: return 0
        if vsp < 3: return 2
        if vsp < 6: return 3
        if vsp < 9: return 4
        if vsp < 12: return 5
        if vsp < 15: return 6
        if vsp < 18: return 7
        if vsp < 21: return 8
        if vsp < 24: return 9
        if vsp < 27: return 10
        if vsp < 30: return 11
        if vsp < 33: return 12
        if vsp < 39: return 13
        return 14

    def calculate(self, segments, weather_data=None, vehicle_spec=None):
        if not weather_data: weather_data = {'temp': 20.0, 'humidity': 50, 'is_wet': False}
        if not vehicle_spec: vehicle_spec = {"type": "ice", "drag_term": 0.000264, "emission_factor": 1.0}

        fuel_type = vehicle_spec.get('type', 'ice')
        k_air, c_r, aux_load_pct = self.get_weather_factors(weather_data) # aux는 여기서 사용안함(전기차 제외) logic 확인 필요, 아래에서 다시 확인
        
        # *수정: get_weather_factors는 aux_kw_ton을 반환함. 
        # 위 코드에서 aux_load_pct로 받으면 혼동이 올 수 있으나 VSP 계산엔 aux_kw_ton이 들어감.
        # 내연기관은 aux_kw_ton을 VSP에 더하고, 전기차는 전력량에 % 부하를 더하는 식으로 분기했었음.
        # 여기서는 깔끔하게 재정리.
        
        k_air, c_r, aux_val = self.get_weather_factors(weather_data)
        
        drag_term = vehicle_spec.get('drag_term', 0.000264)
        weight_kg = vehicle_spec.get('weight_kg', 1500)
        e_factor = vehicle_spec.get('emission_factor', 1.0)

        total_co2 = 0
        total_dist = 0

        for seg in segments:
            dist_m = seg['distance_m']
            speed_kph = seg['speed_kph']
            grade_pct = seg['grade_pct']
            delta_v = seg['delta_v']
            
            time_sec = dist_m / (speed_kph / 3.6) if speed_kph > 0.1 else 0
            accel = 0
            if time_sec > 0: accel = (delta_v / 3.6) / time_sec
            
            cong = seg.get('congestion', 0)
            if cong >= 3: accel += 0.15

            # VSP 계산 (aux_val은 기생 부하)
            # 전기차는 aux를 여기서 더하지 않고 전력량에서 처리
            vsp_aux = 0 if fuel_type == 'ev' else aux_val
            vsp = self.get_vsp_scientific(speed_kph, accel, grade_pct, k_air, c_r, vsp_aux, drag_term)
            
            step_co2 = 0

            if fuel_type == "ev":
                power_kw = vsp * (weight_kg / 1000)
                if power_kw > 0: energy_kwh = (power_kw * time_sec / 3600) / 0.85
                else: energy_kwh = (power_kw * time_sec / 3600) * 0.60
                
                # 전기차 보조 부하 (비율로 적용, 예: 히터 시 1.3배)
                # 간단하게 aux_val을 비율로 환산 (대략적)
                ev_aux_ratio = 1.0 + (aux_val * 0.1) 
                energy_kwh *= ev_aux_ratio
                
                step_co2 = energy_kwh * 424.0
            
            else:
                bin_idx = self.get_bin(vsp, speed_kph)
                base_emission = self.emission_map.get(bin_idx, 5.0) * time_sec
                if fuel_type == "hev":
                    if vsp < 5 and speed_kph < 40: base_emission *= 0.1
                    else: base_emission *= 0.7
                
                step_co2 = base_emission * e_factor

            total_co2 += step_co2
            total_dist += (dist_m / 1000)
            
            seg['step_emission'] = round(step_co2, 2)

        return total_co2, total_dist

    def calculate_weather_impact(self, segments, real_weather, vehicle_spec=None):
        real_co2, _ = self.calculate(segments, real_weather, vehicle_spec)
        base_weather = {'temp': 20.0, 'humidity': 50, 'is_wet': False}
        base_co2, _ = self.calculate(segments, base_weather, vehicle_spec)
        diff = real_co2 - base_co2
        pct = (diff / base_co2) * 100 if base_co2 > 0 else 0
        return real_co2, diff, pct