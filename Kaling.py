import requests, json, base64, re
from bs4 import BeautifulSoup
from Cryptodome import Random
from Cryptodome.Cipher import AES
from hashlib import md5
from urllib import parse


class KakaoAPI:
    def __init__(self, api_key, location):
        if not all(isinstance(item, str) for item in [api_key, location]):
            raise TypeError("매개변수의 타입은 String이어야 합니다.")
        elif len(api_key) != 32:
            raise ReferenceError("API KEY는 32자여야 합니다.")
        if not re.search(r"^https?\:\/\/.+", location):
            raise ReferenceError('도메인 주소의 형식이 올바르지 않습니다.')

        self.api_key = api_key
        self.location = location
        self.kakao_static = 'sdk/1.36.6 os/javascript lang/en-US device/Win32 origin/' + parse.quote_plus(location)
        self.cookies = {}
        self.BS = BeautifulSoup

    def _pad(self, data):
        length = 16 - (len(data) % 16)
        return data + (chr(length) * length).encode()

    def _bytes_to_key(self, data, salt, output=48):
        assert len(salt) == 8, len(salt)
        data += salt
        key = md5(data).digest()
        final_key = key
        while len(final_key) < output:
            key = md5(key + data).digest()
            final_key += key
        return final_key[:output]

    def AES_encrypt(self, message, passphrase):
        message = bytes(message, 'utf-8')
        passphrase = bytes(passphrase, 'utf-8')
        salt = Random.new().read(8)
        key_iv = self._bytes_to_key(passphrase, salt, 32 + 16)
        key = key_iv[:32]
        iv = key_iv[32:]
        aes = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(b"Salted__" + salt + aes.encrypt(self._pad(message))).decode("utf-8")

    def login(self, username, password):
        if not all(isinstance(item, str) for item in [username, password]):
            raise TypeError("아이디와 비밀번호의 타입은 String이어야 합니다.")
        if not self.api_key:
            raise ReferenceError('로그인 메서드를 카카오 SDK가 초기화되기 전에 호출하였습니다.')

        login_url = "https://accounts.kakao.com/login?continue=https%3A%2F%2Faccounts.kakao.com%2Fweblogin%2Faccount%2Finfo"
        headers = {'User-Agent': self.kakao_static, 'referer': 'https://accounts.kakao.com'}
        login_response = requests.get(login_url, headers=headers)

        if login_response.status_code == 200:
            for cookie_name in ['_kadu', '_kadub', '_maldive_oauth_webapp_session_key']:
                try:
                    self.cookies[cookie_name] = login_response.cookies[cookie_name]
                except:
                    pass

            self.referer = login_response.url
            self.crypto_key = login_response.text.split('"p":"')[1].split('"')[0]
            tiara_url = 'https://stat.tiara.kakao.com/track?d=%7B%22sdk%22%3A%7B%22type%22%3A%22WEB%22%2C%22version%22%3A%221.1.15%22%7D%7D'
            try:
                self.cookies['TIARA'] = requests.get(tiara_url).cookies['TIARA']
            except:
                pass
            payload = {
                'os': 'web',
                'webview_v': '2',
                'email': self.AES_encrypt(username, self.crypto_key),
                'password': self.AES_encrypt(password, self.crypto_key),
                'continue': parse.unquote_plus(self.referer.split('continue=')[1]),
                'third': 'false',
                'k': 'true',
            }
            auth_url = 'https://accounts.kakao.com/weblogin/authenticate.json'
            response = requests.post(auth_url, cookies=self.cookies, data=payload, headers=headers)

            status = response.json().get('status')
            if status == 0:
                for cookie_name in ['_kahai', '_karmt', '_karmtea', '_kawlt', '_kawltea']:
                    self.cookies[cookie_name] = response.cookies[cookie_name]
            else:
                raise Exception(f'로그인 과정에서 에러가 발생하였습니다.\n{status}')
        else:
            raise Exception(f'로그인을 실패하였습니다. 오류코드: {login_response.status_code}')

    def send(self, room, params, type='default'):
        payload = {
            'app_key': self.api_key,
            'validation_action': type,
            'validation_params': json.dumps(params),
            'ka': self.kakao_static,
            'lcba': ''
        }
        response = requests.post('https://sharer.kakao.com/talk/friends/picker/link', cookies=self.cookies, headers={'User-Agent': self.kakao_static, 'Referer': self.referer}, data=payload)
        if response.status_code != 200:
            raise ReferenceError('템플릿을 초기화하지 못했습니다. 매개변수를 확인해 주세요.')

        for cookie in ['PLAY_SESSION', 'using']:
            self.cookies[cookie] = response.cookies[cookie]

        validated_link = json.loads(self.BS(response.content, 'html.parser').find('input', {'id': 'validatedTalkLink'}).get('value'))
        csrf_token = self.BS(response.content, 'html.parser').find_all('div')[-1].get('ng-init').split('\'')[1]
        if not csrf_token:
            raise ReferenceError('로그인 세션이 만료되어서 다시 로그인 해야합니다.')

        chat_response = requests.get('https://sharer.kakao.com/api/talk/chats', headers={'User-Agent': self.kakao_static, 'Referer': 'https://sharer.kakao.com/talk/friends/picker/link', 'Csrf-Token': csrf_token, 'App-Key': self.api_key}, cookies=self.cookies)
        chats = {i['title'].replace(u'\xa0', u' '): i['id'] for i in chat_response.json()['chats']}

        if room not in chats:
            raise ReferenceError(f'방 이름 {room}을 찾을 수 없습니다.')

        send_payload = {
            'receiverChatRoomMemberCount': [1],
            'receiverIds': [chats[room]],
            'receiverType': 'chat',
            'securityKey': chat_response.json()['securityKey'],
            'validatedTalkLink': validated_link
        }

        send_response = requests.post('https://sharer.kakao.com/api/talk/message/link', headers={'User-Agent': self.kakao_static, 'Referer': 'https://sharer.kakao.com/talk/friends/picker/link', 'Csrf-Token': csrf_token, 'App-Key': self.api_key, 'Content-Type': 'application/json;charset=UTF-8'}, cookies=self.cookies, data=json.dumps(send_payload).encode('utf-8'))

        if send_response.status_code != 200:
            raise Exception('메시지를 보내지 못했습니다. 매개변수를 확인한 후 다시 시도하세요.')


if __name__ == "__main__":
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
