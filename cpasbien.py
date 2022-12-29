# -*- coding: utf-8 -*-
# VERSION: 1.1
# AUTHOR: Davy39 <davy39@hmamail.com>
# CONTRIBUTORS: Simon <simon@brulhart.me>

# Copyleft


from __future__ import print_function

import re
# python3
from html.parser import HTMLParser
import os
try:
    import requests
except:
    os.system("pip install requests")
    import requests

from helpers import download_file, retrieve_url
from novaprinter import prettyPrinter



class cpasbien(object):
    url = "http://www.cpasbien.si"
    name = "Cpasbien (french)"
    supported_categories = {
        "all": [""],
        "books": ["ebook/"],
        "movies": ["films/"],
        "tv": ["series/"],
        "music": ["musique/"],
        "software": ["logiciels/"],
        "games": ["jeux-pc/", "jeux-consoles/"]
    }

    def __init__(self):
        self.results = []
        self.parser = self.SimpleHTMLParser(self.results, self.url)

    def download_torrent(self, url):
        print(download_file(url))

    class TableRowExtractor(HTMLParser):
        def __init__(self, url, results):
            self.results = results
            self.map_name = {'titre': 'name', 'poid': 'size', 'up': 'seeds', 'down': 'leech'}
            self.in_tr = False
            self.in_table_corps = False
            self.in_div_or_anchor = False
            self.current_row = {}
            self.url = url
            super().__init__()

        def handle_starttag(self, tag, attrs):
            if tag == 'table':
                # check if the table has a class of "table-corps"
                attrs = dict(attrs)
                if attrs.get('class') == 'table-corps':
                    self.in_table_corps = True

            if self.in_table_corps and tag == 'tr':
                self.in_tr = True

            if self.in_tr and tag in ['div', 'a']:

                # extract the class name of the div element if it exists
                self.in_div_or_anchor = True
                attrs = dict(attrs)
                self.current_div_class = self.map_name.get(attrs.get('class', None), None)
                if tag == 'a' and self.current_div_class == 'name':
                    self.current_row['link'] = self.url + attrs['href']
                    self.current_row["desc_link"] = self.url + attrs['href']
                    self.current_row["engine_url"] = self.url

        def handle_endtag(self, tag):
            if tag == 'tr':
                self.in_tr = False
                if self.current_row['desc_link'] not in self.results:
                    r = requests.get(self.current_row['desc_link'])
                    content =  r.content.decode()
                    link = self.url + re.findall("<a href='(\/get_torrents\/.*?)'>", content)[0]
                    self.current_row['link'] = link
                    self.results.append(self.current_row['desc_link'])
                    prettyPrinter(self.current_row)
                self.current_row = {}
            if tag == 'table':
                self.in_table_corps = False
            if tag in ['div', 'a']:
                self.in_div_or_anchor = False

        def handle_data(self, data):
            if self.in_div_or_anchor and self.current_div_class:
                self.current_row[self.current_div_class] = data

        def get_rows(self):
            return self.results

    class SimpleHTMLParser(HTMLParser):
        def __init__(self, results, url, *args):
            HTMLParser.__init__(self)
            self.url = url
            self.div_counter = None
            self.current_item = None
            self.results = results

        def handle_starttag(self, tag, attr):
            method = 'start_' + tag
            if hasattr(self, method) and tag in ('a', 'div'):
                getattr(self, method)(attr)

        def start_a(self, attr):
            params = dict(attr)
            if params.get('href', '').startswith(self.url + '/dl-torrent/'):
                self.current_item = {}
                self.div_counter = 0
                self.current_item["desc_link"] = params["href"]
                fname = params["href"].split('/')[-1]
                fname = re.sub(r'\.html$', '.torrent', fname, flags=re.IGNORECASE)
                self.current_item["link"] = self.url + '/telechargement/' + fname

        def start_div(self, attr):
            if self.div_counter is not None:
                self.div_counter += 1
                # Abort if div class does not match
                div_classes = {1: 'poid', 2: 'up', 3: 'down'}
                attr = dict(attr)
                if div_classes[self.div_counter] not in attr.get('class', ''):
                    self.div_counter = None
                    self.current_item = None

        def handle_data(self, data):
            data = data.strip()
            if data:
                if self.div_counter == 0:
                    self.current_item['name'] = data
                elif self.div_counter == 1:
                    self.current_item['size'] = unit_fr2en(data)
                elif self.div_counter == 2:
                    self.current_item['seeds'] = data
                elif self.div_counter == 3:
                    self.current_item['leech'] = data
            # End of current_item, final validation:

            if self.div_counter == 3:
                required_keys = ('name', 'size')
                if any(key in self.current_item for key in required_keys):
                    self.current_item['engine_url'] = self.url
                    prettyPrinter(self.current_item)
                    self.results.append("a")
                else:
                    pass
                self.current_item = None
                self.div_counter = None

    def search(self, what, cat="all"):
        results = []
        for page in range(10):
            # parser = self.SimpleHTMLParser(results, self.url)
            parser = self.TableRowExtractor(self.url, results)
            for subcat in self.supported_categories[cat]:
                url = f"{self.url}/recherche/{what}/{page*50 +1}"
                data = retrieve_url(url)
                parser.feed(data)
            # print(parser.rows)
            parser.close()
            results = parser.results
            print(len(results))
            if len(results) <= 0:
                break



def unit_fr2en(size):
    """Convert french size unit to english"""
    return re.sub(
        r'([KMGTP])o',
        lambda match: match.group(1) + 'B',
        size, flags=re.IGNORECASE
    )
