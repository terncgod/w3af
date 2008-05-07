'''
craftedRequests.py

Copyright 2007 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import pygtk, gtk
import core.ui.gtkUi.reqResViewer as reqResViewer
import core.ui.gtkUi.helpers as helpers
import core.ui.gtkUi.entries as entries
import core.ui.gtkUi.fuzzygen as fuzzygen
from core.controllers.w3afException import w3afException

request_example = """\
GET http://www.some_host.com/path HTTP/1.0
Host: www.some_host.com
User-Agent: w3af.sf.net
Pragma: no-cache
Content-Type: application/x-www-form-urlencoded
"""

class ManualRequests(entries.RememberingWindow):
    '''Infrastructure to generate manual HTTP requests.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, w3af):
        super(ManualRequests,self).__init__(w3af, "manualreq", "w3af - Manual Requests")
        self.w3af = w3af

        # send button
        hbox = gtk.HBox()
        b = gtk.Button("   Send   ")
        b.connect("clicked", self._send)
        hbox.pack_start(b, True, False)

        # request-response viewer
        self.reqresp = reqResViewer.reqResViewer([b])
        self.reqresp.response.notebook.set_sensitive(False)
        self.vbox.pack_start(self.reqresp, True, True)

        self.vbox.pack_start(hbox, False, False, padding=10)
        
        # Add a default request
        self.reqresp.request.rawShow(request_example, '')
        
        # Show all!
        self.show_all()

    def _send(self, widg):
        '''Actually generates the manual requests.

        @param widget: who sent the signal.
        '''
        (tsup, tlow) = self.reqresp.request.getBothTexts()

        try:
            httpResp = helpers.coreWrap(self.w3af.uriOpener.sendRawRequest, tsup, tlow)
        except w3afException:
            self.reqresp.response.clearPanes()
            self.reqresp.response.notebook.set_sensitive(False)
            return

        # get the info
        body = httpResp.getBody()
        headers = httpResp.dumpResponseHead()

        # activate and show
        self.reqresp.response.notebook.set_sensitive(True)
        self.reqresp.response.rawShow(headers, body)


class PreviewWindow(entries.RememberingWindow):
    '''A window with the analysis preview.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, w3af, parent, pages):
        super(PreviewWindow,self).__init__(w3af, "fuzzypreview", "Preview")
        self.pages = pages
        self.set_modal(True)
        self.set_transient_for(parent) 

        # content
        self.panes = reqResViewer.requestPaned()
        self.vbox.pack_start(self.panes.notebook)

        # the ok button
        centerbox = gtk.HBox()
        self.pagesControl = entries.PagesControl(w3af, self._pageChange, len(pages))
        centerbox.pack_start(self.pagesControl, True, False) 
        self.vbox.pack_start(centerbox, False, False, padding=5)

        self._pageChange(0)
        self.show_all()

    def _pageChange(self, page):
        (txtup, txtdn) = self.pages[page]
        self.panes.rawShow(txtup, txtdn)



FUZZYHELP = """\
"$" is the delimiter
Use "$$" to include a "$"
"$something$" will eval "something" 
Already imported:
    the "string" module
    the "xx" function
"""

class FuzzyRequests(entries.RememberingWindow):
    '''Infrastructure to generate fuzzy HTTP requests.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, w3af):
        super(FuzzyRequests,self).__init__(w3af, "fuzzyreq", "w3af - Fuzzy Requests")
        self.w3af = w3af
        mainhbox = gtk.HBox()

        # ---- left pane ----
        vbox = gtk.VBox()
        mainhbox.pack_start(vbox, padding=10)

        # we create the buttons first, to pass them
        analyzBut = gtk.Button("Analyze")
        sendBut = gtk.Button("Send all")

        # request and help
        self.originalReq = reqResViewer.requestPaned([analyzBut, sendBut])
        self.originalReq.rawShow(request_example, '')
        self.originalReq.notebook.append_page(gtk.Label(FUZZYHELP), gtk.Label("Syntax help"))
        vbox.pack_start(self.originalReq.notebook, True, True, padding=5)

        # the commands
        t = gtk.Table(2, 3)
        analyzBut.connect("clicked", self._analyze)
        t.attach(analyzBut, 0, 1, 0, 1)
        self.analyzefb = gtk.Label("? requests")
        t.attach(self.analyzefb, 1, 2, 0, 1)
        self.preview = gtk.CheckButton("preview")
        t.attach(self.preview, 2, 3, 0, 1)
        sendBut.connect("clicked", self._send)
        t.attach(sendBut, 0, 1, 1, 2)
        self.sendfb = gtk.Label("? ok, ? errors")
        t.attach(self.sendfb, 1, 2, 1, 2)
        vbox.pack_start(t, False, False, padding=5)

        # ---- right pane ----
        vbox = gtk.VBox()
        mainhbox.pack_start(vbox, padding=10)

        # result itself
        self.resultReqResp = reqResViewer.reqResViewer()
        self.resultReqResp.set_sensitive(False)
        vbox.pack_start(self.resultReqResp, True, True, padding=5)

        # result control
        centerbox = gtk.HBox()
        self.pagesControl = entries.PagesControl(w3af, self._pageChange)
        centerbox.pack_start(self.pagesControl, True, False) 
        vbox.pack_start(centerbox, False, False, padding=5)

        # Show all!
        self.vbox.pack_start(mainhbox)
        self.show_all()

    def _analyze(self, widg):
        '''Handles the Analyze part.'''
        (request, postbody) = self.originalReq.getBothTexts()
        try:
            fg = helpers.coreWrap(fuzzygen.FuzzyGenerator, request, postbody)
        except fuzzygen.FuzzyError:
            return
            
        # 
        preview = list(fg.generate())
        self.analyzefb.set_text("%d requests" % len(preview))

        # raise the window only if preview is active
        if self.preview.get_active():
            PreviewWindow(self.w3af, self, preview)


    def _send(self, widg):
        '''Sends the requests.'''
        (request, postbody) = self.originalReq.getBothTexts()
        try:
            fg = helpers.coreWrap(fuzzygen.FuzzyGenerator, request, postbody)
        except fuzzygen.FuzzyError:
            return
            
        # let's send the requests!
        self.responses = []
        result_ok = 0
        result_err = 0
        for (realreq, realbody) in fg.generate():
            try:
                httpResp = self.w3af.uriOpener.sendRawRequest(realreq, realbody)
                respbody = httpResp.getBody()
                resphead = httpResp.dumpResponseHead()
                result_ok += 1
            except w3afException, e:
                respbody = str(e)
                resphead = None
                result_err += 1
            self.responses.append((realreq, realbody, respbody, resphead))
            self.sendfb.set_text("%d ok, %d errors" % (result_ok, result_err))

        # activate and show
        self.resultReqResp.set_sensitive(True)
        self.pagesControl.activate(len(self.responses))
        self._pageChange(0)

    def _pageChange(self, page):
        (realreq, realbody, respbody, resphead) = self.responses[page]

        self.resultReqResp.request.rawShow(realreq, realbody)
        if resphead is not None:
            self.resultReqResp.response.rawShow(respbody, resphead)
        else:
            self.resultReqResp.response.showError(respbody)
