'''
symfony.py

Copyright 2011 Andres Riancho and Carlos Pantelides

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

import re

import core.data.kb.knowledge_base as kb
import core.data.kb.info as info

from core.data.options.opt_factory import opt_factory
from core.data.options.option_list import OptionList
from core.data.bloomfilter.bloomfilter import scalable_bloomfilter
from core.controllers.plugins.grep_plugin import GrepPlugin


class symfony(GrepPlugin):
    '''
    Grep every page for traces of the Symfony framework.
      
    @author: Carlos Pantelides (carlos.pantelides@yahoo.com ) based upon 
    work by Andres Riancho (andres.riancho@gmail.com) and help from
    Pablo Mouzo (pablomouzo@gmail.com)
    '''
    
    def __init__(self):
        GrepPlugin.__init__(self)
        
        # Internal variables
        self._already_inspected = scalable_bloomfilter()
        self._override = False
        
    def grep(self, request, response):
        '''
        Plugin entry point.
        
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None, all results are saved in the kb.
        '''
        url = response.getURL()
        if response.is_text_or_html() and url not in self._already_inspected:
            
            # Don't repeat URLs
            self._already_inspected.add(url)

            if self.symfonyDetected(response):
                dom = response.getDOM()
                if dom is not None and not self.csrfDetected(dom):
                    i = info.info()
                    i.setPluginName(self.get_name())
                    i.set_name('Symfony Framework')
                    i.setURL(url)
                    i.set_desc('The URL: "%s" seems to be generated by the '
                      'Symfony framework and contains a form that perhaps '
                      'has CSRF protection disabled.' % url)
                    i.set_id(response.id)
                    kb.kb.append(self, 'symfony', i)

    def symfonyDetected(self, response):
        if self._override:
            return True
        for header_name in response.getHeaders().keys():
            if header_name.lower() == 'set-cookie' or header_name.lower() == 'cookie':
                if re.match('^symfony=', response.getHeaders()[header_name]):
                    return True
        return False      
    
    def csrfDetected(self, dom):
        forms = dom.xpath('//form')
        if forms:
            csrf_protection_regex_string = '.*csrf_token'
            csrf_protection_regex_re = re.compile( csrf_protection_regex_string, re.IGNORECASE )
            for form in forms:
                inputs = form.xpath('//input[@id]')
                if inputs:
                    for _input in inputs:
                        if csrf_protection_regex_re.search(_input.attrib["id"]):
                            return True
        return False

    def set_options( self, options_list ):
        self._override = options_list['override'].get_value()
    
    def get_options( self ):
        '''
        @return: A list of option objects for this plugin.
        '''
        ol = OptionList()
        
        d = 'Skip symfony detection and search for the csrf (mis)protection.'
        o = opt_factory('override', self._override, d, 'boolean')
        ol.add(o)
        
        return ol
        
        
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self.print_uniq( kb.kb.get( 'symfony', 'symfony' ), 'URL' )

    def get_long_desc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin greps every page for traces of the Symfony framework and the
        lack of CSRF protection.
        '''
