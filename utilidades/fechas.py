import datetime


def calcular_edad(fecha):

    if not fecha:
        return ""

    try:

        n = datetime.datetime.strptime(
            fecha,
            "%Y-%m-%d"
        )

        h = datetime.datetime.now()

        edad = h.year - n.year

        if (
            h.month,
            h.day
        ) < (
            n.month,
            n.day
        ):

            edad -= 1

        return edad

    except ValueError:

        return ""


def hora_actual():

    return datetime.datetime.now().strftime(
        "%H:%M:%S"
    )


def fecha_actual():

    return datetime.datetime.now().strftime(
        "%Y-%m-%d"
    )
