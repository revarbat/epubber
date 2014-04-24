
import sys, re, time
import requests

from xml.dom.minidom import parseString as xmlParseString
from fixtags import FixTagsHtmlParser
from epubgen import ePubGenerator
from HTMLParser import HTMLParser
 
reload(sys)
sys.setdefaultencoding('utf-8')


class BodyFileHtmlParser(HTMLParser):
    chapters_data = []
    tag_stack = []
    _curr_data = ''
    _item_data = ''
    _chapter_title = ''
    _chapter_cb = None
    _image_cb = None
    self_closing_tags = [ 'br', 'hr', 'img', 'meta', 'link', 'input' ]

    def __init__(self):
        self.chapters_data = []
        self.tag_stack = []
        self._curr_data = ''
        self._item_data = ''
        self._chapter_title = ''
        self._chapter_cb = None
        self._image_cb = None
        HTMLParser.__init__(self)

    def _esc(self, s):
        safe_entities = [
            ('&', '&amp;'),
            ('"', '&quot;'),
            ("'", '&apos;'),
            ('<', '&lt;'),
            ('>', '&gt;')
        ]
        for ch,ent in safe_entities:
            s = s.replace(ch,ent)
        return s

    def _attrstr(self,attrs):
        out = ''
        for key,val in attrs:
            if val is None:
                out += ' %s' % key
            else:
                out += ' %s="%s"' % (key,self._esc(val))
        return out

    def set_chapter_cb(self, cb):
        self._chapter_cb = cb

    def set_image_cb(self, cb):
        self._image_cb = cb

    def chapter_complete(self):
        chaptitle = self._chapter_title.strip()
        outdata = self._curr_data.strip()
        outdata = re.sub(r'<hr ?/?>\s*$', '', outdata)
        if chaptitle and outdata:
            fixtags = FixTagsHtmlParser()
            fixtags.strip_js = True
            outdata = fixtags.fixup_string(outdata)
            del fixtags
            self._chapter_cb(chaptitle, outdata)
            self._chapter_title = ''
            self._curr_data = ''
            self._item_data = ''

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'body':
            self.tag_stack.append('body')
            return
        if len(self.tag_stack) == 0:
            return
        attrkeys = [key for key,val in attrs]
        if tag == 'a' and 'name' in attrkeys:
            self.chapter_complete()
            self.tag_stack.append('anchor')
            return
        if tag == 'h3' and self.tag_stack[-1] == 'anchor':
            self.tag_stack.pop()
            self.tag_stack.append('chaptitle')
            self._item_data = ''
            return
        if self.tag_stack[-1] == 'chaptitle':
            return
        if tag == 'iframe':
            return
        if not self._chapter_title:
            return
        if tag == 'img':
            newattrs = []
            for key,val in attrs:
                if key.lower() == 'src':
		    val = self._image_cb(val)
                newattrs.append( (key,val) )
            attrs = newattrs
        if tag in self.self_closing_tags:
            self._curr_data += '<%s%s />' % (tag, self._attrstr(attrs))
        else:
            self._curr_data += '<%s%s>' % (tag, self._attrstr(attrs))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'body':
            self.chapter_complete()
            self.tag_stack = []
            return
        if len(self.tag_stack) == 0:
            return
        if tag == 'a' and self.tag_stack[-1] == 'anchor':
            return
        if tag == 'iframe':
            return
        if self.tag_stack[-1] == 'chaptitle':
            if tag == 'h3':
                self._chapter_title = self._item_data
                self.tag_stack.pop()
            return
        if tag not in self.self_closing_tags:
            self._curr_data += '</%s>' % tag

    def handle_data(self, data):
        if len(self.tag_stack) == 0:
            return
        if self.tag_stack[-1] in ['chaptitle']:
            self._item_data += data
        elif self._chapter_title:
            self._curr_data += data

    def handle_entityref(self, name):
	self.handle_data('&%s;' % name)

    def handle_charref(self, name):
	self.handle_data('&#%s;' % name)



