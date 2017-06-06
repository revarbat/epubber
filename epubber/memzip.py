import sys
import time
import requests
import zipfile

import clay.config

from io import BytesIO
from multiprocessing import Pool

reload(sys)
sys.setdefaultencoding('utf-8')


errorlog = clay.config.get_logger('epubber_error')


def fetch_from_url(url):
    resp = None
    for retry in range(3):
        try:
            resp = requests.get(url, stream=True, timeout=10.0)
        except requests.exceptions.RequestException, e:
            errorlog.exception('Failed to HTTP GET file at %s' % url)
        except requests.exceptions.Timeout, e:
            errorlog.exception('Timed out trying to HTTP GET file at %s' % url)
            continue
        if resp.status_code == 200:
            imgdata = BytesIO()
            for chunk in resp.iter_content(8192):
                imgdata.write(chunk)
            imgdata.seek(0)
            return imgdata.getvalue()
        if resp.status_code // 100 in [4, 5]:
            errorlog.warning('Got %d on trying to HTTP GET file at %s' % (resp.status_code, url))
            break
        time.sleep(2*(2**retry))
    return None


class MemZip():
    def __init__(self):
        self.memOut = BytesIO()
        self.zipFile = zipfile.ZipFile(
            self.memOut, 'w',
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=False
        )
        self.url_target_files = {}
        self.fetch_tasks = {}
        self.pool = Pool(processes=10, maxtasksperchild=4)

    def add_file(self, targfile, filename):
        self.zipFile.write(targfile, filename)
        return True

    def add_file_from_data(self, targfile, data):
        self.zipFile.writestr(targfile, data)
        return True

    def add_file_from_url(self, targfile, url):
        if url not in self.url_target_files:
            self.url_target_files[url] = targfile
            self.fetch_tasks[url] = self.pool.apply_async(fetch_from_url, (url,))
        return True

    def poll_web_fetches(self, callback=None):
        for url in self.fetch_tasks.keys():
            if self.fetch_tasks[url].ready():
                if self.fetch_tasks[url].successful():
                    data = self.fetch_tasks[url].get()
                    if data is not None:
                        self.add_file_from_data(self.url_target_files[url], data)
                        if callback is not None and callable(callback):
                            callback(url)
                        data = None
                del self.url_target_files[url]
                del self.fetch_tasks[url]

    def finish_web_fetches(self, callback=None):
        while self.fetch_tasks:
            time.sleep(0.1)
            self.poll_web_fetches(callback=callback)
        self.pool.close()
        self.pool.join()

    def pending_web_fetches(self):
        return len(self.fetch_tasks)

    def finish(self):
        self.finish_web_fetches()
        self.zipFile.close()
        self.memOut.seek(0)
        return self.memOut.getvalue()


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 nowrap

