#!/usr/bin/env python3
"""
JAVDB 磁力链接监控工具

自动浏览 JAVDB 标签筛选页面，提取新增影片的磁力链接，保存到本地文件。
使用 DrissionPage 控制真实浏览器，模拟人类浏览行为，降低被检测风险。

用法:
    # 首次使用：打开浏览器登录 JAVDB
    python main.py --login

    # 正常运行：抓取新增磁力链接
    python main.py

    # 查看历史统计
    python main.py --stats
"""
import os
import sys
import argparse
import logging
import random
import time
import yaml
from datetime import datetime
from pathlib import Path

# 确保脚本在自身目录下运行
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

from browser import HumanBrowser
from db import HistoryDB

# ---- 日志配置 ----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def load_config(config_path=None):
    """加载 YAML 配置文件"""
    if config_path is None:
        config_path = BASE_DIR / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def write_magnets_to_file(output_file, results):
    """
    将新获取的磁力链接追加写入 txt 文件
    results: [{'video_id': ..., 'title': ..., 'magnets': [{'magnet': ..., 'name': ..., 'size': ...}]}]
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'a', encoding='utf-8') as f:
        f.write(f'\n# ========== {datetime.now().strftime("%Y-%m-%d %H:%M")} ==========\n')
        for item in results:
            vid = item['video_id']
            title = item.get('title', '')
            f.write(f'\n# {vid}')
            if title:
                f.write(f'  {title}')
            f.write('\n')
            for m in item['magnets']:
                size = m.get('size', '')
                if size:
                    f.write(f'# size: {size}\n')
                f.write(f'{m["magnet"]}\n')

    logger.info(f'已写入 {output_path}')


# ---- 命令：登录 ----

def cmd_login(config):
    """打开浏览器，让用户手动登录 JAVDB"""
    browser_cfg = config.get('browser', {})
    browser = HumanBrowser(
        profile_dir=browser_cfg.get('profile_dir', './browser_data'),
        headless=False,  # 登录必须有头模式
        browser_path=browser_cfg.get('browser_path') or None,
    )

    try:
        browser.navigate('https://javdb.com', delays=(2, 4))
        print()
        print('=' * 55)
        print('  浏览器已打开，请在浏览器中完成以下操作：')
        print()
        print('  1. 登录你的 JAVDB 账号')
        print('  2. 登录成功后，试着访问标签筛选页')
        print('  3. 选择标签（如「足交」），勾选「含磁鏈」')
        print('  4. 复制地址栏的 URL')
        print('  5. 将 URL 粘贴到 config.yaml 的对应位置')
        print()
        print('  完成后回到终端，按 Enter 关闭浏览器')
        print('=' * 55)
        print()
        input('按 Enter 关闭浏览器...')
    finally:
        browser.close()

    print('\n登录完成！浏览器配置已保存。')
    print('现在请编辑 config.yaml，填入标签筛选 URL，然后运行:')
    print('  python main.py')


# ---- 命令：查看统计 ----

def cmd_stats(config):
    """显示历史抓取统计"""
    db = HistoryDB(config.get('db_file', './data/history.db'))
    stats = db.get_stats()
    db.close()
    print(f'已记录影片数: {stats["videos"]}')
    print(f'已记录磁力链接数: {stats["magnets"]}')


# ---- 命令：运行监控 ----

def cmd_run(config):
    """主运行逻辑：遍历标签页，提取新增磁力链接"""
    tags = config.get('tags', [])
    max_pages = config.get('max_pages', 3)
    delays = config.get('delays', {})
    browser_cfg = config.get('browser', {})

    # 检查标签 URL 是否已配置
    valid_tags = [t for t in tags if t.get('url')]
    if not valid_tags:
        print('错误: 没有配置标签筛选 URL')
        print('请先运行 python main.py --login 登录并获取 URL')
        print('然后编辑 config.yaml 填入标签筛选 URL')
        sys.exit(1)

    db = HistoryDB(config.get('db_file', './data/history.db'))
    browser = HumanBrowser(
        profile_dir=browser_cfg.get('profile_dir', './browser_data'),
        headless=browser_cfg.get('headless', False),
        browser_path=browser_cfg.get('browser_path') or None,
    )

    all_new_results = []
    total_checked = 0
    total_skipped = 0
    total_new = 0

    try:
        for tag_info in valid_tags:
            tag_name = tag_info['name']
            tag_url = tag_info['url']

            logger.info(f'开始处理标签: {tag_name}')
            logger.info(f'URL: {tag_url}')

            current_url = tag_url

            for page_num in range(1, max_pages + 1):
                logger.info(f'--- 第 {page_num}/{max_pages} 页 ---')
                browser.navigate(current_url, delays=delays.get('after_page_load', [3, 6]))

                # 检查是否被重定向到登录页
                if browser.is_login_page():
                    logger.warning('需要登录！正在等待手动登录...')
                    browser.wait_for_login()
                    browser.navigate(current_url, delays=delays.get('after_page_load', [3, 6]))

                # 模拟浏览页面
                browser.human_scroll_page(delays=delays.get('between_scrolls', [0.3, 1.2]))

                # 提取视频列表
                videos = browser.get_video_list()
                logger.info(f'本页找到 {len(videos)} 个影片')

                if not videos:
                    logger.info('本页无影片，停止翻页')
                    break

                seen_count = 0

                for video in videos:
                    vid = video['video_id']
                    total_checked += 1

                    if db.is_seen(vid):
                        seen_count += 1
                        total_skipped += 1
                        logger.debug(f'  [跳过] {vid} (已获取过)')
                        continue

                    logger.info(f'  [新] {vid} - 访问详情页...')
                    browser.human_delay(delays.get('between_videos', [4, 10]))
                    browser.navigate(video['url'], delays=delays.get('after_page_load', [3, 6]))

                    # 检查登录
                    if browser.is_login_page():
                        logger.warning('详情页需要登录，等待...')
                        browser.wait_for_login()
                        browser.navigate(video['url'], delays=delays.get('after_page_load', [3, 6]))

                    # 模拟浏览详情页
                    browser.human_scroll_down(distance=random.randint(400, 800))
                    browser.human_delay(delays.get('reading_detail', [2, 5]))

                    # 提取信息
                    detail = browser.get_video_detail()
                    magnets = browser.get_magnets()

                    if magnets:
                        total_new += len(magnets)
                        db.add_video(
                            video_id=vid,
                            title=detail.get('title', video.get('title', '')),
                            url=video['url'],
                            tag=tag_name,
                            date=detail.get('date', ''),
                            magnets=magnets,
                        )
                        all_new_results.append({
                            'video_id': vid,
                            'title': detail.get('title', video.get('title', '')),
                            'magnets': magnets,
                        })
                        logger.info(f'  提取到 {len(magnets)} 个磁力链接')
                    else:
                        # 没有磁力链接也记录，避免下次重复访问
                        db.add_video(
                            video_id=vid,
                            title=detail.get('title', video.get('title', '')),
                            url=video['url'],
                            tag=tag_name,
                            date=detail.get('date', ''),
                            magnets=[],
                        )
                        logger.info(f'  该影片无磁力链接')

                    # 回到列表页
                    browser.navigate(current_url, delays=delays.get('after_page_load', [3, 6]))
                    browser.human_scroll_page(delays=delays.get('between_scrolls', [0.3, 1.2]))

                # 如果本页大部分都是已见过的，考虑提前终止
                if videos and seen_count == len(videos):
                    logger.info(f'本页所有影片都已获取过，停止翻页')
                    break

                # 翻页
                if page_num < max_pages:
                    next_url = browser.get_next_page_url()
                    if next_url:
                        logger.info(f'翻到下一页...')
                        browser.human_delay(delays.get('between_pages', [5, 12]))
                        current_url = next_url
                    else:
                        logger.info('没有下一页了')
                        break

            logger.info(f'标签 [{tag_name}] 处理完成\n')

    except KeyboardInterrupt:
        logger.info('\n用户中断，正在保存已获取的数据...')
    except Exception as e:
        logger.error(f'运行出错: {e}', exc_info=True)
    finally:
        browser.close()
        db.close()

    # 输出结果
    print()
    print('=' * 45)
    print(f'  本次运行统计')
    print(f'  检查影片数:   {total_checked}')
    print(f'  跳过(已有):   {total_skipped}')
    print(f'  新增磁力链接: {total_new}')
    print('=' * 45)

    if all_new_results:
        write_magnets_to_file(config.get('output_file', './output/magnets.txt'), all_new_results)
        print(f'\n新增磁力链接已保存到: {config.get("output_file", "./output/magnets.txt")}')
    else:
        print('\n本次没有新增磁力链接')


# ---- 入口 ----

def main():
    parser = argparse.ArgumentParser(
        description='JAVDB 磁力链接监控工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python main.py --login      首次使用，打开浏览器登录
  python main.py              运行监控，抓取新增磁力链接
  python main.py --stats      查看历史统计
  python main.py --config /path/to/config.yaml  使用自定义配置
        ''',
    )
    parser.add_argument('--login', action='store_true',
                        help='打开浏览器进行登录设置')
    parser.add_argument('--stats', action='store_true',
                        help='查看历史抓取统计')
    parser.add_argument('--config', type=str, default=None,
                        help='配置文件路径 (默认: config.yaml)')
    parser.add_argument('--debug', action='store_true',
                        help='开启调试日志')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config(args.config)

    if args.login:
        cmd_login(config)
    elif args.stats:
        cmd_stats(config)
    else:
        cmd_run(config)


if __name__ == '__main__':
    main()