class FimFictionEPubGenerator(ePubGenerator):
    site_url = 'http://www.fimfiction.net'
    story_num = ''
    _chapter_title = ''
    _chapter_data = ''

    def __init__(self):
        self.story_num = ''
        self._chapter_title = ''
        self._chapter_data = ''
        ePubGenerator.__init__(self)


    def add_css_file(self):
        outdata = ''
        outdata += 'body {\n'
        outdata += '  margin-left: .5em;\n'
        outdata += '  margin-right: .5em;\n'
        outdata += '  text-align: justify;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'p {\n'
        outdata += '  font-family: serif;\n'
        outdata += '  font-size: 10pt;\n'
        outdata += '  text-align: justify;\n'
        outdata += '  margin-top: 0px;\n'
        outdata += '  margin-bottom: 1ex;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'h1, h2, h3 {\n'
        outdata += '  font-family: sans-serif;\n'
        outdata += '  font-style: italic;\n'
        outdata += '  text-align: center;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'h1, h2 {\n'
        outdata += '  background-color: #6b879c;\n'
        outdata += '  color: white;\n'
        outdata += '  width: 100%;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'h1 {\n'
        outdata += '  margin-bottom: 2px;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'h2 {\n'
        outdata += '  margin-top: -2px;\n'
        outdata += '  margin-bottom: 2px;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'p.double {\n'
        outdata += '  margin-top:1.0em;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'p.indented {\n'
        outdata += '  text-indent:3.0em;\n'
        outdata += '}\n'
        outdata += '\n'
        outdata += 'img {\n'
        outdata += '  max-width: 100%;\n'
        outdata += '  max-height: 100%;\n'
        outdata += '}\n'
        css_file = self.metas['cssfile']
        outdata = bytes(outdata)
        self.add_file(css_file, tagname='css_css1', mimetype='text/css', data=outdata)


    def add_cover_page(self):
        if 'coverimg' not in self.metas:
            return
        outdata = ''
        outdata += '<?xml version="1.0" encoding="utf-8"?>\n'
        outdata += '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n'
        outdata += '\t<head>\n'
        outdata += '\t\t<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n'
        outdata += '\t\t<title>Cover</title>\n'
        outdata += '\t\t<link rel="stylesheet" type="text/css" href="%(cssfile)s" />\n'
        outdata += '\t\t<style type="text/css" title="override_css">\n'
        outdata += '\t\t\t@page {padding: 0pt; margin:0pt}\n'
        outdata += '\t\t\tbody { text-align: center; padding:0pt; margin: 0pt; }\n'
        outdata += '\t\t\tsvg text {text-shadow:0px 0px 3px #ffd; text-anchor:middle}\n'
        outdata += '\t\t</style>\n'
        outdata += '\t</head>\n'
        outdata += '\t<body>\n'
        outdata += '\t\t<div>\n'
        outdata += '\t\t\t<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="100%%" height="100%%" viewBox="0 0 474 751" preserveAspectRatio="xMinyMin">\n'
        outdata += '\t\t\t\t<image width="474" height="751" xlink:href="%(coverimg)s" />\n'
        outdata += '\t\t\t</svg>\n'
        outdata += '\t\t</div>\n'
        outdata += '\t</body>\n'
        outdata += '</html>\n'
        outdata = outdata % self.metas
        outdata = bytes(outdata)
        self.add_file("coverpage.xhtml", title="Cover Art", tagname='coverpage', mimetype='application/xhtml+xml', data=outdata)


    def add_title_page(self):
        outdata = ''
        outdata += '<?xml version="1.0" encoding="UTF-8"?>\n'
        outdata += '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n'
        outdata += '\t<head>\n'
        outdata += '\t\t<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n'
        outdata += '\t\t<title>Title Page</title>\n'
        outdata += '\t\t<link rel="stylesheet" type="text/css" href="%(cssfile)s" />\n'
        outdata += '\t\t<style type="text/css" title="override_css">\n'
        outdata += '\t\t\t@page {padding: 0pt; margin:0pt}\n'
        outdata += '\t\t\tbody { text-align: center; padding:0pt; margin: 0pt; }\n'
        outdata += '\t\t\tdiv.block { text-align: left; margin-top: 20px; }\n'
        outdata += '\t\t</style>\n'
        outdata += '\t</head>\n'
        outdata += '\t<body>\n'
        outdata += '\t\t<h1>%(title)s</h1>\n'
        outdata += '\t\t<h2>by %(author)s</h2>\n'
        outdata += '\t\t<div class="block">Description: <blockquote>%(description)s</blockquote></div>\n'
        outdata += '\t\t<div class="block">Categories: <blockquote>%(categories)s</blockquote></div>\n'
        outdata += '\t\t<div class="block">Characters: <blockquote>%(characters)s</blockquote></div>\n'
        outdata += '\t</body>\n'
        outdata += '</html>\n'
        outdata = outdata % self.metas
        outdata = bytes(outdata)
        self.add_file("titlepage.xhtml", title='Title Page', tagname='titlepage', mimetype='application/xhtml+xml', data=outdata)


    def add_fim_chapter(self, chap_title, data):
        outdata = ''
        outdata += '<?xml version="1.0" encoding="utf-8"?>\n'
        outdata += '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n'
        outdata += '\t<head>\n'
        outdata += '\t\t<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
        outdata += '\t\t<link rel="stylesheet" type="text/css" href="%(cssfile)s" />\n'
        outdata += '\t\t<title>%(title)s</title>\n'
        outdata += '\t</head>\n'
        outdata += '\t<body>\n'
        outdata = outdata % self.metas
        if chap_title:
            outdata += '\t\t<h3>' + chap_title + '</h3><hr />\n'
        outdata += data + '\n'
        outdata += '\t</body>\n'
        outdata += '</html>\n'
        outdata = bytes(outdata)
        return self.add_chapter(chap_title, outdata)


    def _getValue(self, el):
        val = ''
        for child in el.childNodes:
            if child.nodeType == child.TEXT_NODE:
                val += child.data
        return val


    def get_metas_from_fimfiction(self):
        desc_url = '%s/story/%s' % (self.site_url, self.story_num)
        url_pat = r'<link rel="canonical" href="([^"]*)"'
        metapat = r'<meta property="og:([a-z]*)" content="([^"]*)"'
        authpat = r'<span class="author"><a href="/user/[^>]*>([^<]*)<'
        catapat = r'class="story_category.*?>(.*?)</a>'
        charpat = r'class="character_icon.*? title="(.*?)"'
        descpat = r'class="description".*?<hr.*?>(.*?)</div>'
        resp = requests.get(desc_url)

        categories = []
        characters = []
        data = {}
        for m in re.finditer(metapat, resp.text, re.I):
            data[m.group(1)] = m.group(2).strip()
        for m in re.finditer(url_pat, resp.text, re.I):
            data['url'] = m.group(1).strip()
            break
        for m in re.finditer(authpat, resp.text, re.I):
            data['author'] = m.group(1).strip()
            break
        for m in re.finditer(descpat, resp.text, re.I):
            data['description'] = m.group(1).strip()
            break
        for m in re.finditer(catapat, resp.text, re.I):
            categories.append(m.group(1).strip())
        data['categories'] = ', '.join(categories)
        for m in re.finditer(charpat, resp.text, re.I):
            characters.append(m.group(1).strip())
        data['characters'] = ', '.join(characters)

        # Jump through XML hoops to unparse entities.
        xml_parts = ['<item name="%s">%s</item>' % (key, val) for key,val in data.iteritems()]
        xml_str = '<items>' + (''.join(xml_parts)) + '</items>'
        doc = xmlParseString(xml_str)
        els = doc.getElementsByTagName('item')
        out_data = {}
        for el in els:
            key = el.attributes['name'].value
            val = self._getValue(el)
            out_data[key] = val

        tzed = time.strftime("%z")
        created_at = time.strftime("%Y-%m-%dT%H:%M:%S") + tzed[:3] + ':' + tzed[3:]

        for key,val in out_data.iteritems():
            self.set_meta(key, val)

        short_name = re.sub(r'[^a-zA-Z0-9_-]', '', self.metas['title'])
        epub_file = "%s.epub" % short_name

        self.set_meta('url', desc_url)
        self.set_meta('creationdate', created_at)
        self.set_meta('short_name', short_name)
        self.set_meta('epub_file', epub_file)
        self.set_meta('cssfile', 'styles.css')
        return epub_file


    def add_chapters(self):
        """ Get Story Body and Split Into Chapters. """
        body_url = '%s/download_story.php?story=%s&html' % (self.site_url, self.story_num)
        cht_re = re.compile(r'<h3>(.*)</h3>', re.I)
        img_re = re.compile(r'<img ([^>]*)src="([^"]*)"', re.I)

        resp = requests.get(body_url)
        indata = resp.text.encode(resp.encoding)

        bfhp = BodyFileHtmlParser()
        bfhp.set_chapter_cb(self.add_fim_chapter)
        bfhp.set_image_cb(self.add_image)
        bfhp.feed(indata)
        return


    def add_cover_image(self):
        if 'image' in self.metas:
            img_url = self.metas['image']
            filename = self.add_image(img_url, tagname='coverimage')
            self.set_meta('coverimg', filename)


    def handle_url(self, url):
        # If url is a fimfiction URL, get the story number.
        pats = [
            (r'^(http://)?(www[.])?fimfiction[.]net/story/([0-9][0-9]*)(/.*)?$', r'\3'),
            (r'^(http://)?(www[.])?fimfiction[.]net/download_(story|epub).php\?story=([0-9][0-9]*)(&.*)?$', r'\4')
        ]
        for pat,pos in pats:
            if re.match(pat, url):
                self.story_num = re.sub(pat, pos, url)
                return True
        return False


    def gen_epub(self):
        epub_file = self.get_metas_from_fimfiction()
        self.add_cover_image()
        self.add_cover_page()
        self.add_title_page()
        self.add_css_file()
        self.add_chapters()
        return (epub_file, self.finish())



