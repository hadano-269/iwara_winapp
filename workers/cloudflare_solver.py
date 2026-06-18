from PyQt5.QtCore import QThread, pyqtSignal
import subprocess, time, requests, json, os, sys, tempfile, websocket


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), '_internal')
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BUNDLED_CHROME_PATHS = [
    os.path.join(_app_dir(), 'browser', 'chrome-win64', 'chrome.exe'),
]

PLAYWRIGHT_CHROME_PATHS = [
    os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ms-playwright',
                 'chromium-1223', 'chrome-win64', 'chrome.exe'),
]

SYSTEM_BROWSER_PATHS = [
    ('Edge', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'),
    ('Edge', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'),
    ('Chrome', r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
    ('Chrome', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'),
]

CF_PROFILE_DIR = os.path.join(tempfile.gettempdir(), 'iwara_cf_profile')
CF_DEBUG_PORT = 19322


def find_browser():
    for path in BUNDLED_CHROME_PATHS:
        if os.path.exists(path):
            return 'Chromium', path
    for path in PLAYWRIGHT_CHROME_PATHS:
        if os.path.exists(path):
            return 'Chromium', path
    for name, path in SYSTEM_BROWSER_PATHS:
        if os.path.exists(path):
            return name, path
    import shutil
    for exe in ['msedge', 'chrome']:
        found = shutil.which(exe)
        if found:
            return ('Edge' if 'edge' in exe.lower() else 'Chrome'), found
    return None, None


class HanimateBrowserBridge:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.browser_name = None
        self.browser_path = None
        self._msg_id = 0
        self._closed = False

    def launch_and_verify(self, url, progress_cb=None):
        def log(msg):
            if progress_cb:
                progress_cb(msg)

        self.browser_name, self.browser_path = find_browser()
        if not self.browser_path:
            raise RuntimeError('未找到可用浏览器，请安装 Edge 或 Chrome，或运行 pip install playwright && python -m playwright install chromium')

        log(f'正在启动 {self.browser_name}...')
        self.proc = subprocess.Popen(
            [
                self.browser_path,
                f'--remote-debugging-port={CF_DEBUG_PORT}',
                '--remote-allow-origins=*',
                f'--user-data-dir={CF_PROFILE_DIR}',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-networking',
                '--disable-extensions',
                '--disable-popup-blocking',
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        log('等待浏览器启动...')
        time.sleep(3)

        log('连接浏览器...')
        r = requests.get(f'http://127.0.0.1:{CF_DEBUG_PORT}/json', timeout=5)
        tabs = r.json()
        target = None
        for tab in tabs:
            if 'hanime1' in tab.get('url', ''):
                target = tab
                break
        if not target:
            for tab in tabs:
                if tab.get('type') == 'page':
                    target = tab
                    break
        if not target:
            raise RuntimeError('未找到浏览器标签页')

        self.ws = websocket.create_connection(
            target['webSocketDebuggerUrl'],
            origin=f'http://127.0.0.1:{CF_DEBUG_PORT}',
        )

        log('等待 Cloudflare 验证通过...')
        for i in range(20):
            time.sleep(2)
            result = self._eval('document.querySelector(".video-item-container") ? "yes" : "no"')
            if result == 'yes':
                log('验证通过！')
                return True
            log(f'等待验证通过... ({i+1}/20)')

        raise RuntimeError('Cloudflare 验证超时')

    def fetch_html(self, url):
        escaped = url.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"')
        js = f'''
        (async () => {{
            try {{
                const resp = await fetch("{escaped}");
                const text = await resp.text();
                return text;
            }} catch(e) {{
                return "FETCH_ERROR:" + e.message;
            }}
        }})()
        '''
        self._msg_id += 1
        self.ws.send(json.dumps({
            'id': self._msg_id,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': js,
                'awaitPromise': True,
                'returnByValue': True,
            }
        }))
        result = json.loads(self.ws.recv())
        value = result.get('result', {}).get('result', {}).get('value', '')
        if isinstance(value, str) and value.startswith('FETCH_ERROR:'):
            raise RuntimeError(value)
        return value

    def _eval(self, expression):
        self._msg_id += 1
        self.ws.send(json.dumps({
            'id': self._msg_id,
            'method': 'Runtime.evaluate',
            'params': {'expression': expression, 'returnByValue': True}
        }))
        result = json.loads(self.ws.recv())
        return result.get('result', {}).get('result', {}).get('value', '')

    def close(self):
        if self._closed:
            return
        self._closed = True

        if self.ws:
            try:
                self._msg_id += 1
                self.ws.send(json.dumps({
                    'id': self._msg_id,
                    'method': 'Browser.close',
                }))
                self.ws.settimeout(3)
                try:
                    self.ws.recv()
                except Exception:
                    pass
            except Exception:
                pass
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

        if self.proc:
            for _ in range(10):
                ret = self.proc.poll()
                if ret is not None:
                    break
                time.sleep(0.3)
            if self.proc.poll() is None:
                try:
                    subprocess.Popen(
                        ['taskkill', '/F', '/T', '/PID', str(self.proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    ).wait(timeout=5)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
            self.proc = None


class CloudflareSolverWorker(QThread):
    solved = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.bridge = HanimateBrowserBridge()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self.bridge.launch_and_verify(self.url, self._emit_progress)
            if self._cancelled:
                self.bridge.close()
                return
            self.solved.emit(self.bridge)
        except Exception as e:
            self.bridge.close()
            self.failed.emit(str(e))

    def _emit_progress(self, msg):
        self.progress.emit(msg)


class BrowserCloseWorker(QThread):
    finished = pyqtSignal()

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def run(self):
        if self.bridge:
            self.bridge.close()
        self.finished.emit()
