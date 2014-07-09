import sys
import time
import requests
import zipfile

import clay.config

from io import BytesIO
 
reload(sys)
sys.setdefaultencoding('utf-8')


errorlog = clay.config.get_logger('epubber_error')


class MemZip():
    memOut = None
    zipFile = None

    def __init__(self):
        self.memOut = BytesIO()
        self.zipFile = zipfile.ZipFile(
            self.memOut, 'w',
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=False
        ) 

    def add_file(self, targfile, filename):
        self.zipFile.write(targfile, filename)
        return True

    def add_file_from_data(self, targfile, data):
        self.zipFile.writestr(targfile, data)
        return True

    def add_file_from_url(self, targfile, url):
        resp = None
        for retry in range(3):
            try:
                resp = requests.get(url, stream=True)
            except requests.exceptions.RequestException, e:
                errorlog.exception('Failed to HTTP GET file at %s' % url)
                break
            if resp.status_code == 200:
                break
            if resp.status_code == 404:
                errorlog.warning('Got 404 on trying to HTTP GET file at %s' % url)
                break
            time.sleep(2*(2**retry))
        if not resp:
            return False
        if resp.status_code == 200:
            imgdata = BytesIO()
            for chunk in resp.iter_content(1024):
                imgdata.write(chunk)
            imgdata.seek(0)
            self.zipFile.writestr(targfile, imgdata.getvalue())
            del imgdata
            return True
        return False

    def finish(self):
        self.zipFile.close()
        self.memOut.seek(0)
        return self.memOut.getvalue()



# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 nowrap

