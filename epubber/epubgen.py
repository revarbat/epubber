from __future__ import absolute_import

import sys
from epubber.memzip import MemZip

 
reload(sys)
sys.setdefaultencoding('utf-8')


class ArgumentError(Exception):
    msg = ''
    def __init__(self, mesg):
        self.msg = mesg



class ePubGenerator():
    mem_zip = None
    manifest_files = []
    contents_index = []
    chapter_num = 0
    image_num = 0
    metas = {}

    def __init__(self):
        self.mem_zip = MemZip()
        self.manifest_files = []
        self.contents_index = []
        self.chapter_num = 0
        self.image_num = 0
        self.metas = {}


    def set_meta(self, key, val):
        self.metas[key] = val


    def add_file(self, targfile, tagname=None, mimetype='application/xhtml+xml', title=None, data=None, filename=None, url=None):
        if data:
            self.mem_zip.add_file_from_data(targfile, data)
        elif url:
            self.mem_zip.add_file_from_url(targfile, url)
        elif filename:
            self.mem_zip.add_file(targfile, filename)
        else:
            raise ArgumentError("Must specify one of data, url, or filename")
        if tagname:
            self.manifest_files.append( (tagname, targfile, mimetype) )
            if title:
                self.contents_index.append( (tagname, targfile, title) )


    def add_image(self, url, tagname=None):
        img_ext = '.jpeg'
        img_mime = 'image/jpeg'
        if '.gif' in url:
            img_ext = '.gif'
            img_mime = 'image/gif'
        if '.png' in url:
            img_ext = '.png'
            img_mime = 'image/png'
        if tagname is None:
            self.image_num += 1
            tagname = 'image%d' % self.image_num
        imgfile = tagname + img_ext
        self.add_file(imgfile, tagname=tagname, mimetype=img_mime, url=url)
        return imgfile


    def add_chapter(self, title, data):
        self.chapter_num += 1
        chapfile = "Chapter%d.html" % self.chapter_num
        chaptag = "chapter%d" % self.chapter_num
        self.add_file(chapfile, tagname=chaptag, title=title, mimetype='application/xhtml+xml', data=data)
        return chapfile


    def add_ncx(self):
        """ Create NCX index file """
        outdata = ''
        outdata += '<?xml version="1.0" encoding="UTF-8"?>\n'
        outdata += '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"\n "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n'
        outdata += '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en">\n'
        outdata += '\t<head>\n'
        outdata += '\t\t<meta name="dtb:uid" content="%(url)s" />\n'
        outdata += '\t\t<meta name="dtb:depth" content="2" />\n'
        outdata += '\t\t<meta name="dtb:totalPageCount" content="0" />\n'
        outdata += '\t\t<meta name="dtb:maxPageNumber" content="0" />\n'
        outdata += '\t\t<meta name="dtb:generator" content="fimfic_reader (1.0)" />\n'
        outdata += '\t</head>\n'
        outdata += '\t<docTitle><text>%(title)s</text></docTitle>\n'
        outdata += '\t<docAuthor><text>%(author)s</text></docAuthor>\n'
        outdata = outdata % self.metas
        outdata += '\t<navMap>\n'
        playorder = 0
        for chaptag,chapfile,chaptitle in self.contents_index:
            playorder += 1
            outdata += '\t\t<navPoint id="%s" playOrder="%d">\n' % (chaptag, playorder)
            outdata += '\t\t\t<navLabel><text>%s</text></navLabel>\n' % (chaptitle, )
            outdata += '\t\t\t<content src="%s" />\n' % (chapfile, )
            outdata += '\t\t</navPoint>\n'
        outdata += '\t</navMap>\n'
        outdata += '</ncx>\n'
        outdata = bytes(outdata)
        self.add_file("book.ncx", tagname='ncx', mimetype='application/x-dtbncx+xml', data=outdata)


    def add_opf(self):
        # Create OPF main metadata file
        outdata = ''
        outdata += '<?xml version="1.0" encoding="utf-8"?>\n'
        outdata += '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">\n'
        outdata += '\t<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        outdata += '\t\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        outdata += '\t\txmlns:opf="http://www.idpf.org/2007/opf"\n'
        outdata += '\t\txmlns:dcterms="http://purl.org/dc/terms/">\n'
        outdata += '\t\t<dc:title>%(title)s</dc:title>\n'
        outdata += '\t\t<dc:language>en</dc:language>\n'
        outdata += '\t\t<dc:identifier id="BookId" opf:scheme="URI">%(url)s</dc:identifier>\n'
        outdata += '\t\t<dc:description>%(description)s</dc:description>\n'
        outdata += '\t\t<dc:publisher>Fimfiction</dc:publisher>\n'
        outdata += '\t\t<dc:relation>http://www.fimfiction.net</dc:relation>\n'
        outdata += '\t\t<dc:creator opf:file-as="%(author)s" opf:role="aut">%(author)s</dc:creator>\n'
        outdata += '\t\t<dc:date>%(creationdate)s</dc:date>\n'
        outdata += '\t\t<dc:source>%(url)s</dc:source>\n'
        outdata += '\t</metadata>\n'
        outdata = outdata % self.metas
        outdata += '\t<manifest>\n'
        for chaptag,chapfile,chaptype in self.manifest_files:
            outdata += '\t\t<item id="%(chaptag)s" href="%(chapfile)s" media-type="%(chaptype)s" />\n' % {
                "chaptag": chaptag,
                "chapfile": chapfile,
                "chaptype": chaptype,
            }
        outdata += '\t</manifest>\n'
        outdata += '\t<spine toc="ncx">\n'
        for chaptag,chapfile,chaptitle in self.contents_index:
            outdata += '\t\t<itemref idref="%(chaptag)s" />\n' % {
                "chaptag": chaptag,
            }
        outdata += '\t</spine>\n'
        outdata += '</package>\n'
        outdata = bytes(outdata)
        self.add_file("book.opf", data=outdata)


    def add_base(self):
        outdata = ''
        outdata += '<?xml version="1.0" encoding="UTF-8"?>\n'
        outdata += '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        outdata += '\t<rootfiles>\n'
        outdata += '\t\t<rootfile full-path="book.opf" media-type="application/oebps-package+xml" />\n'
        outdata += '\t</rootfiles>\n'
        outdata += '</container>\n'
        outdata = bytes(outdata)
        self.add_file("META-INF/container.xml", data=outdata)


    def add_mimetype(self):
        # Create mimetype file
        self.add_file("mimetype", data="application/epub+zip")


    def finish(self):
        self.add_ncx()
        self.add_opf()
        self.add_base()
        self.add_mimetype()
        return self.mem_zip.finish()




