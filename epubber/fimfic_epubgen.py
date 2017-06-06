from __future__ import absolute_import

import sys, re, time, cgi
import requests
import urlparse
import textwrap

import clay.config
from HTMLParser import HTMLParser

from epubber.fixtags import FixTagsHtmlParser
from epubber.epubgen import ePubGenerator
 
reload(sys)
sys.setdefaultencoding('utf-8')


errorlog = clay.config.get_logger('epubber_error')


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
        outdata = textwrap.dedent("""\
            body {
              margin-left: .5em;
              margin-right: .5em;
              text-align: justify;
            }
            
            p {
              font-family: serif;
              font-size: 10pt;
              text-align: justify;
              margin-top: 0px;
              margin-bottom: 1ex;
            }
            
            h1, h2, h3 {
              font-family: sans-serif;
              font-style: italic;
              text-align: center;
            }
            
            h1, h2 {
              width: 100%;
            }
            
            h1 {
              margin-bottom: 2px;
            }
            
            h2 {
              margin-top: -2px;
              margin-bottom: 20px;
            }
            
            p.double {
              margin-top:1.0em;
            }
            
            p.indented {
              text-indent:3.0em;
            }
            
            img {
              max-width: 100%;
              max-height: 100%;
            }

            .story_category, .story_category_small {
                display: inline-block;
                padding: 8px;
                line-height: 1.0em;
                padding-left: 12px;
                padding-right: 12px;
                color: #555;
                font-family: Calibri, Arial;
                text-decoration: none;
                background-color: #eee;
                border: 1px solid rgba(0, 0, 0, 0.2)
            }

            .story_category_small {
                padding: 4px;
                border-radius: 4px;
                font-size: 0.7em
            }

            .story_category_romance {
                border-color: #5f308f !important;
                background-color: #773db3 !important;
                color: #FFF;
                text-shadow: -1px -1px #5f308f;
                background: #763cb2;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #7c40bb), color-stop(100%, #7139aa));
                background: -webkit-linear-gradient(top, #7c40bb 0%, #7139aa 100%);
                background: linear-gradient(to bottom, #7c40bb 0%, #7139aa 100%);
                box-shadow: 0px 1px 0px #9a4fe8 inset
            }

            .story_category_dark {
                border-color: #791c1c !important;
                background-color: #982323 !important;
                color: #FFF;
                text-shadow: -1px -1px #791c1c;
                background: #972222;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #9f2424), color-stop(100%, #902121));
                background: -webkit-linear-gradient(top, #9f2424 0%, #902121 100%);
                background: linear-gradient(to bottom, #9f2424 0%, #902121 100%);
                box-shadow: 0px 1px 0px #c52d2d inset
            }

            .story_category_sad {
                border-color: #ad4b6c !important;
                background-color: #d95e87 !important;
                color: #FFF;
                text-shadow: -1px -1px #ad4b6c;
                background: #d85d86;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #e3628d), color-stop(100%, #ce5980));
                background: -webkit-linear-gradient(top, #e3628d 0%, #ce5980 100%);
                background: linear-gradient(to bottom, #e3628d 0%, #ce5980 100%);
                box-shadow: 0px 1px 0px #ff7aaf inset
            }

            .story_category_tragedy {
                border-color: #b37d22 !important;
                background-color: #e09d2b !important;
                color: #FFF;
                text-shadow: -1px -1px #b37d22;
                background: #df9c2a;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #eba42d), color-stop(100%, #d49528));
                background: -webkit-linear-gradient(top, #eba42d 0%, #d49528 100%);
                background: linear-gradient(to bottom, #eba42d 0%, #d49528 100%);
                box-shadow: 0px 1px 0px #ffcc37 inset
            }

            .story_category_comedy {
                border-color: #a18400 !important;
                background-color: #caa600 !important;
                color: #FFF;
                text-shadow: -1px -1px #a18400;
                background: #c9a500;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #d4ae00), color-stop(100%, #bf9d00));
                background: -webkit-linear-gradient(top, #d4ae00 0%, #bf9d00 100%);
                background: linear-gradient(to bottom, #d4ae00 0%, #bf9d00 100%);
                box-shadow: 0px 1px 0px gold inset
            }

            .story_category_random {
                border-color: #325ca4 !important;
                background-color: #3f74ce !important;
                color: #FFF;
                text-shadow: -1px -1px #325ca4;
                background: #3e73cd;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #4279d8), color-stop(100%, #3b6ec3));
                background: -webkit-linear-gradient(top, #4279d8 0%, #3b6ec3 100%);
                background: linear-gradient(to bottom, #4279d8 0%, #3b6ec3 100%);
                box-shadow: 0px 1px 0px #5196ff inset
            }

            .story_category_slice_of_life {
                border-color: #323aa5 !important;
                background-color: #3f49cf !important;
                color: #FFF;
                text-shadow: -1px -1px #323aa5;
                background: #3e48ce;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #424cd9), color-stop(100%, #3b45c4));
                background: -webkit-linear-gradient(top, #424cd9 0%, #3b45c4 100%);
                background: linear-gradient(to bottom, #424cd9 0%, #3b45c4 100%);
                box-shadow: 0px 1px 0px #515eff inset
            }

            .story_category_adventure {
                border-color: #37a040 !important;
                background-color: #45c950 !important;
                color: #FFF;
                text-shadow: -1px -1px #37a040;
                background: #44c850;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #48d354), color-stop(100%, #41be4c));
                background: -webkit-linear-gradient(top, #48d354 0%, #41be4c 100%);
                background: linear-gradient(to bottom, #48d354 0%, #41be4c 100%);
                box-shadow: 0px 1px 0px #59ff68 inset
            }

            .story_category_alternate_universe {
                border-color: #6c6c6c !important;
                background-color: #888 !important;
                color: #FFF;
                text-shadow: -1px -1px #6c6c6c;
                background: #878787;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #8e8e8e), color-stop(100%, #818181));
                background: -webkit-linear-gradient(top, #8e8e8e 0%, #818181 100%);
                background: linear-gradient(to bottom, #8e8e8e 0%, #818181 100%);
                box-shadow: 0px 1px 0px #b0b0b0 inset
            }

            .story_category_crossover {
                border-color: #389380 !important;
                background-color: #47b8a0 !important;
                color: #FFF;
                text-shadow: -1px -1px #389380;
                background: #46b7a0;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #4ac1a8), color-stop(100%, #43ae98));
                background: -webkit-linear-gradient(top, #4ac1a8 0%, #43ae98 100%);
                background: linear-gradient(to bottom, #4ac1a8 0%, #43ae98 100%);
                box-shadow: 0px 1px 0px #5cefd0 inset
            }

            .story_category_human {
                border-color: #906848 !important;
                background-color: #b5835a !important;
                color: #FFF;
                text-shadow: -1px -1px #906848;
                background: #b48259;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #be895e), color-stop(100%, #ab7c55));
                background: -webkit-linear-gradient(top, #be895e 0%, #ab7c55 100%);
                background: linear-gradient(to bottom, #be895e 0%, #ab7c55 100%);
                box-shadow: 0px 1px 0px #ebaa75 inset
            }

            .story_category_anthro {
                border-color: #905448 !important;
                background-color: #b5695a !important;
                color: #FFF;
                text-shadow: -1px -1px #905448;
                background: #b46859;
                background: -webkit-gradient(linear, left top, left bottom, color-stop(0%, #be6e5e), color-stop(100%, #ab6355));
                background: -webkit-linear-gradient(top, #be6e5e 0%, #ab6355 100%);
                background: linear-gradient(to bottom, #be6e5e 0%, #ab6355 100%);
                box-shadow: 0px 1px 0px #eb8875 inset
            }
        """)
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
        if 'cover_link' in self.metas:
            outdata += '\t\t\t<a href="%(cover_link)s">\n'
        outdata += '\t\t\t\t<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="100%%" height="100%%" viewBox="0 0 800 1200" preserveAspectRatio="xMinyMin">\n'
        outdata += '\t\t\t\t\t<image width="800" height="1200" xlink:href="%(coverimg)s" />\n'
        outdata += '\t\t\t\t</svg>\n'
        if 'cover_link' in self.metas:
            outdata += '\t\t\t</a>\n'
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
        outdata += '\t\t<h1><a href="%(url)s">%(title)s</a></h1>\n'
        outdata += '\t\t<h2>by %(author)s</h2>\n'
        outdata += '\t\t<hr />\n'

        if self.metas['categories']:
            outdata += '\t\t<p class="double">%(categories)s </p>\n'

        outdata += '\t\t<p class="double">%(description)s</p>\n'
        outdata += '\t\t<hr />\n'

        if self.metas['characters']:
            outdata += '\t\t<p class="double">Dramatis Personae: %(characters)s </p>\n'

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
        url_pat = r'<link rel="canonical" href="(.*?)"'
        metapat = r'<meta property="og:([a-z]*)" content="(.*?)"'
        authpat = r'<a href="/user/.*?" >(.*?)</a>.\s*</h1>'
        catapat = r'class="tag-genre" .*?>(.*?)</a>'
        charpat = r'class="tag-character" .*?>(.*?)</a>'
        descpat = r'<span class="description-text bbcode">.\s*(.*?)</span>'
        imglpat = r'<div class="story_container__story_image">.\s*<img data-src=".*?" class="lazy-img" data-lightbox data-fullsize="(.*?)" />'

        resp = None
        cookies = dict(view_mature='true')
        for retry in range(3):
            try:
                resp = requests.get(desc_url,cookies=cookies)
            except requests.exceptions.RequestException, e:
                errorlog.exception('Failed to HTTP GET file at %s' % desc_url)
                break
            if resp.status_code == 200:
                break
            if resp.status_code == 404:
                errorlog.warning('Got 404 on trying to HTTP GET file at %s' % desc_url)
                resp = None
                break
            time.sleep(2*(2**retry))

        if resp is None:
            return None

        fixtags = FixTagsHtmlParser()
        fixtags.strip_js = True

        categories = []
        characters = []
        data = {}
        if resp.status_code == 200:
            # Ensure we use the right encoding.
            indata = resp.text.encode(resp.encoding)

            m = re.search(r'<article .*?>(.*?)</article>', indata, re.I|re.DOTALL)
            articledata = m.group(1)

            # Get some story metadata from header.
            for m in re.finditer(metapat, indata, re.I):
                data[m.group(1)] = m.group(2).strip()

            # Get the story categories.
            for m in re.finditer(catapat, articledata, re.I|re.DOTALL):
                categories.append('<span class="story_category">%s</span>' % (m.group(1).strip()))

            # Get the characters listed for the story.
            for m in re.finditer(charpat, articledata, re.I|re.DOTALL):
                characters.append(m.group(1).strip())

            # Get the official story URL.
            m = re.search(url_pat, indata, re.I|re.DOTALL)
            if m:
                data['url'] = m.group(1).strip()

            # Get the story author.
            m = re.search(authpat, indata, re.I|re.DOTALL)
            if m:
                data['author'] = m.group(1).strip()

            # Get the long version of the story description, if possible.
            m = re.search(descpat, articledata, re.I|re.DOTALL)
            if m:
                descr = u'<p class="double">'+m.group(1).strip()
                descr = fixtags.fixup_string(descr).strip()
                if descr:
                    data['long_descr'] = descr

            # Get the hyperlink for the cover art, if any.
            m = re.search(imglpat, indata, re.I|re.DOTALL)
            if m:
                link_url = urlparse.urljoin(desc_url, m.group(1).strip())
                data['cover_link'] = link_url

        data['categories'] = ' '.join(categories)
        data['characters'] = ', '.join(characters)

        tzed = time.strftime("%z")
        created_at = time.strftime("%Y-%m-%dT%H:%M:%S") + tzed[:3] + ':' + tzed[3:]

        short_name = re.sub(r'&[^;]*;', '', data['title'])
        short_name = re.sub(r'[^a-zA-Z0-9_-]', '', short_name)
        epub_file = "%s.epub" % short_name

        for key,val in data.iteritems():
            self.set_meta(key, val)

        self.set_meta('url', desc_url)
        self.set_meta('creationdate', created_at)
        self.set_meta('short_name', short_name)
        self.set_meta('epub_file', epub_file)
        self.set_meta('cssfile', 'styles.css')

        errorlog.debug(str(self.metas))

        return epub_file


    def add_chapters(self):
        """ Get Story Body and Split Into Chapters. """
        body_url = '%s/story/download/%s/html' % (self.site_url, self.story_num)
        cht_re = re.compile(r'<h3>(.*)</h3>', re.I)
        img_re = re.compile(r'<img ([^>]*)src="([^"]*)"', re.I)

        resp = None
        cookies = dict(view_mature='true')
        for retry in range(3):
            try:
                resp = requests.get(body_url, cookies=cookies)
            except requests.exceptions.RequestException, e:
                errorlog.exception('Failed to HTTP GET file at %s' % body_url)
                break
            if resp.status_code == 200:
                break
            if resp.status_code == 404:
                errorlog.warning('Got 404 on trying to HTTP GET file at %s' % body_url)
                resp = None
                break
            time.sleep(2*(2**retry))

        if resp is None:
            return

        if resp.status_code == 200:
            indata = resp.text.encode(resp.encoding)
            bfhp = BodyFileHtmlParser()
            bfhp.set_chapter_cb(self.add_fim_chapter)
            bfhp.set_image_cb(self.add_inline_image)
            bfhp.feed(indata)


    def add_cover_image(self):
        if 'image' in self.metas:
            base_url = self.metas['url']
            img_url = urlparse.urljoin(base_url, self.metas['image'])
            filename = self.add_image(img_url, tagname='coverimage')
            self.set_meta('coverimg', filename)


    def add_inline_image(self, url):
        url = urlparse.urljoin(self.metas['url'], url)
        return self.add_image(url)


    def handle_url(self, url):
        # If url is a fimfiction URL, get the story number.
        pats = [
            (r'^(https?://)?(www[.])?fimfiction[.]net/story/([0-9][0-9]*)(/.*)?$', r'\3'),
            (r'^(https?://)?(www[.])?fimfiction[.]net/download_(story|epub).php\?story=([0-9][0-9]*)(&.*)?$', r'\4')
        ]
        for pat,pos in pats:
            if re.match(pat, url):
                self.story_num = re.sub(pat, pos, url)
                return True
        return False


    def gen_epub(self):
        epub_file = self.get_metas_from_fimfiction()
        if epub_file is None:
            return (None, None)

        self.add_cover_image()
        self.add_cover_page()
        self.add_title_page()
        self.add_css_file()
        self.add_chapters()

        return (epub_file, self.finish())



# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 nowrap

