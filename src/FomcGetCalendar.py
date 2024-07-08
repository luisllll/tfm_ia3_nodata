from datetime import datetime
import os
import sys
import pickle
import re

import pandas as pd

import requests
from bs4 import BeautifulSoup

from tqdm import tqdm

def dump_df(df, filename="output"):
    '''
    Guarda un DataFrame interno df en un archivo pickle y csv
    '''
    filepath = filename + '.pickle'
    print("")
    print("Escribiendo en ", filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as output_file:
        pickle.dump(df, output_file)
    filepath = filename + '.csv'
    print("Escribiendo en ", filepath)
    df.to_csv(filepath, index=False)

def is_integer(n):
    '''
    Verifica si una cadena de entrada se puede convertir a entero
    '''
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()

if __name__ == '__main__':
    '''
    Este programa obtiene todas las fechas del calendario de reuniones pasadas y anunciadas del FOMC.
    El primer argumento es opcional para especificar desde qué año obtener las fechas.
    Crea un DataFrame y guarda un archivo pickle y un archivo csv.
    '''
    # URLs del sitio web del FOMC
    base_url = 'https://www.federalreserve.gov'
    calendar_url = base_url + '/monetarypolicy/fomccalendars.htm'

    date_list = []
    pg_name = sys.argv[0]

    if len(sys.argv) != 2:
        print("Uso: ", pg_name)
        print("Por favor, especifique el primer argumento entre 1936 y 2015")
        sys.exit(1)    
        
    from_year = sys.argv[1]

    # Maneja el primer argumento, from_year
    if from_year:
        if is_integer(from_year):
            from_year = int(from_year)
        else:
            print("Uso: ", pg_name)
            print("Por favor, especifique el primer argumento entre 1936 y 2015")
            sys.exit(1)
        
        if (from_year < 1936) or (from_year > 2015):
            print("Uso: ", pg_name)
            print("Por favor, especifique el primer argumento entre 1936 y 2015")
            sys.exit(1)
    else:
        from_year = 1936
        print("El año desde es 1936. Por favor, especifique el año como el primer argumento si es necesario.")

    # Obtener fechas de reunión del FOMC desde la página actual - de 2015 a 2020
    r = requests.get(calendar_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    panel_divs = soup.find_all('div', {"class": "panel panel-default"})

    for panel_div in panel_divs:
        m_year = panel_div.find('h4').get_text()[:4]
        m_months = panel_div.find_all('div', {"class": "fomc-meeting__month"})
        m_dates = panel_div.find_all('div', {"class": "fomc-meeting__date"})
        print("AÑO: {} - {} reuniones encontradas.".format(m_year, len(m_dates)))

        for (m_month, m_date) in zip(m_months, m_dates):
            month_name = m_month.get_text().strip()
            date_text = m_date.get_text().strip()
            is_forecast = False
            is_unscheduled = False
            is_month_short = False

            if ("cancelada" in date_text):
                continue
            elif "voto de anotación" in date_text:
                date_text = date_text.replace("(voto de anotación)", "").strip()
            elif "no programada" in date_text:
                date_text = date_text.replace("(no programada)", "").strip()
                is_unscheduled = True
            
            if "*" in date_text:
                date_text = date_text.replace("*", "").strip()
                is_forecast = True
            
            if "/" in month_name:
                month_name = re.findall(r".+/(.+)$", month_name)[0]
                is_month_short = True
            
            if "-" in date_text:
                date_text = re.findall(r".+-(.+)$", date_text)[0]
            
            meeting_date_str = m_year + "-" + month_name + "-" + date_text
            if is_month_short:
                meeting_date = datetime.strptime(meeting_date_str, '%Y-%b-%d')
            else:
                meeting_date = datetime.strptime(meeting_date_str, '%Y-%B-%d')

            date_list.append({"date": meeting_date, "unscheduled": is_unscheduled, "forecast": is_forecast, "confcall": False})

    # Obtener fechas de reunión del FOMC anteriores a 2015
    for year in range(from_year, 2015):
        hist_url = base_url + '/monetarypolicy/fomchistorical' + str(year) + '.htm'
        r = requests.get(hist_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        if year in (2011, 2012, 2013, 2014):
            panel_headings = soup.find_all('h5', {"class": "panel-heading"})
        else:
            panel_headings = soup.find_all('div', {"class": "panel-heading"})
        print("AÑO: {} - {} reuniones encontradas.".format(year, len(panel_headings)))
        for panel_heading in panel_headings:
            date_text = panel_heading.get_text().strip()
            #print("Fecha: ", date_text)
            regex = r"(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre).*\s(\d*-)*(\d+)\s+(Reunión|Conferencias? telefónicas?|\(no programada\))\s-\s(\d+)"
            date_text_ext = re.findall(regex, date_text)[0]
            meeting_date_str = date_text_ext[4] + "-" + date_text_ext[0] + "-" + date_text_ext[2]
            #print("   Extraído:", meeting_date_str)
            if meeting_date_str == '1992-Junio-1':
                meeting_date_str = '1992-Julio-1'
            elif meeting_date_str == '1995-Enero-1':
                meeting_date_str = '1995-Febrero-1'
            elif meeting_date_str == '1998-Junio-1':
                meeting_date_str = '1998-Julio-1'
            elif meeting_date_str == '2012-Julio-1':
                meeting_date_str = '2012-Agosto-1'
            elif meeting_date_str == '2013-Abril-1':
                meeting_date_str = '2013-Mayo-1'

            meeting_date = datetime.strptime(meeting_date_str, '%Y-%B-%d')
            is_confcall = "Conferencia telefónica" in date_text_ext[3]
            is_unscheduled = "no programada" in date_text_ext[3]
            date_list.append({"date": meeting_date, "unscheduled": is_unscheduled, "forecast": False, "confcall": is_confcall})

    df = pd.DataFrame(date_list).sort_values(by=['date'])
    df.reset_index(drop=True, inplace=True)
    print(df)

    # Guardar
    dump_df(df, "../data/FOMC/fomc_calendar")
