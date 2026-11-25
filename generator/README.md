# GMAT batch generator

Genera una griglia di script GMAT variando i burn fraction e (opzionalmente) li lancia in batch con `GmatConsole`.
I CSV prodotti hanno i nomi attesi dagli analizzatori del repo.

| Modo | Template | Variabili | Output | Analisi |
|---|---|---|---|---|
| `transfer` | `LRS_LT_Transfer_*.script` | `BF1`, `BF2` | `Risultato_<BF1>_<BF2>.csv` (`;`) | `analizzatore.py` |
| `sk` | `SK_*.script` | `BF_Apo`, `BF_Per` | `SK_<BF_Apo>_<BF_Per>.csv` | `analizzatoreSK.py` |

```bash
# Transfer: griglia 0.1:0.1:0.5 su BF1 e BF2 (25 script)
python generator/gmat_batch_generator.py --mode transfer \
    -t LRS_LT_Transfer_0.367_0.411.script \
    --results-dir "C:/path/output/GridSearch" -o runs_transfer

# Stationkeeping + esecuzione batch in parallelo
python generator/gmat_batch_generator.py --mode sk -t SK_0.46_0.46.script \
    --results-dir "C:/path/output/GridSearch_SK" -o runs_sk \
    --bf1 0.1:0.1:0.5 --bf2 0.1:0.1:0.5 \
    --run --gmat "C:/GMAT/bin/GmatConsole.exe" --jobs 4
```

Gli intervalli sono `start:step:stop` (estremi inclusi) oppure liste `a,b,c`.
Viene scritto anche `manifest.csv` (script, CSV, valori BF) e, con `--run`, un `.log` per ogni run.

Il generatore modifica solo: i valori dei burn fraction, `Filename` del report di output e,
in modo `transfer`, `Delimiter` e `Add` del `SummaryFile` (colonne lette da `analizzatore.py`).
