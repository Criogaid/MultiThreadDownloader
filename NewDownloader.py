from __future__ import annotations

import os
import signal
from time import time

# 用于多线程操作
import multitasking
# 加速计算（可精简）
import numpy as np
# 用于发起网络请求
import requests
# 导入 retry 库以方便进行下载出错重试
from retry import retry
# 用于显示进度条
from tqdm import tqdm
# 终止已开启的全部线程达到初始化效果
signal.signal(signal.SIGINT, multitasking.killall)
# 主体框架来源
'''https://zhuanlan.zhihu.com/p/369531344'''

# 请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
}

# 存放所有进程/线程
threads = []

def split(start: int, end: int, step: int) -> list[tuple[int, int]]:
    # 文件切割 来自知乎用户Jack Bauer的留言
    parts = [(start, min(np.add(start, step), end))
             for start in range(0, end, step)]
    return parts


def get_file_name(url, header):
    # 获取文件名称，提高泛用性
    '''https://blog.csdn.net/mbh12333/article/details/103721834'''
    filename = ''
    if 'Content-Disposition' in header and header['Content-Disposition']:
        disposition_split = header['Content-Disposition'].split(';')
        if len(disposition_split) > 1:
            if disposition_split[1].strip().lower().startswith('filename='):
                file_name = disposition_split[1].split('=')
                if len(file_name) > 1:
                    try:
                        filename = eval(file_name[1])
                    except NameError:
                        filename = file_name[1]
    if not filename and os.path.basename(url):
        filename = os.path.basename(url).split("?")[0]
    if not filename:
        return time.time()
    return filename


def get_file_size(url: str, header, raise_error: bool = False):
    # 从Range获取文件大小，由于请求头中发送了{'Range': 'bytes=0-0'}，Length的值大多为1，若Range无法正确获取文件大小，则通过Length获取
    if (filesize := header.get('Content-Range')) is None:
        header_ = requests.head(url=url, allow_redirects=True).headers
        file_size = header_.get('Content-Length')
    else:
        file_size = filesize.split('/')[1]
    # 无法获取文件大小则报错
    if raise_error is True:
        raise ValueError('该文件不支持多线程分段下载！')
    return int(file_size)


def download(url: str, retry_times: int = 3) -> None:
    # 获取返回头，用于文件名及文件大小分析
    header_ = requests.head(url=url, headers={'Range': 'bytes=0-0'}, allow_redirects=True).headers
    file_name, file_size = get_file_name(url=url, header=header_), get_file_size(url=url, header=header_)
    # 创建同名空文件提供写入
    f = open(file_name, 'wb')
    
    
    @retry(tries=retry_times)  # 失败重试
    @multitasking.task  # 多线程
    def start_download(start: int, end: int) -> None:
        _headers = headers.copy()
        # 分段下载的核心
        _headers['Range'] = f'bytes={np.subtract(start, end)}'
        # 发起请求并获取响应（流式）
        response = session.get(url, headers=_headers, stream=True, allow_redirects=True)
        # 每次读取的流式响应大小
        chunk_size = 128
        # 暂存已获取的响应，后续循环写入
        chunks = []
        for chunk in response.iter_content(chunk_size=chunk_size):
            # 暂存获取的响应
            chunks.append(chunk)
            # 更新进度条
            bar.update(chunk_size)
        f.seek(start)
        for chunk in chunks:
            f.write(chunk)
        # 释放已写入的资源
        del chunks

    session = requests.Session()
    # 分割文件，目前默认16线程，若文件大小小于16MB则单线程
    if file_size <= np.rint(np.multiply(16, np.power(1024, 2))):
        parts = split(0, file_size, file_size)
    else:
        parts = split(0, file_size, int(np.divide(file_size, 15)))
    # 创建进度条
    bar = tqdm(total=file_size, desc=f'下载文件：{file_name}')
    # 创建线程，开始下载
    for part in parts:
        start, end = part
        start_download(start, end)
    # 等待全部线程结束
    multitasking.wait_for_tasks()
    print(f'下载完毕，用时{np.subtract(time(), start_time)}秒')
    f.close()
    bar.close()


if "__main__" == __name__:
    ####################测试链接####################
    # url = 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/packages/0d/ea/f936c14b6e886221e53354e1992d0c4e0eb9566fcc70201047bb664ce777/tensorflow-2.3.1-cp37-cp37m-macosx_10_9_x86_64.whl#sha256=1f72edee9d2e8861edbb9e082608fd21de7113580b3fdaa4e194b472c2e196d0'
    # url = 'https://ak.hycdn.cn/apk/202204121544-1801-yk1f3rk2xef6ouhqok38/arknights-hg-1801.apk'
    # url = 'http://omp.boogiepop.top/c02/2021%E5%B9%B404%E6%9C%88%E7%95%AA/%E5%89%83%E9%A1%BB%E3%80%82%E7%84%B6%E5%90%8E%E6%8D%A1%E5%88%B0%E5%A5%B3%E9%AB%98%E4%B8%AD%E7%94%9F/%E3%80%90%E5%96%B5%E8%90%8C%E5%A5%B6%E8%8C%B6%E5%B1%8B%E3%80%91[%E5%89%83%E9%A1%BB%E3%80%82%E7%84%B6%E5%90%8E%E6%8D%A1%E5%88%B0%E5%A5%B3%E9%AB%98%E4%B8%AD%E7%94%9F%E3%80%82%E5%88%AE%E6%8E%89%E8%83%A1%E5%AD%90%E7%9A%84%E6%88%91%E4%B8%8E%E6%8D%A1%E5%88%B0%E7%9A%84%E5%A5%B3%E9%AB%98%E4%B8%AD%E7%94%9FHige%20wo%20Soru.%20Soshite%20Joshikousei%20wo%20Hirou.][01-13][BDRip][1080p][%E7%AE%80%E4%BD%93]/[Nekomoe%20kissaten][Higehiro][01][1080p][CHS].mp4'
    # url = "https://issuecdn.baidupcs.com/issue/netdisk/yunguanjia/BaiduNetdisk_7.2.8.9.exe"
    # url = "https://github.com/EhPanda-Team/EhPanda/releases/download/v2.4.0_b136/EhPanda.ipa"
    ################################################
    # 开始下载文件
    start_time = time()
    download(url)
