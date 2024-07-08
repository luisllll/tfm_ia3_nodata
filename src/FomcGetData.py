from datetime import date
import numpy as np
import pandas as pd
import pickle
import sys

# Importar las clases que manejan los diferentes tipos de datos del FOMC
from fomc_get_data.FomcStatement import FomcStatement
from fomc_get_data.FomcMinutes import FomcMinutes
from fomc_get_data.FomcMeetingScript import FomcMeetingScript
from fomc_get_data.FomcPresConfScript import FomcPresConfScript
from fomc_get_data.FomcSpeech import FomcSpeech
from fomc_get_data.FomcTestimony import FomcTestimony

def download_data(fomc, from_year):
    '''
    Función para descargar datos de un tipo específico de contenido del FOMC para un rango de años.
    Guarda el DataFrame descargado como un archivo pickle y los textos como archivos de texto plano.
    '''
    # Obtener el DataFrame con los contenidos del FOMC para el rango de años especificado
    df = fomc.get_contents(from_year)
    print("Shape of the downloaded data: ", df.shape)
    print("The first 5 rows of the data: \n", df.head())
    print("The last 5 rows of the data: \n", df.tail())

    # Guardar el DataFrame como un archivo pickle
    fomc.pickle_dump_df(filename=fomc.content_type + ".pickle")

    # Guardar los textos como archivos de texto plano en una carpeta específica
    fomc.save_texts(prefix=fomc.content_type + "/FOMC_" + fomc.content_type + "_")

if __name__ == '__main__':
    # Nombre del programa (nombre del script)
    pg_name = sys.argv[0]

    # Argumentos pasados al script desde la línea de comandos
    args = sys.argv[1:]

    # Tipos de contenido válidos para descargar
    content_type_all = ('statement', 'minutes', 'meeting_script', 'presconf_script', 'speech', 'testimony', 'all')

    # Validación de los argumentos pasados
    if (len(args) != 1) and (len(args) != 2):
        print("Uso: ", pg_name)
        print("Por favor, especifique el primer argumento de ", content_type_all)
        print("Puede añadir from_year (yyyy) como el segundo argumento.")
        print("\n Usted especificó: ", ','.join(args))
        sys.exit(1)

    # Establecer el año mínimo predeterminado para la descarga
    if len(args) == 1:
        from_year = 1990  # Año mínimo
    else:
        from_year = int(args[1])

    # Validar el tipo de contenido especificado
    content_type = args[0].lower()
    if content_type not in content_type_all:
        print("Uso: ", pg_name)
        print("Por favor, especifique el primer argumento de ", content_type_all)
        sys.exit(1)

    # Validar el rango del año desde el cual descargar
    if (from_year < 1980) or (from_year > 2020):
        print("Uso: ", pg_name)
        print("Por favor, especifique el segundo argumento entre 1980 y 2020")
        sys.exit(1)

    # Descargar todos los tipos de contenido si se especifica 'all', o solo uno específico
    if content_type == 'all':
        fomc = FomcStatement()
        download_data(fomc, from_year)

        fomc = FomcMinutes()
        download_data(fomc, from_year)

        fomc = FomcMeetingScript()
        download_data(fomc, from_year)

        fomc = FomcPresConfScript()
        download_data(fomc, from_year)

        fomc = FomcSpeech()
        download_data(fomc, from_year)

        fomc = FomcTestimony()
        download_data(fomc, from_year)
    else:
        # Descargar solo el tipo de contenido especificado
        if content_type == 'statement':
            fomc = FomcStatement()
        elif content_type == 'minutes':
            fomc = FomcMinutes()
        elif content_type == 'meeting_script':
            fomc = FomcMeetingScript()
        elif content_type == 'presconf_script':
            fomc = FomcPresConfScript()
        elif content_type == 'speech':
            fomc = FomcSpeech()
        elif content_type == 'testimony':
            fomc = FomcTestimony()

        download_data(fomc, from_year)

