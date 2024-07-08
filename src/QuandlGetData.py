import datetime  # Importamos el módulo datetime para trabajar con fechas
import sys, os  # Importamos los módulos sys y os para manejar argumentos de línea de comandos y operaciones del sistema
import quandl  # Importamos la biblioteca Quandl para acceder a datos financieros
import nasdaqdatalink  # Importamos un módulo llamado nasdaqdatalink (suponemos que es personalizado)

def download_data(quandl_code, from_date):
    """
    Función para descargar datos desde Quandl para un código dado y a partir de una fecha especificada.
    Guarda los datos descargados en un archivo CSV y muestra información resumida sobre los datos descargados.
    """
    print("Descargando: [{}]".format(quandl_code))
    df = nasdaqdatalink.get(quandl_code, start_date=from_date)  # Llamamos a una función para obtener los datos usando nasdaqdatalink
    print("Forma de los datos descargados: ", df.shape)  # Mostramos la forma (número de filas y columnas) de los datos descargados
    print("Primeras 5 filas de los datos: \n", df.head())  # Mostramos las primeras 5 filas de los datos descargados
    print("Últimas 5 filas de los datos: \n", df.tail())  # Mostramos las últimas 5 filas de los datos descargados
    # Guardamos los datos en un archivo CSV en la carpeta ../data/MarketData/Quandl/
    df.to_csv(os.path.join("..", "data", "MarketData", "Quandl", quandl_code.replace("/", "_")+".csv"))

if __name__ == '__main__':
    pg_name = sys.argv[0]  # Nombre del programa obtenido de los argumentos de la línea de comandos
    args = sys.argv[1:]  # Argumentos de la línea de comandos excluyendo el nombre del programa
    fred_all = ('DFEDTAR', 'DFEDTARL', 'DFEDTARU', 'DFF', 'GDPC1', 'GDPPOT', 'PCEPILFE', 'CPIAUCSL', 'UNRATE', 'PAYEMS', 'RRSFS', 'HSN1F')
    ism_all = ('MAN_PMI', 'NONMAN_NMI')
    treasury_code = 'USTREASURY/YIELD'  # Código de Quandl para los rendimientos del Tesoro de EE. UU.

    if (len(args) != 2) and (len(args) != 3):  # Verificamos si se proporcionaron 2 o 3 argumentos
        print("Uso: python {} api_key from_date [Quandl Code]".format(pg_name))
        print("   api_key: Copiar desde tu cuenta de Quandl")
        print("   from_date: Especificar la fecha de inicio en formato yyyy-mm-dd")
        print("   Quandl Code: Opcional para especificar el código. (por ejemplo, FRED/DFEDTAR) Si no se especifica, se descargan todos los datos.")
        print("\n Has especificado: ", ','.join(args))
        sys.exit(1)  # Salimos del programa con código de error 1 si los argumentos no son correctos

    if len(args) == 2:
        all_data = True  # Si se proporcionaron 2 argumentos, se descargan todos los datos
    else:
        all_data = False  # Si se proporcionaron 3 argumentos, se descarga un código específico

    quandl.ApiConfig.api_key = args[0]  # Configuramos la clave de la API de Quandl usando el primer argumento
    from_date = args[1]  # Fecha de inicio obtenida del segundo argumento

    try:
        datetime.datetime.strptime(from_date, '%Y-%m-%d')  # Verificamos que la fecha de inicio esté en el formato correcto
    except ValueError:
        print("from_date debe estar en formato yyyy-mm-dd. Has proporcionado: ", from_date)
        sys.exit(1)  # Salimos del programa con código de error 1 si la fecha no es válida

    if all_data:
        # Descargamos todos los conjuntos de datos en las tuplas fred_all e ism_all, y los rendimientos del Tesoro
        for dataset_code in fred_all:
            download_data("FRED/" + dataset_code, from_date)
        for dataset_code in ism_all:
            download_data("ISM/" + dataset_code, from_date)
        download_data(treasury_code, from_date)
    else:
        download_data(quandl_code, from_date)  # Descargamos solo el conjunto de datos especificado por el código de Quandl

