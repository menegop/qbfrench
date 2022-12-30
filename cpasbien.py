# -*- coding: utf-8 -*-
# VERSION: 1.1
# AUTHOR: Davy39 <davy39@hmamail.com>, Paolo M
# CONTRIBUTORS: Simon <simon@brulhart.me>

# Copyleft


from __future__ import print_function
import urllib
import re

from html.parser import HTMLParser

from helpers import retrieve_url, headers
from novaprinter import prettyPrinter
import tempfile
import os
import gzip
import io


class cpasbien(object):
    url = "http://www.cpasbien.si"
    name = "Cpasbien (french)"
    supported_categories = {
        "all": [""]
    }

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
                if self.in_table_corps and 'desc_link' in self.current_row and self.current_row['desc_link'] not in [res['desc_link'] for res in self.results]:
                    self.results.append(self.current_row)
                self.in_tr = False

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

    def download_torrent(self, desc_link):
        """ Download file at url and write it to a file, return the path to the file and the url """
        file, path = tempfile.mkstemp()
        file = os.fdopen(file, "wb")
        # Download url
        req = urllib.request.Request(desc_link, headers=headers)
        try:
            response = urllib.request.urlopen(req)
        except urllib.error.URLError as errno:
            print(" ".join(("Connection error:", str(errno.reason))))
            return ""
        content = response.read().decode()
        link = self.url + re.findall("<a href='(\/get_torrents\/.*?)'>", content)[0]
        req = urllib.request.Request(link, headers=headers)
        response = urllib.request.urlopen(req)
        dat = response.read()
        # Check if it is gzipped
        if dat[:2] == b'\x1f\x8b':
            # Data is gzip encoded, decode it
            compressedstream = io.BytesIO(dat)
            gzipper = gzip.GzipFile(fileobj=compressedstream)
            extracted_data = gzipper.read()
            dat = extracted_data

        # Write it to a file
        file.write(dat)
        file.close()
        # return file path
        print(path + " " + link)

    def search(self, what, cat="all"):
        results = []
        len_old_result = 0
        for page in range(10):
            # parser = self.SimpleHTMLParser(results, self.url)
            url = f"{self.url}/recherche/{what}/{page * 50 + 1}"
            try:
                data = retrieve_url(url)
                parser = self.TableRowExtractor(self.url, results)
                parser.feed(data)
                results = parser.results
                parser.close()
            except:
                break

            if len(results) - len_old_result == 0:
                break
            len_old_result = len(results)
        # Sort results
        good_order = [ord_res for _, ord_res in
                      sorted(zip([[int(res['seeds']), int(res['leech'])] for res in results], range(len(results))))]
        results = [results[x] for x in good_order[::-1]]
        [prettyPrinter(res) for res in results]


