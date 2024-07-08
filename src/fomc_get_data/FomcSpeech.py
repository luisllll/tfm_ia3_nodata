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

class FomcSpeech(FomcBase):
    '''
    Una clase conveniente para extraer discursos del sitio web del FOMC
    Ejemplo de uso:  
        fomc = FomcSpeech()
        df = fomc.get_contents()
    '''
    def __init__(self, verbose=True, max_threads=10, base_dir='../data/FOMC/'):
        super().__init__('speech', verbose, max_threads, base_dir)
        self.speech_base_url = self.base_url + '/newsevents/speech'

    def _get_links(self, from_year):
        '''
        Sobrescribe la función privada que establece todos los enlaces para los contenidos a descargar en el sitio web del FOMC
        desde from_year (=min(2015, from_year)) hasta el año más reciente
        '''
        self.links = []
        self.titles = []
        self.speakers = []
        self.dates = []

        res = requests.get(self.calendar_url)
        soup = BeautifulSoup(res.text, 'html.parser')

        if self.verbose: print("Obteniendo enlaces para discursos...")
        to_year = datetime.today().strftime("%Y")

        if from_year <= 1995:
            print("Archivo solo desde 1996, estableciendo from_year como 1996...")
            from_year = 1996
        for year in range(from_year, int(to_year)+1):
            # Archivos entre 1996 y 2005, la URL cambió desde 2011
            if year < 2011:
                speech_url = self.speech_base_url + '/' + str(year) + 'speech.htm'
            else:
                speech_url = self.speech_base_url + '/' + str(year) + '-speeches.htm'

            res = requests.get(speech_url)
            soup = BeautifulSoup(res.text, 'html.parser')
            speech_links = soup.findAll('a', href=re.compile('^/?newsevents/speech/.*{}\d\d\d\d.*.htm|^/boarddocs/speeches/{}/|^{}\d\d\d\d.*.htm'.format(str(year), str(year), str(year))))
            for speech_link in speech_links:
                # A veces se pone el mismo enlace para ver el video en vivo. Omitir esos.
                if speech_link.find({'class': 'watchLive'}):
                    continue

                # Agregar enlace, título y fecha
                self.links.append(speech_link.attrs['href'])
                self.titles.append(speech_link.get_text())
                self.dates.append(datetime.strptime(self._date_from_link(speech_link.attrs['href']), '%Y-%m-%d'))

                # Agregar orador
                # De alguna manera, el orador está antes del enlace solo en 1997, mientras que en los otros es viceversa
                if year == 1997:
                    # De alguna manera, solo el enlace para el discurso del 15 de diciembre tiene el orador después del enlace en la página de 1997.
                    if speech_link.get('href') == '/boarddocs/speeches/1997/19971215.htm':
                        tmp_speaker = speech_link.parent.next_sibling.next_element.get_text().replace('\n', '').strip()
                    else:
                        tmp_speaker = speech_link.parent.previous_sibling.previous_sibling.get_text().replace('\n', '').strip()
                else:
                    # De alguna manera, 20051128 y 20051129 están estructurados de manera diferente
                    if speech_link.get('href') in ('/boarddocs/speeches/2005/20051128/default.htm', '/boarddocs/speeches/2005/20051129/default.htm'):
                        tmp_speaker = speech_link.parent.previous_sibling.previous_sibling.get_text().replace('\n', '').strip()
                    tmp_speaker = speech_link.parent.next_sibling.next_element.get_text().replace('\n', '').strip()
                    # Cuando se coloca un ícono de video entre el enlace y el orador
                    if tmp_speaker in ('Watch Live', 'Video'):
                        tmp_speaker = speech_link.parent.next_sibling.next_sibling.next_sibling.next_element.get_text().replace('\n', '').strip()
                self.speakers.append(tmp_speaker)
            if self.verbose: print("AÑO: {} - {} discursos encontrados.".format(year, len(speech_links)))

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
        # La etiqueta p no está correctamente cerrada en muchos casos
        html = html.replace('<P', '<p').replace('</P>', '</p>')
        html = html.replace('<p', '</p><p').replace('</p><p', '<p', 1)
        # eliminar todo después del apéndice o referencias
        x = re.search(r'(<b>references|<b>appendix|<strong>references|<strong>appendix)', html.lower())
        if x:
            html = html[:x.start()]
            html += '</body></html>'
        # Analizar el texto HTML con BeautifulSoup
        article = BeautifulSoup(html, 'html.parser')
        # Eliminar nota al pie
        for fn in article.find_all('a', {'name': re.compile('fn\d')}):
            if fn.parent:
                fn.parent.decompose()
            else:
                fn.decompose()
        # Obtener todas las etiquetas p
        paragraphs = article.findAll('p')
        self.articles[index] = "\n\n[SECTION]\n\n".join([paragraph.get_text().strip() for paragraph in paragraphs])
