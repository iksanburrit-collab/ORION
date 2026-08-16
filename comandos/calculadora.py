"""Calculadora con expresiones matemáticas limitadas y seguras."""

import ast
import math
import operator


_OPERADORES_BINARIOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_OPERADORES_UNARIOS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_FUNCIONES_PERMITIDAS = {
    "sqrt": math.sqrt,
}


def _evaluar_expresion(expresion: str) -> float | int:
    """Evalúa únicamente números, operaciones aritméticas y funciones permitidas."""
    arbol = ast.parse(expresion, mode="eval")

    def evaluar(nodo: ast.AST) -> float | int:
        if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
            return nodo.value

        if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES_BINARIOS:
            return _OPERADORES_BINARIOS[type(nodo.op)](
                evaluar(nodo.left), evaluar(nodo.right)
            )

        if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _OPERADORES_UNARIOS:
            return _OPERADORES_UNARIOS[type(nodo.op)](evaluar(nodo.operand))

        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id in _FUNCIONES_PERMITIDAS
            and not nodo.keywords
            and len(nodo.args) == 1
        ):
            return _FUNCIONES_PERMITIDAS[nodo.func.id](evaluar(nodo.args[0]))

        raise ValueError("Expresión no permitida")

    return evaluar(arbol.body)


def ejecutar_calculadora(comando: str) -> str:
    try:
        texto = comando.strip().lower()

        if texto.startswith("raiz"):
            texto = f"sqrt({texto.removeprefix('raiz').strip()})"
        elif texto.startswith("pot"):
            partes = texto.split()
            if len(partes) != 3:
                raise ValueError("Potencia inválida")
            texto = f"({partes[1]}) ** ({partes[2]})"

        resultado = _evaluar_expresion(texto.replace("^", "**"))
        return f"🧮 {resultado}"
    except (ArithmeticError, SyntaxError, TypeError, ValueError):
        return "Operación inválida 😅"
