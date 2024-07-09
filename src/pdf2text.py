# Importación de módulos necesarios
import sys
from tika import parser

def pdf2text(filename):
    # Función para convertir PDF a texto
    
    # Utiliza el parser de Tika para extraer el contenido del archivo PDF
    raw = parser.from_file(filename + '.pdf')

    # Abre un archivo de texto para escribir el contenido extraído
    f = open(filename + '.txt', 'w+')
    
    # Escribe el contenido extraído en el archivo de texto, eliminando espacios en blanco al inicio y al final
    f.write(raw['content'].strip())
    
    # Cierra el archivo de texto
    f.close()  # Nota: Falta los paréntesis aquí, debería ser f.close()

# Obtiene el nombre del programa y los argumentos de la línea de comandos
pg_name = sys.argv[0]
args = sys.argv[1:]

# Verifica si se proporcionó exactamente un argumento
if len(sys.argv) != 2:
    # Si no hay exactamente 2 argumentos (nombre del programa + 1 argumento), muestra un mensaje de uso y sale del programa
    print("Usage: ", pg_name)
    print("Please specify One argument")
    sys.exit(1)

# Llama a la función pdf2text con el argumento proporcionado
pdf2text(args[0])