"""
浏览器自动化模块 - 使用 DrissionPage 模拟真人浏览行为
DrissionPage 不使用 WebDriver 协议，对 Cloudflare 检测的规避效果最好
"""
import random
import time
import logging
from pathlib import Path

from DrissionPage import Chromium, ChromiumOptions

logger = logging.getLogger(__name__)

JAVDB_BASE = 'https://javdb.com'


class HumanBrowser:
    """封装 DrissionPage，提供人类行为模拟能力"""

    def __init__(self, profile_dir='./browser_data', headless=False, browser_path=None):
        co = ChromiumOptions()
        if browser_path:
            co.set_browser_path(browser_path)
        co.set_user_data_path(str(Path(profile_dir).resolve()))
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_argument('--window-size=1920,1080')
        co.set_argument('--lang=zh-TW')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-dev-shm-usage')
        if headless:
            co.headless()

        logger.info('正在启动浏览器...')
        self.browser = Chromium(co)
        self.tab = self.browser.latest_tab
        logger.info('浏览器已启动')

    # ------------------------------------------------------------------
    # 人类行为模拟
    # ------------------------------------------------------------------

    @staticmethod
    def _rand(range_pair):
        """从 [min, max] 区间取随机值"""
        return random.uniform(range_pair[0], range_pair[1])

    def human_delay(self, range_pair=(1, 3)):
        """随机等待，模拟人类阅读/思考时间"""
        delay = self._rand(range_pair)
        time.sleep(delay)

    def human_scroll_down(self, distance=None, delays=(0.3, 1.2)):
        """模拟人类滚动：分多步、变速、偶尔停顿"""
        if distance is None:
            distance = random.randint(300, 800)

        steps = random.randint(3, 7)
        remaining = distance

        for i in range(steps):
            if remaining <= 0:
                break
            # 中间步骤滚动距离大，开头和结尾小（模拟加速-减速）
            progress = i / max(steps - 1, 1)
            factor = 0.6 + 0.8 * (1 - abs(2 * progress - 1))
            chunk = int(remaining / max(steps - i, 1) * factor)
            chunk = max(20, min(chunk, remaining))

            self.tab.actions.scroll(delta_y=chunk)
            remaining -= chunk
            time.sleep(self._rand(delays))

        # 处理剩余
        if remaining > 0:
            self.tab.actions.scroll(delta_y=remaining)

    def human_scroll_page(self, delays=(0.3, 1.2)):
        """模拟浏览整个页面：多次滚动 + 中间停顿阅读"""
        scroll_times = random.randint(3, 6)
        for _ in range(scroll_times):
            self.human_scroll_down(
                distance=random.randint(200, 600),
                delays=delays,
            )
            # 偶尔停下来"阅读"
            if random.random() < 0.4:
                time.sleep(self._rand((1, 3)))

    def human_move_and_click(self, element):
        """模拟人类：移动鼠标到元素 → 短暂停顿 → 点击"""
        duration = random.uniform(0.3, 0.8)
        self.tab.actions.move_to(element, duration=duration)
        time.sleep(random.uniform(0.1, 0.4))
        self.tab.actions.click()
        # 30% 概率微小抖动（模拟手指不稳）
        if random.random() < 0.3:
            self.tab.actions.move(
                offset_x=random.randint(-3, 3),
                offset_y=random.randint(-3, 3),
                duration=0.1,
            )

    # ------------------------------------------------------------------
    # 页面导航
    # ------------------------------------------------------------------

    def navigate(self, url, delays=(3, 6)):
        """导航到 URL，等待页面加载 + Cloudflare 验证通过"""
        logger.debug(f'导航至: {url}')
        self.tab.get(url)
        self._wait_for_cloudflare()
        self.human_delay(delays)

    def _wait_for_cloudflare(self, timeout=30):
        """等待 Cloudflare 验证页面自动通过"""
        start = time.time()
        while time.time() - start < timeout:
            title = self.tab.title or ''
            html_snippet = (self.tab.html or '')[:2000]
            if 'Just a moment' in title or 'Checking your browser' in html_snippet:
                logger.info('检测到 Cloudflare 验证页面，等待自动通过...')
                time.sleep(2)
                continue
            break

    def is_login_page(self):
        """检测当前页面是否为 JAVDB 登录页"""
        url = self.tab.url or ''
        return '/login' in url or '/sign_in' in url

    def wait_for_login(self):
        """等待用户手动完成登录"""
        if not self.is_login_page():
            return True

        logger.info('=' * 50)
        logger.info('请在浏览器中手动登录 JAVDB')
        logger.info('登录完成后，脚本将自动继续')
        logger.info('=' * 50)

        while self.is_login_page():
            time.sleep(2)

        logger.info('登录成功！')
        time.sleep(3)
        return True

    # ------------------------------------------------------------------
    # 页面数据提取
    # ------------------------------------------------------------------

    def get_video_list(self):
        """
        从当前标签列表页提取视频条目
        返回: [{'video_id': 'ABC-123', 'url': 'https://...', 'title': '...'}, ...]
        """
        videos = []
        # JAVDB 列表页使用 a.box 包裹每个影片条目
        items = self.tab.eles('css:a.box')
        for item in items:
            try:
                href = item.attr('href') or ''
                title = item.attr('title') or ''
                # 番号在 .video-title strong 里
                vid_el = item.ele('css:.video-title strong', timeout=0)
                video_id = vid_el.text.strip() if vid_el else ''

                if not video_id or not href:
                    continue

                full_url = href if href.startswith('http') else JAVDB_BASE + href
                videos.append({
                    'video_id': video_id,
                    'url': full_url,
                    'title': title,
                })
            except Exception as e:
                logger.debug(f'解析视频条目时出错: {e}')
                continue

        return videos

    def get_magnets(self):
        """
        从当前影片详情页提取磁力链接
        返回: [{'magnet': 'magnet:?xt=...', 'name': '...', 'size': '...'}, ...]
        """
        magnets = []
        # JAVDB 详情页的磁力链接区域
        magnet_rows = self.tab.eles('css:.magnet-name.column.is-four-fifths')
        for row in magnet_rows:
            try:
                link_el = row.ele('css:a', timeout=0)
                if not link_el:
                    continue
                magnet_url = link_el.attr('href') or ''
                if not magnet_url.startswith('magnet:'):
                    continue
                # 去掉 [javdb.com] 标记
                magnet_url = magnet_url.replace('[javdb.com]', '')

                # 尝试获取名称和大小
                name_el = row.ele('css:span.name', timeout=0)
                size_el = row.ele('css:span.meta', timeout=0)
                name = name_el.text.strip() if name_el else ''
                size = size_el.text.strip() if size_el else ''

                magnets.append({
                    'magnet': magnet_url,
                    'name': name,
                    'size': size,
                })
            except Exception as e:
                logger.debug(f'解析磁力链接时出错: {e}')
                continue

        return magnets

    def get_video_detail(self):
        """从当前详情页获取影片基本信息"""
        info = {}
        try:
            title_el = self.tab.ele('css:h2 strong.current-title', timeout=2)
            info['title'] = title_el.text.strip() if title_el else ''
        except Exception:
            info['title'] = ''

        try:
            date_el = self.tab.ele('xpath://strong[text()="日期:"]', timeout=1)
            if date_el:
                next_el = date_el.next()
                info['date'] = next_el.text.strip() if next_el else ''
        except Exception:
            info['date'] = ''

        return info

    def get_next_page_url(self):
        """获取下一页的 URL，如果没有下一页返回 None"""
        try:
            next_btn = self.tab.ele('css:a.pagination-next[rel="next"]', timeout=2)
            if next_btn:
                href = next_btn.attr('href') or ''
                if href:
                    return href if href.startswith('http') else JAVDB_BASE + href
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self):
        """关闭浏览器"""
        try:
            self.browser.quit()
            logger.info('浏览器已关闭')
        except Exception:
            pass
