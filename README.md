# Iwara Desktop Client

基于 PyQt5 的 Iwara.tv 桌面客户端，支持视频浏览、播放、下载，以及 Hanime1.me 搜索结果集成。

## 功能

- Iwara 视频浏览（热门/最新/播放量/点赞数）
- 视频详情 + 内嵌播放
- 视频下载（后台，多清晰度）
- Hanime1.me 作者搜索（自动 Cloudflare 验证）
- 订阅频道视频列表
- 下载管理（进行中/已完成/重试/清除记录）
- 账号登录持久化
- 亮色极简主题

## 环境要求

- Windows 10+
- Python 3.9+
- Edge/Chrome 浏览器（用于 Hanime Cloudflare 验证）
- 首次运行前需安装内置浏览器：`python -m playwright install chromium`

## 快速开始

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装内置浏览器（Hanime Cloudflare 验证用）
python -m playwright install chromium

# 启动
python app.py
```

或直接运行 `run.bat`。

## 项目结构

```
iwara/
├── app.py                  # 主入口
├── api_client.py           # Iwara API 客户端
├── hanimate_scraper.py     # Hanime 爬虫
├── download_manager.py     # 下载管理器
├── ui/                     # UI 组件
│   ├── main_window.py      # 主窗口
│   ├── home_tab.py         # 首页
│   ├── favorites_tab.py    # 关注页
│   ├── downloads_tab.py    # 下载管理页
│   ├── profile_tab.py      # 我的页面
│   ├── video_card.py       # 视频卡片
│   ├── video_detail.py     # 视频详情
│   ├── login_dialog.py     # 登录对话框
│   ├── download_dialog.py  # 下载进度
│   ├── cloudflare_dialog.py# Cloudflare 验证
│   ├── hanimate_search_dialog.py # Hanime 搜索
│   └── widgets.py          # 通用组件
├── workers/                # 后台工作线程
│   ├── api_worker.py       # API 请求
│   ├── download_worker.py  # 下载线程
│   ├── cloudflare_solver.py# CF 自动验证
│   └── hanimate_worker.py  # Hanime 爬取
├── resources/              # 资源文件
│   ├── dark.qss            # 极简主题
│   └── logo.svg            # 应用图标
└── run.bat                 # 一键启动脚本
```

## 打包为 exe

```bash
pip install pyinstaller
python -m PyInstaller iwara.spec --clean --noconfirm
```

输出在 `dist\IwaraClient\`。

## License

MIT

## 致谢

本项目基于 [xiatg/iwara-python-api](https://github.com/xiatg/iwara-python-api) 的 API 客户端代码（MIT License）。
