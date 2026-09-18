원작: [miumi](https://github.com/miumida/naver_weather)

v2.5.3-0.3

# 네이버 날씨 for HA

![HAKC)][hakc-shield]
![HACS][hacs-shield]
![Version v2.5.3][version-shield]

<a href="https://www.buymeacoffee.com/miumida" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/white_img.png" alt="Buy Me A Coffee"></a>

네이버 날씨 for Home Assistant 입니다.<br>
네이버 날씨 웹페이지를 크롤링하여 센서로 추가해 줍니다.<br>
아무래도 크롤링을 해서 가져오는 부분이라 센서에서 호출하는 부분은 최소화할 수 있도록 했습니다.<br>

통합구성요소를 지원하며, 통합구성요소를 통해 추가시 기기 1개와 구성요소 32개(센서 31개와 날씨 엔티티 1개)가 추가됩니다.<br>
여러지역의 네이버 날씨를 지원합니다. 한군데 이상의 지역으로 등록 가능하지만 너무 많은 지역으로 등록은 삼가해주세요.<br>
10분 간격으로 네이버 날씨정보를 갱신합니다. 10분이면 충분하니 간격을 더 줄이는건 참아주세요!<br>

- senseor
![screenshot_1](https://github.com/miumida/naver_weather/blob/master/images/naver_weather.png?raw=true)<br>
![screenshot_2](https://github.com/miumida/naver_weather/blob/master/images/naver_weather_all.png?raw=true)<br>
- weather
![screenshot_3](https://github.com/miumida/naver_weather/blob/master/images/weather.naverweather.png?raw=true)<br>

<br>

## 버전 기록
| Version | Date        | 내용              |
| :-----: | :---------: | --------------------------------------------------------------------------------------- |
| v1.0.0  | 2020.05.07  | First version  |
| v1.0.1  | 2020.05.08  | - 미세먼지/초미세먼지/오존/자외선 가져오기 수정<br>- 미세먼지등급/초미세먼지등급/오존등급 추가 |
| v1.0.2  | 2020.05.09  | - 자외선 가져오기 오류수정<br>- 시간당 강수량 가져오기 추가<br>- 오타수정 |
| v1.0.3  | 2020.05.10  | 시간당 강수량 가져오기 오류수정 |
| v1.0.4  | 2020.05.10  | 오타수정 |
| v1.0.5  | 2020.05.12  | - 풍속/풍향 추가<br>- 속성순서 수정 |
| v1.0.6  | 2020.05.12  | 현재습도 수정 |
| v1.1.0  | 2020.05.13  | weather.py 추가 |
| v1.1.1  | 2020.05.14  | 내일오전날씨/내일오후날씨 수정 |
| v1.1.2  | 2020.05.25  | SUB 지역(area_sub) 추가 |
| v1.1.3  | 2020.05.25  | 오류 수정 |
| v1.2.0  | 2020.06.18  | weathe에 sensor 통합 |
| v1.2.1  | 2020.10.14  | weathe, sensor 현재습도, 현재풍속 가져오기 수정 |
| v2.0.0  | 2021.04.12  | Renewal - 통합구성요소 적용 |
| v2.0.2  | 2021.04.13  | bug Fix |
| v2.0.3  | 2021.04.14  | bug Fix |
| v2.0.4  | 2021.04.15  | bug Fix |
| v2.0.5  | 2021.04.19  | bug Fix + 자외선등급 추가 |
| v2.0.6  | 2021.04.20  | bug Fix |
| v2.0.7  | 2021.04.26  | api_nweather.py 예외처리 |
| v2.0.8  | 2021.07.09  | api_nweather.py 예외처리 |
| v2.0.9  | 2021.07.10  | bug Fix(자외선등급 처리) |
| v2.1.0  | 2021.09.19  | 웹페이지 개편에 따른 api 수정 |
| v2.1.1  | 2021.09.19  | 로그출력 삭제 |
| v2.1.2  | 2021.09.24  | bs4 select 수정  |
| v2.1.4  | 2021.10.01  | 미세먼지 관련 오류   |
| v2.1.6  | 2021.12.15  | Fixed bug |
| v2.1.8  | 2022.05.04  | Fixed bug |
| v2.1.11  | 2022.06.22  | Fixed bug |
| v2.1.12  | 2022.06.28  | 강수확률, 시간당강수량 api 로직 수정 |
| v2.2.0 | 2022.07.07  | 현재날씨, 현재날씨정보 정리 + 현재날씨정보 출력형태 변경  |
| v2.2.1 | 2022.07.08  | Fixed bug  |
| v2.2.2 | 2022.07.18  | Fixed bug  |
| v2.2.3 | 2022.09.06  | - 자외선 등급 추가<br> - 내일오전날씨, 내일오후날씨 api 로직 수정<br> - 오늘비시작시간, 오늘내일비시작시간 api 로직 수정  |
| v2.2.4 | 2022.09.23  | 미세먼지, 초미세먼지 device_class(pm25) 추가  |
| v2.2.5 | 2022.12.29  | 주간예보에 오늘날씨 포함 옵션   |
| v2.2.6 | 2023.04.14  | 풍속 정규식 처리    |
| v2.2.7 | 2023.07.28  | DeviceEntryType -> entry_type   |
| v2.2.8 | 2023.07.29  | DeviceEntryType 원복  |
| v2.3.0 | 2023.10.12  | WeatherEntity 업데이트 대응 |
| v2.3.3 | 2024.02.27  | DeprecatedConstant 업데이트 대응, FORECAST_TWICE_DAILY 적용 |
| v2.4.1 | 2024.03.25  | FORECAST_DAILY 지원 |
| v2.5.1 | 2024.11.06  | api_nweather.py 수정 |
| v2.5.3 | 2025.03.22  | 네이버 미세먼지 페이지 변경 대응 |
<br>

## 설치
### _My Home Assistant_ HACS로 설치
- 아래 링크를 클릭해서 이동 후 다운로드 버튼을 눌러 설치하세요.<br>
- 다운로드 후 Home Assistant를 재시작합니다.<br>
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ninthsword&repository=naver_weather&category=integration)
### 수동 설치
- HA 설치 경로 아래 custom_components에 naver_weather_custom폴더 안의 전체 파일을 복사해줍니다.<br>
  `<config directory>/custom_components/naver_weather_custom/`<br>
- configuration.yaml 파일에 설정을 추가합니다.<br>
- Home-Assistant 를 재시작합니다<br>
### HACS
- HACS > Integretions > 우측상단 메뉴 > Custom repositories 선택
- 'https://github.com/ninthsword/naver_weather' 주소 입력, Category에 'integration' 선택 후, 저장
- HACS > Integretions 메뉴 선택 후, naver_weather 검색하여 설치

### 커스텀 도메인 공존

이 포크는 의도적으로 `custom_components/naver_weather_custom/` 경로에 설치되며,
`naver_weather_custom` 통합구성요소 도메인을 사용합니다. 이를 통해 파일이나 엔티티
식별자를 공유하지 않고도 upstream `naver_weather` 통합구성요소와 공존할 수 있습니다.

설정된 하나의 지역(area)에 속한 모든 엔티티는 10분 주기의 coordinator 갱신을
공유합니다. 갱신에 실패하면 오래된 날씨 데이터를 최신인 것처럼 표시하는 대신
엔티티를 사용 불가(unavailable) 상태로 표시합니다. 현재날씨/대기질 요청은 하나의
all-or-nothing(전부 성공 또는 전부 실패) 갱신 작업으로 유지됩니다.

일별, 시간별, 예보 발표 타임스탬프는 네이버가 표시하는 라벨을 기준으로 한국표준시
(KST)로 해석하며, 12월/1월 연도 전환(rollover)도 처리합니다. 기존 `today` 옵션은
일별 및 하루 두 번(twice-daily) 예보 표시에만 영향을 주며, 활성화하면 현재 KST
날짜를 포함하고 기본값(비활성화)에서는 그 날짜만 제외합니다. 시간별 행은 네이버가
표시하는 타임스탬프 `T`를 그대로 유지합니다. 해당 행의 날씨상태와 강수량 값은 직전
구간 `(T-1h,T]`을 나타내며, 기온·풍속·습도는 정확히 `T` 시점 행에 맞춰집니다.
선택적 배열이 짧거나 없더라도 그 자체로 유효한 다른 행을 버리지 않습니다. 풍속은
원본 단위인 m/s로 유지되며, 현재/시간별/주간 발표시간은 ISO-8601 KST 값
(`publicTimeC`, `publicTimeH`, `publicTimeW`)으로 노출됩니다. 예보 데이터는 Home
Assistant의 기본 기온·풍속·강수량 필드를 사용하며, HA 예보 경계(boundary)에서는
UTC RFC-3339 형식의 날짜/시간 문자열로 출력됩니다.

<br>

## 사용법
### 커스텀 통합구성요소
- 구성 > 통합구성요소 > 통합구성요소 추가하기 > 네이버 날씨 선택 > 지역(area) 입력후, 확인.

<br>

### 기본 설정값

|옵션|내용|sensor|weather|
|--|--|--|--|
|platform| (필수) naver_weather  |O|O|
|area| (옵션) 원하는 동네 / default(날씨) |O|O|
|today| (옵션) 주간예보에 오늘날씨를 포함||O|
<br>

### area 설정값
area는 기본값으로 '날씨'로 들어갑니다.<br>
기본적으로 날씨로 지정되면 장비가 있는 위치를 기준으로 날씨가 나오는거 같았습니다.<br>
추가로 area에 원하시는 지역을 네이버에서 검색하셔서 입력해보시고 날씨가 조회되면 area에 입력하시면 됩니다.<br>
물론 네이버에 정상적으로 검색되는지 확인이 필요합니다.<br>
창원시 대방동 날씨로 검색했을 때, 정상적으로 날씨정보가 조회된다면 '창원시 대방동'으로 area를 입력하시면 됩니다.<br>
![screenshot_3](https://github.com/miumida/naver_weather/blob/master/images/naver_weather_search.png?raw=true)<br>

<br>

### 네이버 날씨 제공정보
|정보| 비고 |
|-------|-------|
|위치| |
|체감온도       | |
|현재온도       | |
|현재습도       | |
|현재풍속       | |
|현재풍향       | |
|최고온도       | |
|최저온도       | |
|내일최고온도     | |
|내일최저온도     | |
|~~자외선지수~~      | |
|자외선등급      | |
|강수확률 | 기상청에서 제공되는 강수확률에 문제가 있는 것으로 보임.<br> 현재시간 기준의 강수확률은 거의 표시되지 않음. |
|시간당강수량     | |
|오늘비시작시간   | |
|오늘내일비시작시간 | |
|현재날씨       | |
|현재날씨정보    | |
|현재 및 1시간예보 발표시간 | ISO-8601 KST |
|시간별예보 발표시간 | ISO-8601 KST |
|주간예보 발표시간 | ISO-8601 KST |
|내일오전날씨     | |
|내일오후날씨     | |


### 네이버 대기질 제공정보
|정보| 비고 |
|-------|-------|
|미세먼지       | |
|미세먼지등급     | |
|초미세먼지      | |
|초미세먼지등급   | |


### 네이버 오염물질 제공정보
|정보| 비고 |
|-------|-------|
|오존       |등급 |
|일산화탄소       |등급|
|아황산가스       |등급|
|이산화질소       |등급|
|통합대기       |등급|
<br>

#### 감사의 말
- 네이버 HomeAssistant 카페 | 랜이님
- 네이버 HomeAssistant 카페 | 초후님
- 네이버 HomeAssistant 카페 | mahlernim님
- 네이버 HomeAssistant 카페 | 트루월드님
- 네이버 HomeAssistant 카페 | af950833님

<br>

## 참고사이트
[1] 네이버 HomeAssistant 카페 | af950833님의 [HA] 네이버 날씨 (<https://cafe.naver.com/stsmarthome/19337>)<br>

[version-shield]: https://img.shields.io/badge/version-v2.5.3-orange.svg
[hakc-shield]: https://img.shields.io/badge/HAKC-Enjoy-blue.svg
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-red.svg

## 개발 확인

개발 환경은 Python 3.14.7, uv 0.12.5, Node.js 24를 사용합니다. 해시로 잠긴
(hash-locked) 의존성에는 Home Assistant 2026.8.0, Beautiful Soup 4.12.3, Ruff
0.16.4가 포함됩니다. Pyright 1.1.413은 `devtools/pyright` 아래에 격리되어 있으며,
통합구성요소의 Python 3.11 문법 호환성은 그대로 유지됩니다. 런타임과 개발용
Beautiful Soup 버전 고정은 Home Assistant의 공유 Python 환경에서의 호환성을 위해
4.12.3으로 동일하게 맞춰져 있습니다.

```sh
python3 -m pip install uv==0.12.5
uv venv --python 3.14.7 .venv
uv pip sync --python .venv/bin/python --require-hashes requirements-dev.lock
npm ci --prefix devtools/pyright --ignore-scripts --no-audit --no-fund
devtools/pyright/node_modules/.bin/pyright --project pyrightconfig.json --pythonpath .venv/bin/python --outputjson
.venv/bin/ruff check --no-cache custom_components tests tests_ha
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m unittest discover -s tests_ha -p test_options_flow.py -v
.venv/bin/python -B -m unittest discover -s tests_ha -p test_parser_dependency.py -v
```

Pyright는 9개의 통합구성요소 모듈과 두 개의 경량 테스트 모듈, 그리고 실제 Home
Assistant를 사용하는 두 회귀(regression) 테스트 모듈을 모두 검사합니다. 두 테스트
디렉터리는 서로 다른 프로세스에서 실행하세요: `tests`는 경량 모듈 shim을 설치해
사용하고, `tests_ha`는 실행 중인 인스턴스나 네트워크 없이 합성(synthetic) 데이터로
실제 Home Assistant 클래스를 사용합니다. 실제 클래스 기반 회귀 테스트는 HA의
getter 전용 `OptionsFlow.config_entry`, 옵션 우선순위, 기존 기본값과 제출된 값에
대한 동작을 보호합니다. 별도 서브프로세스로 실행되는 파서 테스트는 실제 Home
Assistant와 Beautiful Soup 패키지를 임포트해 합성 HTML, 활성 패널 CSS 선택,
시간별 롤오버, 선택적 값, 발표 메타데이터를 검증합니다. 이 기대값들은 사용 중인
파서 버전과 무관하게 성립합니다.

개발 의존성을 의도적으로 변경할 때는 `requirements-dev.in`과 해시로 검증되는
`requirements-dev.lock`을 항상 함께 갱신하세요. 이 개발 확인 과정은 Home
Assistant에 통합구성요소를 설치하거나 어떤 서비스·장치도 실제로 동작시키지
않습니다.


## Home Assistant 2026.9 호환성 검증

기존 2026.8 최소 버전 검증은 유지합니다. 2026.9.2 검증은 Python 3.14.7과
별도 해시 잠금 파일을 사용하며, 실제 서비스나 장치에 연결하지 않습니다.
`uv==0.12.5`, Node.js 24와 저장소의 잠긴 Pyright 의존성을 사용합니다.

```sh
uv venv --python 3.14.7 .venv-ha2026.9
uv pip sync --python .venv-ha2026.9/bin/python --require-hashes requirements-ha2026.9.lock
npm ci --prefix devtools/pyright --ignore-scripts --no-audit --no-fund
.venv-ha2026.9/bin/python -B -m unittest discover -s tests -v
.venv-ha2026.9/bin/python -B -m unittest discover -s tests_ha -p test_options_flow.py -v
.venv-ha2026.9/bin/python -B -m unittest discover -s tests_ha -p test_parser_dependency.py -v
.venv-ha2026.9/bin/python -B -m pytest -p no:cacheprovider --disable-socket --allow-unix-socket -o asyncio_mode=auto tests_ha/test_setup_lifecycle.py
```

가벼운 기존 테스트와 실제 Home Assistant pytest 테스트는 별도 프로세스에서
실행합니다. 새 pytest 파일은 2026.9 작업에서 명시적으로 타입 검사하며,
기존 2026.8 환경에 pytest 플러그인을 추가하지 않습니다.
