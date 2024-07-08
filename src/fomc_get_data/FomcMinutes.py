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

class FomcMinutes(FomcBase):
    '''
    Una clase para extraer las minutas del sitio web del FOMC
    Ejemplo de uso:  
        fomc = FomcMinutes()
        df = fomc.get_contents()
    '''
    def __init__(self, verbose=True, max_threads=10, base_dir='../data/FOMC/'):
        super().__init__('minutes', verbose, max_threads, base_dir)

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

        # Obtener enlaces de la página actual. Los guiones de las reuniones no están disponibles.
        if self.verbose: print("Obteniendo enlaces para las minutas...")
        contents = soup.find_all('a', href=re.compile('^/monetarypolicy/fomcminutes\d{8}.htm'))
        
        self.links = [content.attrs['href'] for content in contents]
        self.speakers = [self._speaker_from_date(self._date_from_link(x)) for x in self.links]
        self.titles = ['FOMC Meeting Minutes'] * len(self.links)
        self.dates = [datetime.strptime(self._date_from_link(x), '%Y-%m-%d') for x in self.links]
        if self.verbose: print("{} enlaces encontrados en la página actual.".format(len(self.links)))

        # Archivos anteriores a 2015
        if from_year <= 2014:
            print("Obteniendo enlaces de páginas de archivo...")
            for year in range(from_year, 2015):
                yearly_contents = []
                fomc_yearly_url = self.base_url + '/monetarypolicy/fomchistorical' + str(year) + '.htm'
                r_year = requests.get(fomc_yearly_url)
                soup_yearly = BeautifulSoup(r_year.text, 'html.parser')
                yearly_contents = soup_yearly.find_all('a', href=re.compile('(^/monetarypolicy/fomcminutes|^/fomc/minutes|^/fomc/MINUTES)'))
                for yearly_content in yearly_contents:
                    self.links.append(yearly_content.attrs['href'])
                    self.speakers.append(self._speaker_from_date(self._date_from_link(yearly_content.attrs['href'])))
                    self.titles.append('FOMC Meeting Minutes')
                    self.dates.append(datetime.strptime(self._date_from_link(yearly_content.attrs['href']), '%Y-%m-%d'))
                    # A veces las minutas llevan el primer día de la reunión antes del 2000, por lo que se actualizan al segundo día
                    if self.dates[-1] == datetime(1996,1,30):
                        self.dates[-1] = datetime(1996,1,31)
                    elif self.dates[-1] == datetime(1996,7,2):
                        self.dates[-1] = datetime(1996,7,3)
                    elif self.dates[-1] == datetime(1997,2,4):
                        self.dates[-1] = datetime(1997,2,5)
                    elif self.dates[-1] == datetime(1997,7,1):
                        self.dates[-1] = datetime(1997,7,2)
                    elif self.dates[-1] == datetime(1998,2,3):
                        self.dates[-1] = datetime(1998,2,4)
                    elif self.dates[-1] == datetime(1998,6,30):
                        self.dates[-1] = datetime(1998,7,1)
                    elif self.dates[-1] == datetime(1999,2,2):
                        self.dates[-1] = datetime(1999,2,3)
                    elif self.dates[-1] == datetime(1999,6,29):
                        self.dates[-1] = datetime(1999,6,30)

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

        # La etiqueta <p> no está correctamente cerrada en muchos casos
        html = html.replace('<P', '<p').replace('</P>', '</p>')
        html = html.replace('<p', '</p><p').replace('</p><p', '<p', 1)

        # Elimina todo después del apéndice o las referencias
        x = re.search(r'(<b>references|<b>appendix|<strong>references|<strong>appendix)', html.lower())
        if x:
            html = html[:x.start()]
            html += '</body></html>'
        # Analiza el texto HTML con BeautifulSoup
        article = BeautifulSoup(html, 'html.parser')

        #if link == '/fomc/MINUTES/1994/19940517min.htm':
        #    print(article)

        # Elimina las notas al pie
        for fn in article.find_all('a', {'name': re.compile('fn\d')}):
            fn.decompose()
        # Obtén todas las etiquetas <p>
        paragraphs = article.findAll('p')
        self.articles[index] = "\n\n[SECTION]\n\n".join([paragraph.get_text().strip() for paragraph in paragraphs])
