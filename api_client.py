# Iwara API Client
# Originally based on: https://github.com/xiatg/iwara-python-api (MIT License)
import cloudscraper, requests, hashlib, os

api_url = 'https://api.iwara.tv'
file_url = 'https://files.iwara.tv'

class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Bearer ' + self.token
        return r

class ApiClient:
    def __init__(self, email=None, password=None):
        self.scraper = cloudscraper.create_scraper()
        self.email = email
        self.password = password
        self.api_url = api_url
        self.file_url = file_url
        self.token = None

    def _request(self, method, url, **kwargs):
        if self.token:
            kwargs.setdefault('auth', BearerAuth(self.token))
        return getattr(self.scraper, method)(url, **kwargs)

    def login(self, email=None, password=None) -> requests.Response:
        if email:
            self.email = email
        if password:
            self.password = password
        url = self.api_url + '/user/login'
        json = {'email': self.email, 'password': self.password}
        r = self.scraper.post(url, json=json)
        try:
            self.token = r.json().get('token')
        except:
            self.token = None
        return r

    def get_videos(self, sort='date', rating='all', page=0, limit=32, subscribed=False) -> requests.Response:
        url = self.api_url + '/videos'
        params = {
            'sort': sort,
            'rating': rating,
            'page': page,
            'limit': limit,
            'subscribed': 'true' if subscribed else 'false',
        }
        return self._request('get', url, params=params)

    def get_video(self, video_id) -> requests.Response:
        url = self.api_url + '/video/' + video_id
        return self._request('get', url)

    def get_user(self) -> requests.Response:
        url = self.api_url + '/user'
        return self._request('get', url)

    def get_favorites(self, page=0, limit=32) -> requests.Response:
        url = self.api_url + '/favorites'
        params = {'page': page, 'limit': limit}
        return self._request('get', url, params=params)

    def add_favorite(self, video_id) -> requests.Response:
        url = self.api_url + '/favorite/' + video_id
        return self._request('post', url)

    def remove_favorite(self, video_id) -> requests.Response:
        url = self.api_url + '/favorite/' + video_id
        return self._request('delete', url)

    def get_video_download_info(self, video_id):
        video = self.get_video(video_id).json()
        url = video.get('fileUrl', '')
        file_id = video.get('file', {}).get('id', '')
        if not url or not file_id:
            return None
        expires = url.split('/')[4].split('?')[1].split('&')[0].split('=')[1]
        SHA_postfix = "_5nFp9kmbNnHdAFhaqMvt"
        SHA_key = file_id + "_" + expires + SHA_postfix
        hash_val = hashlib.sha1(SHA_key.encode('utf-8')).hexdigest()
        headers = {"X-Version": hash_val}
        resources = self._request('get', url, headers=headers).json()
        result = {'video': video, 'resources': []}
        for resource in resources:
            src = resource.get('src', {})
            if not src:
                continue
            download_url = src.get('download', '')
            if download_url and not download_url.startswith('http'):
                download_url = 'https:' + download_url
            file_type = resource.get('type', 'video/mp4').split('/')[-1]
            name = resource.get('name', '')
            result['resources'].append({
                'name': name,
                'download_url': download_url,
                'file_type': file_type,
            })
        return result

    def download_video_thumbnail(self, video_id, save_dir='.') -> str:
        video = self.get_video(video_id).json()
        file_id = video['file']['id']
        thumbnail_id = video['thumbnail']
        url = self.file_url + '/image/original/' + file_id + '/thumbnail-{:02d}.jpg'.format(thumbnail_id)
        thumbnail_file_name = os.path.join(save_dir, video_id + '.jpg')
        if os.path.exists(thumbnail_file_name):
            return thumbnail_file_name
        with open(thumbnail_file_name, "wb") as f:
            for chunk in self.scraper.get(url).iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
        return thumbnail_file_name

    def download_video(self, video_id, save_dir='.', progress_callback=None) -> str:
        download_info = self.get_video_download_info(video_id)
        if not download_info or not download_info['resources']:
            raise Exception("No video with Source quality found")
        resource = download_info['resources'][0]
        download_link = resource['download_url']
        file_type = resource['file_type']
        video_file_name = os.path.join(save_dir, video_id + '.' + file_type)
        if os.path.exists(video_file_name):
            return video_file_name
        r = self.scraper.get(download_link, stream=True)
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(video_file_name, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded, total)
        return video_file_name
