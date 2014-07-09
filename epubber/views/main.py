from __future__ import absolute_import

import re, os, sys

from clay import app
import clay.config
from flask import make_response, request, redirect, render_template, url_for

from epubber.fimfic_epubgen import FimFictionEPubGenerator


site_epub_classes = [
    FimFictionEPubGenerator
]


accesslog = clay.config.get_logger('epubber_access')


#####################################################################
# Main App Views Section
#####################################################################

@app.route('/', methods=['GET', 'POST'])
def main_view():
    story = request.args.get("story") or None
    if story:
        data = None
        for epgenclass in site_epub_classes:
            epgen = epgenclass()
            if epgen.handle_url(story):
                epub_file,data = epgen.gen_epub()
                accesslog.info('%(title)s - %(url)s' % epgen.metas)
                del epgen
                response = make_response(data)
                response.headers["Content-Type"] = "application/epub+zip"
                response.headers["Content-Disposition"] = "attachment; filename=%s" % epub_file
                return response
            del epgen
        return ("Cannot generate epub for this URL.", 400)

    return render_template("main.html")



#####################################################################
# Secondary Views Section
#####################################################################

@app.route('/health', methods=['GET'])
def health_view():
    '''
    Heartbeat view, because why not?
    '''
    return ('OK', 200)



#####################################################################
# URL Shortener Views Section
#####################################################################

@app.route('/img/<path>', methods=['GET', 'POST'])
def static_img_proxy_view(path):
    '''
    Make shorter URLs for image files.
    '''
    path = re.sub(r'[^A-Za-z0-9_.-]', r'_', path)
    thefile = os.path.join('img', path)
    return redirect(url_for('static', filename=thefile))


@app.route('/js/<path>', methods=['GET', 'POST'])
def static_js_proxy_view(path):
    '''
    Make shorter URLs for javascript files.
    '''
    path = re.sub(r'[^A-Za-z0-9_+.-]', r'_', path)
    thefile = os.path.join('js', path)
    return redirect(url_for('static', filename=thefile))


@app.route('/css/<path>', methods=['GET', 'POST'])
def static_css_proxy_view(path):
    '''
    Make shorter URLs for CSS files.
    '''
    path = re.sub(r'[^A-Za-z0-9_+.-]', r'_', path)
    thefile = os.path.join('css', path)
    return redirect(url_for('static', filename=thefile))



#####################################################################
# Main
#####################################################################

def main():
    # Make templates copacetic with UTF8
    reload(sys)
    sys.setdefaultencoding('utf-8')

    # App Config
    app.secret_key = clay.config.get('flask.secret_key')



main()



# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 nowrap

