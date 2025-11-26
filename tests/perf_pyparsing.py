# Python
import time
import random
import statistics as stats
from typing import Callable

import pyparsing as pp

# ---------- Utilities ----------


def bench(
    name: str, fn: Callable[[], None], iters: int = 4
) -> tuple[str, float, float, list[float]]:

    # one cold run (ignored) to warm caches/JIT-like paths
    fn()

    times = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append(t1 - t0)

    mean = stats.mean(times)
    stdev = stats.pstdev(times) if len(times) > 1 else 0.0
    print(f"{name},{mean:.6f},{stdev:.6f},{iters}")
    return name, mean, stdev, times


def with_packrat(enabled: bool):
    pp.ParserElement.disable_memoization()
    if enabled:
        pp.ParserElement.enable_packrat(force=True)
    assert pp.ParserElement._packratEnabled == enabled


def with_left_recursion(enabled: bool):
    pp.ParserElement.disable_memoization()
    if enabled:
        pp.ParserElement.enable_left_recursion(force=True)


# ---------- Corpora generators ----------


def gen_csv(rows: int, cols: int, seed: int = 1) -> str:
    rnd = random.Random(seed)
    out = []
    for _ in range(rows):
        row = []
        for _ in range(cols):
            # mix of identifiers and quoted strings with commas inside sometimes
            if rnd.random() < 0.5:
                row.append("v" + str(rnd.randint(0, 10_000)))
            else:
                s = "t" + str(rnd.randint(0, 10_000))
                if rnd.random() < 0.2:
                    s += ",inner"
                row.append(f'"{s}"')
        out.append(",".join(row))
    return "\n".join(out)


def gen_expr_sequence(n_terms: int, seed: int = 2) -> str:
    rnd = random.Random(seed)
    ops = ["+", "-", "*", "/", "%"]

    def maybe_paren(term: str, prob: float = 0.25) -> str:
        # randomly wrap a term in parentheses
        return f"({term})" if rnd.random() < prob else term

    def make_term(depth: int) -> str:
        # base integer
        t = str(rnd.randint(0, 1000))
        # with some probability, turn it into a small subexpression
        if rnd.random() < 0.5 and depth < 3:
            # choose a small number of inner terms to keep size reasonable
            k = rnd.randint(2, 4)
            parts = [str(rnd.randint(0, 1000)) for _ in range(k)]
            expr = parts[0]
            for i in range(1, k):
                # occasionally recurse to build nested subexpressions
                if rnd.random() < 0.35:
                    next_part = make_term(depth + 1)
                else:
                    next_part = parts[i]
                expr += f" {rnd.choice(ops)} {next_part}"
            t = maybe_paren(expr, prob=0.8)
        return t

    # build outer expression with n_terms top-level numbers/subexpressions
    terms = [make_term(0) for _ in range(n_terms)]
    expr = terms[0]
    for i in range(1, n_terms):
        expr += f" {rnd.choice(ops)} {terms[i]}"
    # print(expr)
    return expr


def gen_log(n_lines: int, seed: int = 3) -> str:
    rnd = random.Random(seed)
    levels = ["INFO", "WARN", "ERROR", "DEBUG"]
    out = []
    for i in range(n_lines):
        lvl = levels[rnd.randint(0, 3)]
        msg = f"message_{rnd.randint(0, 9999)}"
        out.append(f"{i:06d} [{lvl}] {msg}")
    return "\n".join(out)


# ---------- Grammars ----------


def csv_grammar():
    quoted = pp.QuotedString('"', esc_quote='""', multiline=False)
    field = quoted | pp.Word(pp.printables, exclude_chars=",")
    row = pp.DelimitedList(field).set_name("row")
    doc = pp.OneOrMore(row)
    return doc


def arithmetic_grammar_left_recursive():
    # classic left-recursive arithmetic to exercise enable_left_recursion
    pp.ParserElement.enable_left_recursion(force=True)
    lpar, rpar = map(pp.Suppress, "()")
    E = pp.Forward("E")
    integer = pp.Word(pp.nums)#.add_parse_action(lambda t: int(t[0]))
    muldiv = pp.one_of("* / %")
    addsub = pp.one_of("+ -")
    T = pp.Forward("T")
    F = integer | lpar + E + rpar
    T <<= T + muldiv + F | F
    E <<= E + addsub + T | T
    return E


def arithmetic_grammar_non_recursive():
    integer = pp.Word(pp.nums)#.add_parse_action(lambda t: int(t[0]))
    expr = pp.infix_notation(
        integer,
        [
            (pp.one_of("+ -"), 1, pp.OpAssoc.RIGHT),  # unary
            (pp.one_of("!"), 1, pp.OpAssoc.LEFT),
            (pp.one_of("^"), 2, pp.OpAssoc.LEFT),
            (pp.one_of("* / %"), 2, pp.OpAssoc.LEFT),
            (pp.one_of("+ -"), 2, pp.OpAssoc.LEFT),
        ],
    )
    return expr


def log_grammar():
    level = pp.one_of("INFO WARN ERROR DEBUG")
    lbrack, rbrack = map(pp.Suppress, "[]")
    line = (
        pp.Word(pp.nums, exact=6)("seq")
        + lbrack
        + level("level")
        + rbrack
        + pp.rest_of_line("msg")
    )
    return line


# ---------- Tasks ----------


def bench_csv_parse(rows=3000, cols=8):
    text = gen_csv(rows, cols)
    g = csv_grammar()

    def run():
        g.parse_string(text, parse_all=True)

    return run


def bench_expr_parse(n_terms=200, use_left_recursion=False):
    text = gen_expr_sequence(n_terms)
    if use_left_recursion:
        g = arithmetic_grammar_left_recursive()
    else:
        g = arithmetic_grammar_non_recursive()

    def run():
        g.parse_string(text, parse_all=True)

    return run


