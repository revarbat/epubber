import sys
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

    def add_file_from_data(self, targfile, data):
        self.zipFile.writestr(targfile, data)

    def add_file_from_url(self, targfile, url):
        resp = requests.get(url, stream=True)
        if resp.status_code == 200:
            imgdata = BytesIO()
            for chunk in resp.iter_content(1024):
                imgdata.write(chunk)
            imgdata.seek(0)
            self.zipFile.writestr(targfile, imgdata.getvalue())
            del imgdata

    def finish(self):
        self.zipFile.close()
        self.memOut.seek(0)
        return self.memOut.getvalue()



