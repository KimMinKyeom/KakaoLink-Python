# KakaoLink-Python

> **⚠️ 주의:** 카카오톡 2차 인증 이슈 때문에 작동이 안 됩니다.

파이썬 버전 카카오링크

## Key Features
+ 카카오링크 전송

## Quick Example
```py
from kaling import Kakao

KakaoLink = KakaoAPI('JS KEY', 'URL')
KakaoLink.login('ID', 'PW')
KakaoLink.send("ROOM", {
    "link_ver": "4.0",
    "template_object": {
        "object_type": "text",
        "button_title": "BUTTON TEXT",
        "text": "TEXT",
        "link": {"mobileWebUrl": 'URL', "webUrl": 'URL'}
    }
})
```
## Credit
+ https://github.com/cjh980402/kakao-link
+ https://github.com/ksaidev/KakaoLink-Python
