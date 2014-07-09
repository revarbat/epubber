import os, sys
import unicodedata

from StringIO import StringIO
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint


reload(sys)
sys.setdefaultencoding('utf-8')


class FixTagsHtmlParser(HTMLParser):
    out_f = None
    strip_js = False
    strip_style = False
    strip_doctype = False
    strip_comments = False

    span_tags = [
        'a', 'b', 'big', 'center', 'cite', 'code',
        'em', 'font', 'i', 'pre', 'q', 's', 'samp', 'small',
        'span', 'strike', 'strong', 'sub', 'sup', 'u'
    ]
    paragraph_tags = [ 'div', 'p', 'blockquote', 'head', 'body', 'html' ]
    singular_tags = [ 'br', 'hr', 'img', 'meta', 'link', 'input' ]
    safe_entities = [
        ('&', '&amp;'),
        ('"', '&quot;'),
        ("'", '&apos;'),
        ('<', '&lt;'),
        ('>', '&gt;')
    ]

    tag_stack = []
    popped_tags = []
    skip_tag = None

    def __init__(self, outf=None, stripjs=False, stripstyle=False, stripdoctype=False, stripcomments=False):
        self.out_f = outf
        self.strip_js = stripjs
        self.strip_style = stripstyle
        self.strip_doctype = stripdoctype
        self.strip_comments = stripcomments
        HTMLParser.__init__(self)


    def _esc(self, s):
        for ch,ent in self.safe_entities:
            s = s.replace(ch,ent)
        return s


    def _dump(self, tag):
        out = '\n'
        out += 'tag=<%s>\n' % tag
        out += 'stack=['
        out += ', '.join(["'<%s>'" % (t,) for t,b in self.tag_stack])
        out += ']\n'
        out += 'popped=['
        out += ', '.join(["'<%s>'" % (t,) for t,b in self.popped_tags])
        out += ']\n'
        return out


    def _attrstr(self,attrs):
        out = ''
        for key,val in attrs:
            if val is None:
                out += ' %s"' % key
            else:
                out += ' %s="%s"' % (key,self._esc(val))
        return out


    def start(self):
        self.tag_stack = []
        self.popped_tags = []
        self.skip_tag = None


    def fixup_file(self, infilename, outfilename):
        with open(outfilename, 'w') as outf:
            self.out_f = outf
            self.start()
            with open(infilename,'r') as in_f:
                for line in in_f:
                    self.feed(line)


    def fixup_string(self, data):
        self.out_f = StringIO()
        self.start()
        self.feed(data)
        out = self.out_f.getvalue()
        self.out_f.close()
        return out


    def main(self):
        if len(sys.argv) < 2:
            print("Usage: %s FILE [...]" % sys.argv[0])
            sys.exit(-1)
        for filename in sys.argv[1:]:
            o_fn = 'fixed_'+os.path.basename(filename)
            self.fixup_file(filename, o_fn)


    ###################################################
    # Parser calls follow
    ###################################################
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if not self.skip_tag:
            if self.strip_js and tag == 'script':
                self.skip_tag = 'script'
            elif self.strip_style and tag == 'style':
                self.skip_tag = 'script'
            elif tag in self.singular_tags:
                attrstr = self._attrstr(attrs)
                self.out_f.write("<%s%s />" % (tag, attrstr))
            else:
                if tag in self.paragraph_tags:
                    found = False
                    for stag,sbody in reversed(self.tag_stack):
                        if stag == tag:
                            found = True
                            break
                    if found:
                        self.handle_endtag(tag)
                attrstr = self._attrstr(attrs)
                self.tag_stack.append( (tag, attrstr) )
                self.out_f.write("<%s%s>" % (tag, attrstr))
                if tag in self.paragraph_tags:
                    while self.popped_tags:
                        poptag,popbody = self.popped_tags.pop()
                        self.tag_stack.append( (poptag, popbody) )
                        self.out_f.write("<%s%s>" % (poptag, popbody))


    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == self.skip_tag:
            self.skip_tag = None
        elif not self.skip_tag:
            if tag in self.singular_tags:
                return
            found = False
            for stag,sbody in reversed(self.popped_tags):
                if stag == tag:
                    found = True
                    break
            if found:
                while self.popped_tags:
                    poptag,popbody = self.popped_tags.pop()
                    #self.out_f.write("</%s>" % poptag)
                    if poptag == tag:
                        break
            else:
                found = False
                for stag,sbody in reversed(self.tag_stack):
                    if stag == tag:
                        found = True
                        break
                if found:
                    while self.tag_stack:
                        poptag,popbody = self.tag_stack.pop()
                        self.out_f.write("</%s>" % poptag)
                        if poptag == tag:
                            break
                        if poptag in self.span_tags:
                            self.popped_tags.append( (poptag, popbody) )


    def handle_data(self, data):
        if not self.skip_tag:
            if data.strip():
                while self.popped_tags:
                    poptag,popbody = self.popped_tags.pop()
                    self.tag_stack.append( (poptag, popbody) )
                    self.out_f.write("<%s%s>" % (poptag, popbody))
            #data = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', r'', data)
            data = ''.join(ch for ch in unicode(data) if unicodedata.category(ch)[0]!="C" or ch=='\n' or ch=='\t' or ch=='\r')
            self.out_f.write(data)


    def handle_comment(self, data):
        if not self.strip_comments:
            self.out_f.write('<!--%s-->' % data)


    def handle_entityref(self, name):
        #c = unichr(name2codepoint[name])
        while self.popped_tags:
            poptag,popbody = self.popped_tags.pop()
            self.tag_stack.append( (poptag, popbody) )
            self.out_f.write("<%s%s>" % (poptag, popbody))
        if name in ['amp', 'quot', 'apos', 'lt', 'gt']:
            self.out_f.write('&%s;' % name)
        else:
            chnum = name2codepoint[name]
            if not self.skip_tag:
                if chnum >= 32:
                    self.out_f.write("&#%d;" % chnum)


    def handle_charref(self, name):
        while self.popped_tags:
            poptag,popbody = self.popped_tags.pop()
            self.tag_stack.append( (poptag, popbody) )
            self.out_f.write("<%s%s>" % (poptag, popbody))
        if name.startswith('x'):
            chnum = int(name[1:], 16)
        else:
            chnum = int(name)
        if not self.skip_tag:
            if chnum >= 32:
                self.out_f.write("&#%d;" % chnum)


    def handle_decl(self, data):
        if not self.strip_doctype:
            self.out_f.write("<!%s>" % data)


if __name__ == '__main__':
    FixTagsHtmlParser().main()



# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 nowrap

