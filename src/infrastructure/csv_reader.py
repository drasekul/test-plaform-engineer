# src/infrastructure/csv_reader.py
# Adaptador de lectura del CSV de ventas.
# Responsabilidad única: leer el archivo y retornar datos crudos como lista de dicts.
# La limpieza y transformación de datos es responsabilidad de ProcessSaleUseCase.
import csv


def read_csv(file_path: str) -> list[dict]:
    """
    Lee el archivo CSV de ventas y retorna una lista de diccionarios.

    Se usa encoding='utf-8' ya que ventas.csv está en UTF-8.
    Los artefactos de encoding como 'RegiÃ³n' son caracteres UTF-8 válidos
    que representan la corrupción del texto original; se corrigen en la
    capa de aplicación.

    Retorna los valores como strings (tal como los entrega csv.DictReader),
    sin conversión de tipos — eso también es responsabilidad del caso de uso.
    """
    rows = []
    with open(file_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows
