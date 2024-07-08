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

# Importa la clase base
from .FomcBase import FomcBase

class FomcStatement(FomcBase):
    '''
    Una clase conveniente para extraer comunicados del sitio web del FOMC
    Ejemplo de uso:  
        fomc = FomcStatement()
        df = fomc.get_contents()
    '''
    def __init__(self, verbose=True, max_threads=10, base_dir='../data/FOMC/'):
        super().__init__('statement', verbose, max_threads, base_dir)

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
        
        # Obtener enlaces de la página actual. Los guiones de la reunión no están disponibles.
        if self.verbose: print("Obteniendo enlaces para comunicados...")
        contents = soup.find_all('a', href=re.compile('^/newsevents/pressreleases/monetary\d{8}[ax].htm'))
        self.links = [content.attrs['href'] for content in contents]
        self.speakers = [self._speaker_from_date(self._date_from_link(x)) for x in self.links]
        self.titles = ['FOMC Statement'] * len(self.links)
        self.dates = [datetime.strptime(self._date_from_link(x), '%Y-%m-%d') for x in self.links]
        # Corregir algunas fechas en el enlace que no coinciden con la fecha de la reunión
        for i, m_date in enumerate(self.dates):
            if m_date == datetime(2019, 10, 11):
                self.dates[i] = datetime(2019, 10, 4)

        if self.verbose: print("{} enlaces encontrados en la página actual.".format(len(self.links)))

        # Archivados antes de 2015
        if from_year <= 2014:
            print("Obteniendo enlaces de páginas de archivo...")
            for year in range(from_year, 2015):
                yearly_contents = []
                fomc_yearly_url = self.base_url + '/monetarypolicy/fomchistorical' + str(year) + '.htm'
                r_year = requests.get(fomc_yearly_url)
                soup_yearly = BeautifulSoup(r_year.text, 'html.parser')
                yearly_contents = soup_yearly.findAll('a', text='Statement')
                for yearly_content in yearly_contents:
                    self.links.append(yearly_content.attrs['href'])
                    self.speakers.append(self._speaker_from_date(self._date_from_link(yearly_content.attrs['href'])))
                    self.titles.append('FOMC Statement')
                    self.dates.append(datetime.strptime(self._date_from_link(yearly_content.attrs['href']), '%Y-%m-%d'))
                    # Corregir algunas fechas en el enlace que no coinciden con la fecha de la reunión
                    if self.dates[-1] == datetime(2007, 6, 18):
                        self.dates[-1] = datetime(2007, 6, 28)
                    elif self.dates[-1] == datetime(2007, 8, 17):
                        self.dates[-1] = datetime(2007, 8, 16)
                    elif self.dates[-1] == datetime(2008, 1, 22):
                        self.dates[-1] = datetime(2008, 1, 21)
                    elif self.dates[-1] == datetime(2008, 3, 11):
                        self.dates[-1] = datetime(2008, 3, 10)
                    elif self.dates[-1] == datetime(2008, 10, 8):
                        self.dates[-1] = datetime(2008, 10, 7)

                if self.verbose: print("AÑO: {} - {} enlaces encontrados.".format(year, len(yearly_contents)))

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

        res = requests.get(self.base_url + link)
        html = res.text
        article = BeautifulSoup(html, 'html.parser')
        paragraphs = article.findAll('p')
        self.articles[index] = "\n\n[SECTION]\n\n".join([paragraph.get_text().strip() for paragraph in paragraphs])
