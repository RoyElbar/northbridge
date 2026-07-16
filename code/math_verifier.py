#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
math_verifier.py — the verification contract, as a minimal runnable harness.

This is the checker half of the system's "generator never grades its own work"
rule: a claimed mathematical result is re-derived symbolically in a fresh
process, and the verdict is one of exactly three words. The full system wraps
this contract in an agent (see artifacts/agent-definition.md); the mathematical
core is what you see here.

Usage:
  python3.11 math_verifier.py "diff(sin(x**2), x)" "2*x*cos(x**2)"
      -> VERIFIED

  python3.11 math_verifier.py "integrate(2*x, x)" "x**2 + 7"
      -> REFUTED: difference simplifies to -7

  python3.11 math_verifier.py "solve(x**2 - 4, x)" "[-2, 2]"
      -> VERIFIED (set comparison for solution lists)

Exit codes: 0 = VERIFIED, 1 = REFUTED, 2 = UNCLEAR (could not check mechanically).
The caller treats anything but 0 as "do not ship the claim".
"""

import sys

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

# Symbols available to claims. The real harness builds this from the claim's context.
SYMS = {name: sp.Symbol(name) for name in "abcdknmstuvwxyz"}
ENV = {**SYMS, **{f: getattr(sp, f) for f in (
    "sin", "cos", "tan", "exp", "log", "sqrt", "diff", "integrate",
    "limit", "solve", "simplify", "Matrix", "det", "oo", "pi", "I", "E",
)}, "e": sp.E}  # bare "e" means Euler's number, not a free symbol


def evaluate(expr: str):
    return parse_expr(expr, local_dict=ENV, transformations=TRANSFORMS, evaluate=True)


def verdict(computed: str, claimed: str) -> tuple[str, int]:
    try:
        a, b = evaluate(computed), evaluate(claimed)
    except Exception as e:
        return f"UNCLEAR: could not parse mechanically ({e})", 2

    try:
        if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
            if not (isinstance(a, (list, tuple)) and isinstance(b, (list, tuple))):
                return "UNCLEAR: one side is a solution list, the other is not", 2
            if set(map(sp.simplify, a)) == set(map(sp.simplify, b)):
                return "VERIFIED", 0
            return f"REFUTED: solution sets differ: {sorted(map(str, a))} vs {sorted(map(str, b))}", 1
        delta = sp.simplify(a - b)
    except Exception as e:
        return f"UNCLEAR: could not compare symbolically ({e})", 2

    if delta == 0:
        return "VERIFIED", 0
    return f"REFUTED: difference simplifies to {delta}", 1


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    msg, code = verdict(sys.argv[1], sys.argv[2])
    print(msg)
    sys.exit(code)


if __name__ == "__main__":
    main()
