from core.intenciones import detectar_intencion


def procesar(texto, memoria, config):
    """
    Punto central de decisión de ORION.
    """

    intencion = detectar_intencion(texto)

    return {
        "texto": texto,
        "intencion": intencion
    }