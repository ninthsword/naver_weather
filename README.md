원작: [miumi](https://github.com/miumida/naver_weather)

v2.5.3-0.10

# 네이버 날씨 for HA

![HAKC)][hakc-shield]
![HACS][hacs-shield]
![Version v2.5.3][version-shield]

<a href="https://www.buymeacoffee.com/miumida" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/white_img.png" alt="Buy Me A Coffee"></a>

네이버 날씨 for Home Assistant 입니다.<br>
네이버 날씨 웹페이지를 크롤링하여 센서로 추가해 줍니다.<br>
아무래도 크롤링을 해서 가져오는 부분이라 센서에서 호출하는 부분은 최소화할 수 있도록 했습니다.<br>

통합구성요소를 지원하며, 통합구성요소를 통해 추가시 기기 1개와 구성요소 34개(센서 33개와 날씨 엔티티 1개)가 추가됩니다.<br>
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

통합구성요소는 한 번에 한 지역의 날씨와 대기질을 갱신합니다. Home Assistant 시작 후
또는 항목을 추가하거나 다시 불러오거나 설정을 재시도한 후의 첫 갱신은 진행 중인 지역
갱신이 끝나면 바로 시작합니다. 이후의 갱신은 어느 지역이든 직전 갱신이 끝난 시점부터
최소 30초가 지난 뒤 시작하므로, 여러 지역을 설정하면 10분 갱신 주기가 대기 시간만큼
길어질 수 있습니다.

### 현재 위치 날씨

Home Assistant Companion 앱에서 지오코딩된 위치 센서를 활성화한 뒤, 네이버 날씨
통합구성요소를 새로 추가하고 **위치 센서**에서 해당 센서를 선택하세요. 센서에는
시·도 이름인 `Locality` 속성이 있어야 하며, 동 이름은 `Sub Locality` 속성에서
읽습니다. 이때 같은 화면의 지역 입력은 무시되며 **현재 위치** 항목이 별도로
생성됩니다. 기존 고정 지역 항목과 함께 사용할 수 있습니다.

10분마다 위치 센서의 속성으로 `<Locality> <Sub Locality> 날씨`를 검색합니다.
동 정보가 없으면 시·도 날씨를 검색하고, 시·도 정보까지 사라지면 이 실행 중 마지막으로
확인한 지역을 유지합니다. 처음부터 시·도 정보가 없으면 새 요청을 보내지 못하며,
최근 저장된 날씨가 없는 경우 설정을 재시도합니다. 이동해도 엔티티 ID와 고유 ID는
바뀌지 않습니다. 선택한 위치의 시·도와 동 이름은 날씨 조회를 위해 네이버에 전송됩니다.
현재 위치 항목은 고정 지역 항목과 동일하게 자체적으로 10분마다 갱신합니다.

### 시간별·일별 예보 센서

각 항목에는 **시간별 예보**와 **일별 예보** 센서가 추가됩니다. 센서 상태는 첫 예보의
날씨 상태이며, `forecast` 속성에는 같은 날씨 엔티티에 대한 `weather.get_forecasts`의
시간별 또는 일별 응답과 동일한 전체 예보 목록이 들어 있습니다. 기온·강수량·풍속은
날씨 엔티티에 설정된 단위와 정밀도를 따르며, `today` 옵션은 일별 목록에도 적용됩니다.
이 센서들은 추가 요청을 보내지 않고, `forecast` 속성은 기록기에 저장하지 않습니다.
날씨 엔티티가 비활성화되거나 제거되면 예보 목록은 빈 목록이 됩니다.

첫 예보는 다음과 같이 읽을 수 있습니다. 아래의 `sensor.<시간별 예보 센서>`와
`sensor.<일별 예보 센서>`는 자리 표시자이므로 실제 엔티티 ID로 바꿔야 합니다. 실제
엔티티 ID는 Home Assistant가 생성하며(예: `sensor.naver_weather_custom_<지역>_siganbyeol_yebo`),
개발자 도구 또는 엔티티 목록에서 이름 '시간별 예보'와 '일별 예보'로 찾을 수 있습니다.
예보가 비어 있을 때는 `[0]`을 읽기 전에 목록을 확인해야 합니다.

```jinja2
{% if state_attr('sensor.<시간별 예보 센서>', 'forecast') %}
  {{ state_attr('sensor.<시간별 예보 센서>', 'forecast')[0] }}
{% endif %}
{% if state_attr('sensor.<일별 예보 센서>', 'forecast') %}
  {{ state_attr('sensor.<일별 예보 센서>', 'forecast')[0] }}
{% endif %}
```

