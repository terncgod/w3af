'''
dot_listing.py

Copyright 2012 Tomas Velazquez

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

import core.controllers.outputManager as om
import core.data.kb.knowledge_base as kb
import core.data.kb.vuln as vuln
import core.data.constants.severity as severity

from core.controllers.plugins.crawl_plugin import CrawlPlugin
from core.controllers.w3afException import w3afException
from core.controllers.core_helpers.fingerprint_404 import is_404
from core.data.bloomfilter.bloomfilter import scalable_bloomfilter


class dot_listing(CrawlPlugin):
    '''
    Search for .listing files and extracts new filenames from it.
    @author: Tomas Velazquez ( tomas.velazquezz@gmail.com )
    '''
    
    def __init__(self):
        CrawlPlugin.__init__(self)
        
        # Internal variables
        self._analyzed_dirs = scalable_bloomfilter()
        
        # -rw-r--r--    1 andresr   w3af         8139 Apr 12 13:23 foo.zip
        regex_str = '[a-z-]{10}\s*\d+\s*(.*?)\s+(.*?)\s+\d+\s+\w+\s+\d+\s+[0-9:]{4,5}\s+(.*)'
        self._listing_parser_re = re.compile(regex_str)

    def crawl(self, fuzzable_request):
        '''
        For every directory, fetch the .listing file and analyze the response.
        
        @parameter fuzzable_request: A fuzzable_request instance that contains
                                    (among other things) the URL to test.
        '''
        for domain_path in fuzzable_request.getURL().getDirectories():
            if domain_path not in self._analyzed_dirs:
                self._analyzed_dirs.add( domain_path )
                self._check_and_analyze( domain_path )

    def _check_and_analyze(self, domain_path):
        '''
        Check if a .listing filename exists in the domain_path.
        @return: None, everything is saved to the self.out_queue.
        '''
        # Request the file
        url = domain_path.urlJoin( '.listing' )
        try:
            response = self._uri_opener.GET( url, cache=True )
        except w3afException,  w3:
            msg = ('Failed to GET .listing file: "%s". Exception: "%s".')
            om.out.debug( msg % (url, w3) )
        else:
            # Check if it's a .listing file
            if not is_404( response ):
                
                for fr in self._create_fuzzable_requests( response ):
                    self.output_queue.put(fr)
                
                parsed_url_set = set()
                users = set()
                groups = set()
                
                for username, group, filename in self._extract_info_from_listing(response.getBody()):
                    if filename != '.' and filename != '..':
                        parsed_url_set.add( domain_path.urlJoin( filename ) )
                        users.add(username)
                        groups.add(group)
                        
                self._tm.threadpool.map(self._get_and_parse, parsed_url_set)
                
                if parsed_url_set:
                    v = vuln.vuln()
                    v.setPluginName(self.get_name())
                    v.set_id( response.id )
                    v.set_name( '.listing file found' )
                    v.setSeverity(severity.LOW)
                    v.setURL( response.getURL() )
                    msg = ('A .listing file was found at: "%s". The contents'
                           ' of this file disclose filenames.')
                    v.set_desc( msg % (v.getURL()) )
                    kb.kb.append( self, 'dot_listing', v )
                    om.out.vulnerability( v.get_desc(), severity=v.getSeverity() )
                
                real_users = set([u for u in users if not u.isdigit()])
                real_groups = set([g for g in groups if not g.isdigit()])
                
                if real_users or real_groups:
                    v = vuln.vuln()
                    v.setPluginName(self.get_name())
                    v.set_id( response.id )
                    v.set_name( 'Operating system username and group leak' )
                    v.setSeverity(severity.LOW)
                    v.setURL( response.getURL() )
                    msg = 'A .listing file which leaks operating system usernames' \
                          ' and groups was identified at %s. The leaked users are %s,' \
                          ' and the groups are %s. This information can be used' \
                          ' during a bruteforce attack to the Web application,' \
                          ' SSH or FTP services.'
                    v.set_desc( msg % (v.getURL(), ', '.join(real_users), ', '.join(real_groups)) )
                    kb.kb.append( self, 'dot_listing', v )
                    om.out.vulnerability( v.get_desc(), severity=v.getSeverity() )
                    

    def _extract_info_from_listing(self, listing_file_content):
        '''
        Extract info from .listing file content, each line looks like:
        
        -rw-r--r--    1 andresr   w3af         8139 Apr 12 13:23 foo.zip
        
        We're going to extract "andresr" (user), "w3af" (group) and "foo.zip"
        (file).
        
        @return: A list with the information extracted from the listing_file_content
        '''
        for user, group, filename in self._listing_parser_re.findall( listing_file_content ):
            yield user, group, filename.strip()
        
    def _get_and_parse(self, url):
        '''
        GET a URL that was found in the .listing file, and parse it.
        
        @parameter url: The URL to GET.
        @return: None, everything is saved to self.out_queue.
        '''
        try:
            http_response = self._uri_opener.GET( url, cache=True )
        except w3afException, w3:
            msg = ('w3afException while fetching page in crawl.dot_listing, error: "%s".')
            om.out.debug( msg, (w3) )
        else:
            if not is_404( http_response ):
                for fr in self._create_fuzzable_requests( http_response ):
                    self.output_queue.put(fr)

    def get_long_desc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin searches for the .listing file in all the directories and
        subdirectories that are sent as input and if found it will try to
        discover new URLs from its content. The .listing file holds information
        about the list of files in the current directory. These files are created 
        when download files from FTP with command "wget" and argument "-m" or 
        "--no-remove-listing". For example, if the input is:
            - http://host.tld/w3af/index.php
            
        The plugin will perform these requests:
            - http://host.tld/w3af/.listing
            - http://host.tld/.listing
        
        '''

