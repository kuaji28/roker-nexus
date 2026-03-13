"""
ROKER NEXUS — Importers
Factory para instanciar el importador correcto según el tipo de archivo.
"""
from importers.flexxus_optimizacion import ImportadorOptimizacion
from importers.flexxus_lista_precios import ImportadorListaPrecios
from importers.flexxus_stock import ImportadorStock
from importers.flexxus_ventas import ImportadorVentas, ImportadorCompras
from importers.aitech_mariano import ImportadorAITECH, ImportadorMariano


IMPORTADORES = {
    "optimizacion":    ImportadorOptimizacion,
    "lista_precios":   ImportadorListaPrecios,
    "stock":           ImportadorStock,
    "ventas":          ImportadorVentas,
    "compras":         ImportadorCompras,
    "cotizacion_aitech": ImportadorAITECH,
    "mariano":         ImportadorMariano,
}


def get_importador(tipo: str):
    """Retorna una instancia del importador para el tipo dado."""
    cls = IMPORTADORES.get(tipo)
    if cls:
        return cls()
    return None


def importar_archivo(uploaded_file):
    """
    Detecta automáticamente el tipo de archivo y lo importa.
    Retorna ResultadoImportacion.
    """
    from utils.helpers import detectar_tipo_flexxus
    nombre = getattr(uploaded_file, "name", "")
    tipo = detectar_tipo_flexxus(nombre)
    if not tipo:
        from importers.base import ResultadoImportacion
        r = ResultadoImportacion("desconocido", nombre)
        r.estado = "error"
        r.mensaje = f"No se pudo detectar el tipo de archivo: {nombre}"
        return r
    imp = get_importador(tipo)
    if not imp:
        from importers.base import ResultadoImportacion
        r = ResultadoImportacion("desconocido", nombre)
        r.estado = "error"
        r.mensaje = f"No hay importador para: {tipo}"
        return r
    return imp.importar(uploaded_file)