기존 대시보드와 템플릿 YAML은 자동으로 변경되지 않습니다.

### 날씨 카드

대시보드를 편집하고 **카드 추가**에서 **네이버 날씨 카드**를 검색하세요.
**날씨 엔티티**에서 현재 위치와 고정 지역 항목을 함께 선택할 수 있습니다. 카드는
통합구성요소가 갱신될 때 새 예보를 받습니다. 처음 통합구성요소를 추가할 때 브라우저가
이미 열려 있었거나 버전을 올린 뒤 카드가 보이지 않으면 앱이나 페이지를 한 번 새로고침하세요.

| 옵션 | 화면의 이름과 설정 | 기본값 |
| --- | --- | --- |
| `entities` | **날씨 엔티티**. 표시할 네이버 날씨 엔티티를 하나 이상 선택합니다. | 카드 추가 시 표시 가능한 엔티티 중 ID 순으로 첫 번째 |
| `mode` | **표시 방식**. 시간별(`hourly`), 일별(`daily`), 시간별+일별(`both`) 중 선택합니다. | 시간별+일별 |
| `show_current` | **현재 날씨 표시**. 현재 날씨를 예보 위에 표시합니다. | 켜짐 |
| `hours` | **시간별 개수**. 1~24개 중 선택합니다. | 18개 |
| `days` | **일별 일수**. 1~10일 중 선택합니다. | 10일 |
| `switcher` | **지역 전환**. 슬라이드(`swipe`) 또는 버튼(`buttons`)으로 지역을 바꿉니다. | 슬라이드 |
| `remember` | **마지막 지역 기억**. 브라우저에 마지막으로 선택한 지역을 저장합니다. | 켜짐 |
| `icon_path` | **아이콘 폴더**. 같은 Home Assistant 서버의 폴더 경로를 지정합니다. | 비워 둠 (Home Assistant 아이콘) |

슬라이드를 선택하면 현재 날씨 영역을 좌우로 밀어 지역을 전환합니다. 현재 날씨를
숨겼다면 지역 이름 줄을 밀면 됩니다. 시간별·일별 예보 영역 안에서 밀면 해당
예보의 페이지만 바뀝니다.

직접 준비한 아이콘을 쓰려면 `/local/icons/naver_weather`처럼 `/`로 시작하는 같은
서버의 경로를 입력하고 파일 이름을 `icon_flat_<wtN>.svg` 형식으로 맞추세요.
예를 들어 `wt1`에 해당하는 파일은 `icon_flat_wt1.svg`입니다. 통합구성요소에는
네이버 이미지가 포함되어 있지 않습니다.

YAML에서 `workday_entities`에 Workday 통합구성요소의 이진 센서를 오늘부터 날짜
오프셋 순서대로 넣으면, 해당 날짜의 센서가 `off`일 때 요일 이름이 붉게 표시됩니다.
기본값은 토·일요일을 붉게 표시합니다. `users`에는 사용자 이름별 시작 날씨 엔티티를
지정할 수 있습니다. 마지막 지역을 기억한 경우에는 그 지역을 먼저 열고, 기억한
지역과 사용자별 지정이 모두 없으면 목록의 첫 번째 지역을 엽니다. 아래 엔티티 ID와
사용자 이름은 실제 값으로 바꾸세요.

```yaml
type: custom:naver-weather-card
entities:
  - weather.example_first
  - weather.example_second
users:
  "사용자 이름": weather.example_second
workday_entities:
  - binary_sensor.example_workday_today
  - binary_sensor.example_workday_tomorrow
```

### 브라우저 서비스 (선택 사항)

네이버가 직접 요청에 403을 반환하는 환경에서는 브라우저 서비스를 사용할 수
있습니다. 이 서비스는 Chromium으로 네이버 검색 페이지를 열어 HTML을 전달합니다.
Home Assistant와 별도로 Docker를 사용할 수 있는 서버에서 실행하세요.

저장소의 `browser_service` 디렉터리에서 다음 명령으로 빌드하고 시작합니다.

```sh
cd browser_service
docker compose up -d --build
```

Home Assistant의 네이버 날씨 통합구성요소 옵션에서 **브라우저 서비스 주소**에
`http://<server>:8765`를 입력하세요. `<server>`는 Home Assistant에서 접근할 수 있는
서버 주소로 바꾸고, `/render` 경로는 붙이지 않습니다. 날씨와 대기질 페이지를 모두
이 서비스로 요청하며, 서비스 오류나 시간 초과가 발생한 페이지는 직접 요청으로
다시 시도합니다. 주소를 비워 저장하면 직접 요청을 사용합니다. 옵션 변경은 다음
갱신부터 적용됩니다.

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
devtools/pyright/node_modules/.bin/pyright --project pyrightconfig.json --pythonpath .venv-ha2026.9/bin/python tests_ha/conftest.py tests_ha/test_setup_lifecycle.py tests_ha/test_card_frontend.py tests_ha/test_fetch_gap.py
.venv-ha2026.9/bin/python -B -m unittest discover -s tests -v
.venv-ha2026.9/bin/python -B -m unittest discover -s tests_ha -p test_options_flow.py -v
.venv-ha2026.9/bin/python -B -m unittest discover -s tests_ha -p test_parser_dependency.py -v
.venv-ha2026.9/bin/python -B -m pytest -p no:cacheprovider --disable-socket --allow-unix-socket -o asyncio_mode=auto tests_ha/test_setup_lifecycle.py tests_ha/test_card_frontend.py tests_ha/test_fetch_gap.py
```

가벼운 기존 테스트와 실제 Home Assistant pytest 테스트는 별도 프로세스에서
실행합니다. 새 pytest 파일은 2026.9 작업에서 명시적으로 타입 검사하며,
기존 2026.8 환경에 pytest 플러그인을 추가하지 않습니다.

## Home Assistant 2026.10 호환성 검증

기존 검증 환경과 별도로 안정판 Home Assistant 2026.10.0, Python 3.14.7,
`uv==0.12.5`, Node.js 24를 사용합니다. 새 의존성 입력과 해시 잠금 파일은
`requirements-ha2026.10.in`, `requirements-ha2026.10.lock`입니다.

테스트 플러그인 `pytest-homeassistant-custom-component==0.13.370`의 메타데이터는
`homeassistant==2026.10.0b4`를 요구하므로, 단일 코어 버전만 지정한
`requirements-ha2026.10-overrides.in`으로 안정판을 선택합니다. CI는 설치된
Python·코어·플러그인 버전을 확인하고 전체 의존성 메타데이터를 검사합니다.
플러그인의 이 베타 버전 요구와 설치된 안정판 사이의 불일치가 정확히 하나일
때만 허용하며, 누락된 의존성이나 다른 버전 불일치는 실패로 처리합니다.

의존성 입력을 변경할 때는 같은 도구와 재정의 파일로 잠금을 다시 생성하세요.

```sh
uv pip compile --python 3.14.7 --generate-hashes --override requirements-ha2026.10-overrides.in requirements-ha2026.10.in -o requirements-ha2026.10.lock
```

전용 환경에서 `devtools/ha2026_10_typing.py`를 먼저 실행하세요. HA의 런타임
재노출과 Probatio 별칭을 타입 검사기가 인식하도록, 설치된 소스에서 `.pyi`
파일 네 개를 생성합니다. 원본 런타임 `.py`와 배포 메타데이터는 해시로
보호하며, 코어·플러그인·Probatio 버전과 실제 객체의 동일성도 확인합니다.
다른 가상환경, 예상과 다른 import 구조나 기존 타입 파일은 실패로 처리합니다.
동일한 생성 결과가 이미 있으면 다시 쓰지 않습니다. 이어지는 가드 테스트는
임시 파일과 새 프로세스로 실패 조건을 검사합니다. 이 준비는 2026.10 환경에만
적용되며, 기존 검증 환경과 통합구성요소의 런타임 import는 그대로 유지합니다.

다음 명령은 외부 서비스나 장치에 연결하지 않고, 기존 오프라인 테스트와 실제
Home Assistant 테스트를 별도 프로세스로 실행합니다. CI는 같은 검사에 위의
버전 및 메타데이터 검사를 추가합니다.

```sh
python -m pip install uv==0.12.5
uv venv --python 3.14.7 .venv-ha2026.10
uv pip sync --python .venv-ha2026.10/bin/python --require-hashes requirements-ha2026.10.lock
npm ci --prefix devtools/pyright --ignore-scripts --no-audit --no-fund
.venv-ha2026.10/bin/python -B devtools/ha2026_10_typing.py
.venv-ha2026.10/bin/python -B -m unittest discover -s devtools -p test_ha2026_10_typing.py -v
.venv-ha2026.10/bin/python -B -m pytest --collect-only -p no:cacheprovider --disable-socket --allow-unix-socket -o asyncio_mode=auto tests_ha/test_setup_lifecycle.py tests_ha/test_card_frontend.py tests_ha/test_fetch_gap.py
devtools/pyright/node_modules/.bin/pyright --project pyrightconfig.json --pythonpath .venv-ha2026.10/bin/python
devtools/pyright/node_modules/.bin/pyright --project pyrightconfig.json --pythonpath .venv-ha2026.10/bin/python tests_ha/conftest.py tests_ha/test_setup_lifecycle.py tests_ha/test_card_frontend.py tests_ha/test_fetch_gap.py
.venv-ha2026.10/bin/python -B -m unittest discover -s tests -v
.venv-ha2026.10/bin/python -B -m unittest discover -s tests_ha -p test_options_flow.py -v
.venv-ha2026.10/bin/python -B -m unittest discover -s tests_ha -p test_parser_dependency.py -v
.venv-ha2026.10/bin/python -B -m pytest -p no:cacheprovider --disable-socket --allow-unix-socket -o asyncio_mode=auto tests_ha/test_setup_lifecycle.py tests_ha/test_card_frontend.py tests_ha/test_fetch_gap.py
.venv-ha2026.10/bin/ruff check --no-cache custom_components tests tests_ha
devtools/pyright/node_modules/.bin/pyright --project pyrightconfig.json --pythonpath .venv-ha2026.10/bin/python devtools/ha2026_10_typing.py devtools/test_ha2026_10_typing.py
.venv-ha2026.10/bin/ruff check --no-cache devtools/ha2026_10_typing.py devtools/test_ha2026_10_typing.py
```

## 화면 검증

`devtools/ui_check/check.py`는 실제 Home Assistant 2026.10을 Home Assistant 자체
화면 그대로, 네이버 날씨 대신 합성 날씨 데이터로 실행합니다. 브라우저로 로그인한 뒤
구성 흐름으로 통합구성요소를 추가하고, 한국어 문구와 기기 및 센서, 옵션 화면을
확인하며, 기기 페이지를 데스크톱과 휴대폰 너비로 열어 각 화면의 스크린샷을
저장합니다.

합성 지역을 하나 더 추가하고 카드 선택기와 편집기에서 네이버 날씨 카드를 저장합니다.
1440px와 390px에서 현재 날씨, 시간별 및 일별 예보, 두 종류의 지역 전환, 시간별
예보 페이지 전환을 확인합니다. 두 너비에서 전환 전후 카드와 일별 예보를 저장하며,
휴대폰 환경에서 터치로 지역을 전환하고 현재습도 칩의 상세 화면도 확인합니다.

이 검증은 네이버, 운영 중인 Home Assistant, 장치에 연결하지 않으며 네트워크가
필요하지 않습니다. 다만 네트워크가 있으면 새로 설치한 Home Assistant와 마찬가지로
온보딩 과정에서 기본 통합구성요소인 met, radio_browser, google_translate가 시작되고
브라우저가 Home Assistant의 브랜드 이미지를 불러오므로 인터넷에 접속할 수 있습니다.

`requirements-ui.lock`으로 `.venv-ui`를 만들고 Chromium을 설치한 뒤, 실행할 때마다
`mktemp -d`로 새 디렉터리를 만들어 지정하세요. 이미 파일이 있는 디렉터리는 거부되므로
고정된 경로는 두 번째 실행에서 실패합니다. 스크린샷과 Home Assistant 로그가 그
디렉터리 아래에 저장됩니다.

```sh
python -m pip install uv==0.12.5
uv venv --python 3.14.7 .venv-ui
uv pip sync --python .venv-ui/bin/python --require-hashes requirements-ui.lock
.venv-ui/bin/python -m playwright install --with-deps chromium
out=$(mktemp -d /tmp/naver-ui-check.XXXXXX)
.venv-ui/bin/python -B devtools/ui_check/check.py --out "$out/shots"
```

CI는 `.github/workflows/ui-check.yml`에서 같은 검증을 실행하고, 스크린샷과 로그를
7일 동안 보관합니다.

## 개발용 동작 지도

[핵심 동작 지도](docs/behavior-map.md)에서 기능별 코드·테스트와 확인 범위를 찾을 수 있습니다.
지도는 배포 상태나 실제 장치·서비스의 정상 동작을 보장하지 않습니다.
