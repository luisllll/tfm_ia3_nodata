from datetime import datetime
import threading
import sys
import os
import pickle
import re

import requests
from bs4 import BeautifulSoup

import numpy as np
import pandas as pd


import textract

# Importa la clase base
from .FomcBase import FomcBase

class FomcPresConfScript(FomcBase):
    '''
    Una clase conveniente para extraer los guiones de las conferencias de prensa del sitio web del FOMC.
    Está disponible solo desde abril de 2011.
    Ejemplo de uso:  
        fomc = FomcPresConfScript()
        df = fomc.get_contents()
    '''
    def __init__(self, verbose=True, max_threads=10, base_dir='../data/FOMC/'):
        super().__init__('presconf_script', verbose, max_threads, base_dir)

    def _get_links(self, from_year):
        '''
        Sobrescribe la función privada que establece todos los enlaces para los contenidos a descargar en el sitio web del FOMC
        desde from_year (=min(2015, from_year)) hasta el año más reciente
        '''
        self.links = []
        self.titles = []
        self.speakers = []
        self.dates = []

        r = requests.get(self.calendar_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        if self.verbose: print("Obteniendo enlaces para los guiones de conferencias de prensa...")
        presconfs = soup.find_all('a', href=re.compile('^/monetarypolicy/fomcpresconf\d{8}.htm'))
        presconf_urls = [self.base_url + presconf.attrs['href'] for presconf in presconfs]
        for presconf_url in presconf_urls:
            r_presconf = requests.get(presconf_url)
            soup_presconf = BeautifulSoup(r_presconf.text, 'html.parser')
            contents = soup_presconf.find_all('a', href=re.compile('^/mediacenter/files/FOMCpresconf\d{8}.pdf'))
            for content in contents:
                self.links.append(content.attrs['href'])
                self.speakers.append(self._speaker_from_date(self._date_from_link(content.attrs['href'])))
                self.titles.append('FOMC Press Conference Transcript')
                self.dates.append(datetime.strptime(self._date_from_link(content.attrs['href']), '%Y-%m-%d'))
        if self.verbose: print("{} enlaces encontrados en la página actual.".format(len(self.links)))
        
        # Archivos anteriores a 2015
        if from_year <= 2014:
            print("Obteniendo enlaces de las páginas de archivo...")
            for year in range(from_year, 2015):
                yearly_contents = []
                fomc_yearly_url = self.base_url + '/monetarypolicy/fomchistorical' + str(year) + '.htm'
                r_year = requests.get(fomc_yearly_url)
                soup_yearly = BeautifulSoup(r_year.text, 'html.parser')

                presconf_hists = soup_yearly.find_all('a', href=re.compile('^/monetarypolicy/fomcpresconf\d{8}.htm'))
                presconf_hist_urls = [self.base_url + presconf_hist.attrs['href'] for presconf_hist in presconf_hists]
                for presconf_hist_url in presconf_hist_urls:
                    r_presconf_hist = requests.get(presconf_hist_url)
                    soup_presconf_hist = BeautifulSoup(r_presconf_hist.text, 'html.parser')
                    yearly_contents = soup_presconf_hist.find_all('a', href=re.compile('^/mediacenter/files/FOMCpresconf\d{8}.pdf'))
                    for yearly_content in yearly_contents:
                        self.links.append(yearly_content.attrs['href'])
                        self.speakers.append(self._speaker_from_date(self._date_from_link(yearly_content.attrs['href'])))
                        self.titles.append('FOMC Press Conference Transcript')
                        self.dates.append(datetime.strptime(self._date_from_link(yearly_content.attrs['href']), '%Y-%m-%d'))
                if self.verbose: print("AÑO: {} - {} enlaces encontrados.".format(year, len(presconf_hist_urls)))
            print("Hay un total de ", len(self.links), ' enlaces para ', self.content_type)

    def _add_article(self, link, index=None):
        '''
        Sobrescribe una función privada que agrega un artículo relacionado para 1 enlace en la variable de instancia
        El índice es el índice en el artículo para agregar.
        Debido al procesamiento concurrente, necesitamos asegurarnos de que los artículos se almacenen en el orden correcto
        '''
        if self.verbose:
            sys.stdout.write(".")
            sys.stdout.flush()

        link_url = self.base_url + link
        pdf_filepath = self.base_dir + 'script_pdf/FOMC_PresConfScript_' + self._date_from_link(link) + '.pdf'

        # Los guiones se proporcionan solo en pdf. Guarda el pdf y pasa el contenido
        res = requests.get(link_url)

        with open(pdf_filepath, 'wb') as f:
            f.write(res.content)

        # Extrae texto del pdf
        pdf_file_parsed = textract.process(pdf_filepath).decode('utf-8')
        paragraphs = re.sub('(\n)(\n)+', '\n', pdf_file_parsed.strip())
        paragraphs = paragraphs.split('\n')

        section = -1
        paragraph_sections = []
        for paragraph in paragraphs:
            if not re.search('^(page|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', paragraph.lower()):
                if len(re.findall(r'[A-Z]', paragraph[:10])) > 5 and not re.search('(present|frb/us|abs cdo|libor|rp–ioer|lsaps|cusip|nairu|s cpi|clos, r)', paragraph[:10].lower()):
                    section += 1
                    paragraph_sections.append("")
                if section >= 0:
                    paragraph_sections[section] += paragraph
        self.articles[index] = "\n\n[SECTION]\n\n".join([paragraph for paragraph in paragraph_sections])