def bench_scan_log(n_lines=20000):
    text = gen_log(n_lines)
    g = log_grammar()

    def run():
        # count matches via scan_string
        count = sum(1 for _ in g.scan_string(text))
        assert count == n_lines

    return run


def bench_transform_upper(n_lines=20000):
    # transform_string path + parse actions
    text = gen_log(n_lines)
    g = log_grammar()
    g.add_parse_action(
        lambda s, l, t: [t.seq, f"[{t.level}]", t.msg.upper()]
    )

    def run():
        g.transform_string(text)

    return run


def bench_matchfirst_vs_or(n_alts=2000, seed=4):
    rnd = random.Random(seed)
    # create many similar alternatives to stress dispatch
    alts = [pp.Literal(f"KW{rnd.randint(0, n_alts*2)}") for _ in range(n_alts)]
    text = " ".join(a.match for a in alts[: n_alts // 2])
    g_mf = pp.MatchFirst(alts)
    g_or = pp.Or(alts)

    def run_mf():
        for tok, s, e in g_mf.scan_string(text):
            pass

    def run_or():
        for tok, s, e in g_or.scan_string(text):
            pass

    return run_mf, run_or


def bench_packrat_effect(base_fn_factory: Callable[[], Callable[[], None]]):
    def run_packrat_on():
        with_packrat(True)
        base_fn_factory()()

    def run_packrat_off():
        with_packrat(False)
        base_fn_factory()()

    return run_packrat_on, run_packrat_off


# ---------- Main suite ----------


def main():
    from contextlib import redirect_stdout
    from datetime import timedelta, date
    from io import StringIO
    import sys
    import time
    import littletable as lt
    import os
    from pathlib import Path

    save_csv = StringIO()

    start = time.perf_counter()
    with redirect_stdout(save_csv):
        print("benchmark,mean_s,stdev,runs")

        # 1) CSV parse (packrat off/on)
        run_csv = bench_packrat_effect(lambda: bench_csv_parse())
        bench("csv_parse_packrat_on", run_csv[0])
        bench("csv_parse_packrat_off", run_csv[1])

        # 2) Expression parse via non-left recursion (packrat off/on)
        run_expr = bench_packrat_effect(lambda: bench_expr_parse(use_left_recursion=False))
        bench("expr_non_lr_packrat_on", run_expr[0])
        # omit from cumulative metrics
        # bench("expr_non_lr_packrat_off", run_expr[1])

        # 3) Expression parse via left recursion (left recursion on) – compare packrat separately
        with_left_recursion(True)
        bench("expr_lr_leftrec_on", bench_expr_parse(use_left_recursion=True))
        with_left_recursion(False)

        # 4) Scan-string over logs (tokenization pattern)
        bench("scan_log", bench_scan_log())

        # 5) transform_string with parse action
        bench("transform_upper", bench_transform_upper())

        # 6) MatchFirst vs Or dispatch
        run_mf, run_or = bench_matchfirst_vs_or()
        bench("matchfirst_many", run_mf)
        bench("or_many", run_or)

        # 7) Packrat overall toggle on a heavier CSV
        run_csv_heavy = bench_packrat_effect(lambda: bench_csv_parse(rows=8000, cols=10))
        bench("csv_heavy_packrat_on", run_csv_heavy[0], iters=3)
        bench("csv_heavy_packrat_off", run_csv_heavy[1])

    elapsed = time.perf_counter() - start
    print(f"\aTotal elapsed: {str(timedelta(seconds=elapsed))[:-5]}")

    results = save_csv.getvalue()
    benchmark_stats: lt.Table = lt.csv_import(results, transforms={"*": lt.Table.convert_numeric})
    benchmark_stats.compute_field(
        "date", lambda *args: f"{date.today():%Y-%m-%d}"
    )
    python_version = sys.version.partition(" ")[0]
    if not getattr(sys, "is_gil_enabled", 1):
        python_version += "t"
    benchmark_stats.compute_field("python_version", lambda *args: python_version)
    benchmark_stats.compute_field("pyparsing_version", lambda *args: pp.__version__)
    benchmark_stats.select("date python_version pyparsing_version *").present(width=120)

    print()
    exported_csv = benchmark_stats.csv_export(
        fieldnames="date python_version pyparsing_version benchmark mean_s stdev runs"
    )
    print(exported_csv)

    # Optional: append results to a consolidated CSV file if requested.
    # Usage options:
    #   - pass command-line option:  --append-csv <path-to-csv>
    #   - or set environment variable PERF_PYPARSING_CSV to a file path
    append_csv_path = None
    if "--append-csv" in sys.argv:
        try:
            idx = sys.argv.index("--append-csv")
            append_csv_path = sys.argv[idx + 1]
        except (ValueError, IndexError):
            print("warning: --append-csv specified without a path; ignoring", file=sys.stderr)
            append_csv_path = None
    elif os.getenv("PERF_PYPARSING_CSV"):
        append_csv_path = os.getenv("PERF_PYPARSING_CSV")

    if append_csv_path:
        out_path = Path(append_csv_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # If the file already exists and is non-empty, skip the header from this export
        try:
            file_exists = out_path.exists() and out_path.stat().st_size > 0
        except OSError:
            file_exists = False

        lines = exported_csv.splitlines()
        if file_exists and lines:
            # drop header line
            lines = [ln for i, ln in enumerate(lines) if i != 0]

        # Append the (possibly headerless) lines to the file
        if lines:
            with out_path.open("a", encoding="utf-8", newline="") as fp:
                fp.write("\n".join(lines))
                fp.write("\n")


if __name__ == "__main__":
    main()
