from datetime import date
import re
import threading
import pickle
import sys
import os

import requests
from bs4 import BeautifulSoup

import numpy as np
import pandas as pd

from abc import ABCMeta, abstractmethod

class FomcBase(metaclass=ABCMeta):
    '''
    Una clase base para extraer documentos del sitio web del FOMC
    '''

    def __init__(self, content_type, verbose, max_threads, base_dir):
        
        # Asignar los argumentos a variables internas
        self.content_type = content_type
        self.verbose = verbose
        self.MAX_THREADS = max_threads
        self.base_dir = base_dir

        # Inicialización de variables
        self.df = None
        self.links = None
        self.dates = None
        self.articles = None
        self.speakers = None
        self.titles = None

        # URLs del sitio web del FOMC
        self.base_url = 'https://www.federalreserve.gov'
        self.calendar_url = self.base_url + '/monetarypolicy/fomccalendars.htm'

        # Lista de presidentes del FOMC
        self.chair = pd.DataFrame(
            data=[["Greenspan", "Alan", "1987-08-11", "2006-01-31"], 
                  ["Bernanke", "Ben", "2006-02-01", "2014-01-31"], 
                  ["Yellen", "Janet", "2014-02-03", "2018-02-03"],
                  ["Powell", "Jerome", "2018-02-05", "2022-02-05"]],
            columns=["Surname", "FirstName", "FromDate", "ToDate"])
        
    def _date_from_link(self, link):
        # Extraer la fecha del enlace usando una expresión regular
        date = re.findall('[0-9]{8}', link)[0]
        if date[4] == '0':
            date = "{}-{}-{}".format(date[:4], date[5:6], date[6:])
        else:
            date = "{}-{}-{}".format(date[:4], date[4:6], date[6:])
        return date

    def _speaker_from_date(self, article_date):
        # Determinar el orador basado en la fecha del artículo
        if self.chair.FromDate[0] < article_date and article_date < self.chair.ToDate[0]:
            speaker = self.chair.FirstName[0] + " " + self.chair.Surname[0]
        elif self.chair.FromDate[1] < article_date and article_date < self.chair.ToDate[1]:
            speaker = self.chair.FirstName[1] + " " + self.chair.Surname[1]
        elif self.chair.FromDate[2] < article_date and article_date < self.chair.ToDate[2]:
            speaker = self.chair.FirstName[2] + " " + self.chair.Surname[2]
        elif self.chair.FromDate[3] < article_date and article_date < self.chair.ToDate[3]:
            speaker = self.chair.FirstName[3] + " " + self.chair.Surname[3]
        else:
            speaker = "otro"
        return speaker
        
    @abstractmethod
    def _get_links(self, from_year):
        '''
        Función privada que establece todos los enlaces para las reuniones del FOMC
        desde el año `from_year` hasta el año más reciente.
        `from_year` es min(2015, from_year)
        '''
        # Implementar en las subclases
        pass
    
    @abstractmethod
    def _add_article(self, link, index=None):
        '''
        Agrega el artículo relacionado a un enlace en la variable de instancia.
        `index` es el índice en el artículo a agregar. Debido al procesamiento concurrente,
        necesitamos asegurarnos de que los artículos se almacenen en el orden correcto.
        '''
        # Implementar en las subclases
        pass

    def _get_articles_multi_threaded(self):
        '''
        Obtiene todos los artículos utilizando multi-threading
        '''
        if self.verbose:
            print("Obteniendo artículos - Multi-threaded...")

        self.articles = ['']*len(self.links)
        jobs = []
        # Iniciar y empezar threads:
        index = 0
        while index < len(self.links):
            if len(jobs) < self.MAX_THREADS:
                t = threading.Thread(target=self._add_article, args=(self.links[index], index,))
                jobs.append(t)
                t.start()
                index += 1
            else:    # Esperar a que los threads completen y unirlos de vuelta al main thread
                t = jobs.pop(0)
                t.join()
        for t in jobs:
            t.join()

        #for row in range(len(self.articles)):
        #    self.articles[row] = self.articles[row].strip()

    def get_contents(self, from_year=1990):
        '''
        Retorna un DataFrame de Pandas con la fecha como índice para un rango de fechas desde `from_year` hasta la más reciente.
        También guarda el mismo en la variable interna `df`.
        '''
        self._get_links(from_year)
        self._get_articles_multi_threaded()
        dict = {
            'date': self.dates,
            'contents': self.articles,
            'speaker': self.speakers, 
            'title': self.titles
        }
        self.df = pd.DataFrame(dict).sort_values(by=['date'])
        self.df.reset_index(drop=True, inplace=True)
        return self.df

    def pickle_dump_df(self, filename="output.pickle"):
        '''
        Guarda el DataFrame interno `df` en un archivo pickle
        '''
        filepath = self.base_dir + filename
        print("")
        if self.verbose: print("Escribiendo a ", filepath)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as output_file:
            pickle.dump(self.df, output_file)

    def save_texts(self, prefix="FOMC_", target="contents"):
        '''
        Guarda el DataFrame interno `df` en archivos de texto
        '''
        tmp_dates = []
        tmp_seq = 1
        for i, row in self.df.iterrows():
            cur_date = row['date'].strftime('%Y-%m-%d')
            if cur_date in tmp_dates:
                tmp_seq += 1
                filepath = self.base_dir + prefix + cur_date + "-" + str(tmp_seq) + ".txt"
            else:
                tmp_seq = 1
                filepath = self.base_dir + prefix + cur_date + ".txt"
            tmp_dates.append(cur_date)
            if self.verbose: print("Escribiendo a ", filepath)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as output_file:
                output_file.write(row[target])
