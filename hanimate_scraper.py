from bs4 import BeautifulSoup
from urllib.parse import quote
import requests


BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://hanime1.me/',
}


class CloudflareBlockedException(Exception):
    def __init__(self, url):
        self.url = url
        super().__init__('Cloudflare challenge required')


def _is_cf_block(html, status=200):
    if status == 403:
        return True
    low = html.lower()
    return 'just a moment' in low or 'challenge-platform' in low


class HanimateScraper:
    BASE_URL = 'https://hanime1.me'

    def __init__(self):
        self._bridge = None

    def set_bridge(self, bridge):
        self._bridge = bridge

    def has_bridge(self):
        return self._bridge is not None

    def close_bridge(self):
        if self._bridge:
            self._bridge.close()
            self._bridge = None

    def _fetch_html(self, url):
        if self._bridge:
            html = self._bridge.fetch_html(url)
            if _is_cf_block(html):
                raise CloudflareBlockedException(url)
            return html
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
        if _is_cf_block(r.text, r.status_code):
            raise CloudflareBlockedException(url)
        return r.text

    def search_videos(self, query):
        url = self.BASE_URL + '/search?query=' + quote(query) + '&genre='
        html = self._fetch_html(url)
        soup = BeautifulSoup(html, 'lxml')
        results = []
        containers = soup.find_all('div', class_='video-item-container')
        for container in containers:
            hcard = container.find('div', class_='horizontal-card')
            if not hcard:
                continue
            link_tag = hcard.find('a', class_='video-link')
            if not link_tag:
                continue
            href = link_tag.get('href', '')
            video_id = ''
            if 'hanime1.me' in href and 'v=' in href:
                video_id = href.split('v=')[1].split('&')[0]
            if not video_id:
                continue
            thumb_container = link_tag.find('div', class_='thumb-container')
            thumbnail = ''
            if thumb_container:
                img = thumb_container.find('img', class_='main-thumb')
                if img:
                    thumbnail = img.get('src', '')
            duration = ''
            if thumb_container:
                dur_div = thumb_container.find('div', class_='duration')
                if dur_div:
                    duration = dur_div.get_text(strip=True)
            likes = ''
            views = ''
            if thumb_container:
                stats = thumb_container.find('div', class_='stats-container')
                if stats:
                    stat_items = stats.find_all('div', class_='stat-item')
                    for item in stat_items:
                        text = item.get_text(strip=True)
                        if '%' in text:
                            likes = text
                        else:
                            views = text
            title_div = link_tag.find('div', class_='title')
            title = title_div.get_text(strip=True) if title_div else ''
            subtitle_div = hcard.find('div', class_='subtitle')
            subtitle = subtitle_div.get_text(strip=True) if subtitle_div else ''
            results.append({
                'id': video_id,
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'likes': likes,
                'views': views,
                'subtitle': subtitle,
                'url': href,
            })
        return results

    def get_download_links(self, video_id):
        url = self.BASE_URL + '/download?v=' + video_id
        html = self._fetch_html(url)
        soup = BeautifulSoup(html, 'lxml')
        results = []
        table = soup.find('table', class_='download-table')
        if not table:
            return results
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            quality_text = cells[1].get_text(strip=True)
            file_type = cells[2].get_text(strip=True)
            file_size = cells[3].get_text(strip=True)
            download_tag = cells[4].find('a')
            download_url = ''
            if download_tag:
                download_url = download_tag.get('data-url', '')
                if not download_url:
                    download_url = download_tag.get('href', '')
            if download_url and quality_text:
                results.append({
                    'quality': quality_text,
                    'file_type': file_type,
                    'file_size': file_size,
                    'download_url': download_url,
                })
        return results
