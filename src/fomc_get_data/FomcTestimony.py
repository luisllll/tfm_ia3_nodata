from datetime import datetime
import threading
import sys
import os
import pickle
import re

import requests
from bs4 import BeautifulSoup
import json

import numpy as np
import pandas as pd

# Importa la clase base
from .FomcBase import FomcBase

class FomcTestimony(FomcBase):
    '''
    Una clase conveniente para extraer testimonios del sitio web del FOMC.
    Entre los testimonios, se encuentran los informes semestrales de política monetaria al Congreso por el presidente.
    Ejemplo de uso:  
        fomc = FomcTestimony()
        df = fomc.get_contents()
    '''
    def __init__(self, verbose=True, max_threads=10, base_dir='../data/FOMC/'):
        super().__init__('testimony', verbose, max_threads, base_dir)

    def _get_links(self, from_year):
        '''
        Sobrescribe la función privada que establece todos los enlaces para los contenidos a descargar en el sitio web del FOMC
        desde from_year (=min(1996, from_year)) hasta el año más reciente
        '''
        self.links = []
        self.titles = []
        self.speakers = []
        self.dates = []

        if self.verbose: print("Obteniendo enlaces para testimonios...")
        to_year = datetime.today().strftime("%Y")

        if from_year < 1996:
            print("El archivo solo está disponible desde 1996, así que se establece from_year como 1996...")
            from_year = 1996
        elif from_year > 2006:
            print("Todos los datos desde 2006 están en un solo json, así que se devuelven todos desde 2006 aunque se especifique el año ", from_year)

        url = self.base_url + '/json/ne-testimony.json'
        res = requests.get(url)
        res.encoding = 'utf-8-sig'  # Establecer la codificación para manejar BOM
        res_list = json.loads(res.text)
        for record in res_list:
            doc_link = record.get('l')
            if doc_link:
                self.links.append(doc_link)
                self.titles.append(record.get('t'))
                self.speakers.append(record.get('s'))
                date_str = record.get('d').split(" ")[0]
                self.dates.append(datetime.strptime(date_str, '%m/%d/%Y'))

        if from_year < 2006:
            for year in range(from_year, 2006):
                url = self.base_url + '/newsevents/testimony/' + str(year) + 'testimony.htm'

                res = requests.get(url)
                soup = BeautifulSoup(res.text, 'html.parser')

                doc_links = soup.findAll('a', href=re.compile('^/boarddocs/testimony/{}/|^/boarddocs/hh/{}/'.format(str(year), str(year))))
                for doc_link in doc_links:
                    # A veces se pone el mismo enlace para ver el video en vivo. Saltar esos.
                    if doc_link.find({'class': 'watchLive'}):
                        continue
                    # Agregar enlaces
                    self.links.append(doc_link.attrs['href'])

                    # Manejar errores de marcado
                    if doc_link.get('href') in ('/boarddocs/testimony/2005/20050420/default.htm'):
                        title = doc_link.get_text()
                        speaker = doc_link.parent.parent.next_element.next_element.get_text().replace('\n', '').strip()
                        date_str = doc_link.parent.parent.next_element.replace('\n', '').strip()
                    elif doc_link.get('href') in ('/boarddocs/testimony/1997/19970121.htm'):
                        title = doc_link.parent.parent.find_next('em').get_text().replace('\n', '').strip()
                        speaker = doc_link.parent.parent.find_next('strong').get_text().replace('\n', '').strip()
                        date_str = doc_link.get_text()
                    else:
                        title = doc_link.get_text()
                        speaker = doc_link.parent.find_next('div').get_text().replace('\n', '').strip()
                        # Cuando se coloca un ícono de video entre el enlace y el orador
                        if speaker in ('Watch Live', 'Video'):
                            speaker = doc_link.parent.find_next('p').find_next('p').get_text().replace('\n', '').strip()
                        date_str = doc_link.parent.parent.next_element.replace('\n', '').strip()

                    self.titles.append(doc_link.get_text())
                    self.speakers.append(speaker)
                    self.dates.append(datetime.strptime(date_str, '%B %d, %Y'))
                    
                if self.verbose: print("AÑO: {} - {} documentos de testimonio encontrados.".format(year, len(doc_links)))

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

        res = requests.get(self.base_url + link)
        html = res.text
        # La etiqueta p no está cerrada correctamente en muchos casos
        html = html.replace('<P', '<p').replace('</P>', '</p>')
        html = html.replace('<p', '</p><p').replace('</p><p', '<p', 1)
        # Eliminar todo después de apéndice o referencias
        x = re.search(r'(<b>references|<b>appendix|<strong>references|<strong>appendix)', html.lower())
        if x:
            html = html[:x.start()]
            html += '</body></html>'
        # Analizar el texto HTML con BeautifulSoup
        article = BeautifulSoup(html, 'html.parser')
        # Eliminar nota al pie
        for fn in article.find_all('a', {'name': re.compile('fn\d')}):
            fn.decompose()
        # Obtener todas las etiquetas p
        paragraphs = article.findAll('p')
        self.articles[index] = "\n\n[SECTION]\n\n".join([paragraph.get_text().strip() for paragraph in paragraphs])
