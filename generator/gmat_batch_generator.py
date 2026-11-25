#!/usr/bin/env python3
"""
LunaRadSat - GMAT batch generator (grid search sui burn fraction).

Parte da uno script GMAT di riferimento e genera una griglia di script
variando i burn fraction. I file di output sono nominati come si aspettano
gli analizzatori del repo:

  --mode transfer : variabili BF1, BF2          -> <outdir>/Risultato_<BF1>_<BF2>.csv   (analizzatore.py)
  --mode sk       : variabili BF_Apo, BF_Per    -> <outdir>/SK_<BF_Apo>_<BF_Per>.csv    (analizzatoreSK.py)

Esempi
------
python gmat_batch_generator.py --mode transfer -t ../LRS_LT_Transfer_0.367_0.411.script \
    --results-dir "C:/Users/.../output/GridSearch" -o runs_transfer

python gmat_batch_generator.py --mode sk -t ../SK_0.46_0.46.script \
    --results-dir "C:/Users/.../output/GridSearch_SK" -o runs_sk \
    --bf1 0.1:0.1:0.5 --bf2 0.1:0.1:0.5 \
    --run --gmat "C:/GMAT/bin/GmatConsole.exe" --jobs 4
"""
import argparse
import csv
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PureWindowsPath

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

MODES = {
    "transfer": dict(var1="BF1", var2="BF2", report="SummaryFile", prefix="Risultato",
                     prog="analizzatore.py"),
    "sk": dict(var1="BF_Apo", var2="BF_Per", report="SK_Report", prefix="SK",
               prog="analizzatoreSK.py"),
}

# Colonne che analizzatore.py legge dal file Risultato_*.csv (separatore ';')
TRANSFER_ADD = ("{LRS1.ElapsedDays, DeltaV, FuelConsumed, LRS1.LunaMJ2000Eq.INC, "
                "LRS1.LunaMJ2000Eq.AOP, LRS1.LunaMJ2000Eq.RAAN, AltApo, AltPer}")


def parse_range(spec):
    """'start:step:stop' (estremi inclusi) oppure lista 'a,b,c'."""
    if ":" in spec:
        a, s, b = (float(x) for x in spec.split(":"))
        return [round(a + i * s, 10) for i in range(int(round((b - a) / s)) + 1)]
    return [float(x) for x in spec.split(",")]


def fmt(v):
    """0.1 -> '0.1', 0.46 -> '0.46' (come float() nei nomi file degli analizzatori)."""
    return f"{v:g}"


def set_var(text, name, value):
    pat = re.compile(rf"(^[ \t]*(?:GMAT[ \t]+)?{re.escape(name)}[ \t]*=[ \t]*)({NUM})([ \t]*;)", re.M)
    return pat.subn(lambda m: f"{m.group(1)}{value:.6g}{m.group(3)}", text)


def set_prop(text, obj, prop, new_value_literal):
    """Sostituisce 'obj.prop = <qualsiasi>;' (una riga)."""
    pat = re.compile(rf"^([ \t]*(?:GMAT[ \t]+)?{re.escape(obj)}\.{re.escape(prop)}[ \t]*=[ \t]*)[^;\n]*;",
                     re.M)
    return pat.subn(lambda m: f"{m.group(1)}{new_value_literal};", text)


def gmat_path(p):
    # GMAT accetta '/' anche su Windows; evita problemi di escape nelle stringhe
    return str(p).replace("\\", "/")


def run_one(gmat, script, timeout):
    log = script.with_suffix(".log")
    with open(log, "w") as f:
        try:
            r = subprocess.run([gmat, "--run", str(script)], stdout=f,
                               stderr=subprocess.STDOUT, timeout=timeout)
            return script.name, r.returncode
        except subprocess.TimeoutExpired:
            return script.name, "TIMEOUT"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=MODES, required=True)
    ap.add_argument("-t", "--template", required=True, type=Path)
    ap.add_argument("-o", "--outdir", default="runs", type=Path, help="dove salvare gli script generati")
    ap.add_argument("--results-dir", required=True,
                    help="cartella dove GMAT scrivera' i CSV (quella letta dall'analizzatore)")
    ap.add_argument("--bf1", default="0.1:0.1:0.5", help="BF1 / BF_Apo: start:step:stop oppure a,b,c")
    ap.add_argument("--bf2", default="0.1:0.1:0.5", help="BF2 / BF_Per")
    ap.add_argument("--var1"); ap.add_argument("--var2")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--gmat", default="GmatConsole")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--timeout", type=float)
    a = ap.parse_args()

    cfg = MODES[a.mode]
    v1, v2 = a.var1 or cfg["var1"], a.var2 or cfg["var2"]
    with open(a.template, encoding="utf-8", errors="replace", newline="") as fh:
        tpl = fh.read()   # newline="" preserva CRLF/LF originali

    for v in (v1, v2):
        if set_var(tpl, v, 0.0)[1] == 0:
            sys.exit(f"ERRORE: '{v} = <numero>;' non trovato nel template.")
    if set_prop(tpl, cfg["report"], "Filename", "''")[1] == 0:
        sys.exit(f"ERRORE: '{cfg['report']}.Filename' non trovato nel template.")

    a.outdir.mkdir(parents=True, exist_ok=True)
    manifest = []
    scripts = []
    for b1 in parse_range(a.bf1):
        for b2 in parse_range(a.bf2):
            txt, _ = set_var(tpl, v1, b1)
            txt, _ = set_var(txt, v2, b2)
            csvname = f"{cfg['prefix']}_{fmt(b1)}_{fmt(b2)}.csv"
            out = gmat_path(Path(a.results_dir) / csvname) if "\\" not in a.results_dir \
                else gmat_path(PureWindowsPath(a.results_dir) / csvname)
            txt, _ = set_prop(txt, cfg["report"], "Filename", f"'{out}'")
            if a.mode == "transfer":
                # formato atteso da analizzatore.py: ';' come separatore, colonne Days..AltPer
                txt, _ = set_prop(txt, "SummaryFile", "Delimiter", "';'")
                txt, _ = set_prop(txt, "SummaryFile", "Add", TRANSFER_ADD)
            p = a.outdir / f"{a.template.stem.split('_0.')[0]}_{fmt(b1)}_{fmt(b2)}.script"
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(txt)
            scripts.append(p)
            manifest.append({"script": p.name, "csv": csvname, v1: b1, v2: b2})

    with open(a.outdir / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0]))
        w.writeheader(); w.writerows(manifest)
    print(f"Generati {len(scripts)} script in {a.outdir}/  ->  CSV in {a.results_dir}")
    print(f"Poi analizza con: python {cfg['prog']}")

    if a.run:
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for name, rc in ex.map(lambda s: run_one(a.gmat, s, a.timeout), scripts):
                print(f"  {name}: {'OK' if rc == 0 else f'FAIL ({rc})'}")


if __name__ == "__main__":
    main()
