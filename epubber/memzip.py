import sys
import time
import requests
import zipfile

from io import BytesIO
 
reload(sys)
sys.setdefaultencoding('utf-8')



class MemZip():
    memOut = None
    zipFile = None

    def __init__(self):
        self.memOut = BytesIO()
        self.zipFile = zipfile.ZipFile(self.memOut, 'w') 

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
                break
            if resp.status_code == 200:
                break
            if resp.status_code == 404:
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



