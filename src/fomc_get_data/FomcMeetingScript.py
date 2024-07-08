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

class FomcMeetingScript(FomcBase):
    '''
    Una clase  para extraer guiones de reuniones del sitio web del FOMC.
    El FOMC publica los guiones de las reuniones después de 5 años, por lo que esto no puede usarse para la predicción de la política monetaria en tiempo real.

    Ejemplo de uso:  
        fomc = FomcMeetingScript()
        df = fomc.get_contents()
    '''
    def __init__(self, verbose = True, max_threads = 10, base_dir = '../data/FOMC/'):
        super().__init__('meeting_script', verbose, max_threads, base_dir)

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
        
        # Los guiones de las reuniones solo se pueden encontrar en el archivo, ya que se publican después de cinco años
        if from_year > 2014:
            print("Los guiones de las reuniones están disponibles para 2014 o años anteriores")
        if from_year <= 2014:
            for year in range(from_year, 2015):
                yearly_contents = []
                fomc_yearly_url = self.base_url + '/monetarypolicy/fomchistorical' + str(year) + '.htm'
                r_year = requests.get(fomc_yearly_url)
                soup_yearly = BeautifulSoup(r_year.text, 'html.parser')
                # Busca enlaces a archivos PDF de guiones de reuniones
                meeting_scripts = soup_yearly.find_all('a', href=re.compile('^/monetarypolicy/files/FOMC\d{8}meeting.pdf'))
                for meeting_script in meeting_scripts:
                    self.links.append(meeting_script.attrs['href'])
                    self.speakers.append(self._speaker_from_date(self._date_from_link(meeting_script.attrs['href'])))
                    self.titles.append('FOMC Meeting Transcript')
                    self.dates.append(datetime.strptime(self._date_from_link(meeting_script.attrs['href']), '%Y-%m-%d'))
                if self.verbose: print("AÑO: {} - {} guiones de reuniones encontrados.".format(year, len(meeting_scripts)))
            print("Hay un total de ", len(self.links), ' enlaces para ', self.content_type)

    def _add_article(self, link, index=None):
        '''
        Sobrescribe una función  que agrega un artículo relacionado para 1 enlace en la variable de instancia
        El índice es el índice en el artículo para agregar.
        Debido al procesamiento concurrente, necesitamos asegurarnos de que los artículos se almacenen en el orden correcto
        '''
        if self.verbose:
            sys.stdout.write(".")
            sys.stdout.flush()

        link_url = self.base_url + link
        pdf_filepath = self.base_dir + 'script_pdf/FOMC_MeetingScript_' + self._date_from_link(link) + '.pdf'

        # Los guiones solo se proporcionan en formato PDF. Guarda el PDF y pasa el contenido
        res = requests.get(link_url)
        with open(pdf_filepath, 'wb') as f:
            f.write(res.content)

        # Extrae texto del PDF
        pdf_file_parsed = textract.process(pdf_filepath).decode('utf-8')
        paragraphs = re.sub('(\n)(\n)+', '\n', pdf_file_parsed.strip())
        paragraphs = paragraphs.split('\n')

        section = -1
        paragraph_sections = []
        for paragraph in paragraphs:
            # Filtra los párrafos que no empiezan con fechas o palabras clave específicas
            if not re.search('^(page|january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', paragraph.lower()):
                # Filtra los párrafos que no parecen ser encabezados de sección
                if len(re.findall(r'[A-Z]', paragraph[:10])) > 5 and not re.search('(present|frb/us|abs cdo|libor|rp–ioer|lsaps|cusip|nairu|s cpi|clos, r)', paragraph[:10].lower()):
                    section += 1
                    paragraph_sections.append("")
                if section >= 0:
                    paragraph_sections[section] += paragraph
        self.articles[index] = "\n\n[SECTION]\n\n".join([paragraph for paragraph in paragraph_sections])
