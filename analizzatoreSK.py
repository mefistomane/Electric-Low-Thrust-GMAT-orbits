import pandas as pd
import numpy as np
import glob
import os

# =============================================================================
# ANALISI GRID SEARCH - STATIONKEEPING (LRS1)
# Ranking gerarchico su tutta la serie temporale:
#   1. Deviazione quote (AltApo da 4000 km, AltPer da 100 km)
#   2. Deviazione inclinazione (rispetto al valore iniziale)
#   3. DeltaV totale e Fuel consumato
# =============================================================================

# --- PERCORSI ---
cartella_csv      = r'C:\Users\crist\OneDrive\Documenti\PoliTo\output\GridSearch_SK'
file_excel_finale = r'C:\Users\crist\OneDrive\Documenti\PoliTo\Analisi_GridSearch_SK.xlsx'

# --- COLONNE GMAT (nomi esatti dal CSV) ---
COL_DAYS      = 'LRS1.ElapsedDays'
COL_ECC       = 'LRS1.Luna.ECC'
COL_RAD_APO   = 'LRS1.Luna.RadApo'
COL_RAD_PER   = 'LRS1.Luna.RadPer'
COL_INC       = 'LRS1.LunaMJ2000Eq.INC'        # corretto
COL_FUEL_MASS = 'LRS1.ElectricTank1.FuelMass'
COL_BURNS     = 'BurnCount'
COL_DELTAV    = 'DeltaV'
COL_FUEL_CONS = 'FuelConsumed'

# Raggio medio lunare [km] — se GMAT restituisce già altitudini, imposta 0
R_LUNA = 1737.4

# --- TARGET ORBITALI ---
TARGET_ALT_APO = 4000.0   # km
TARGET_ALT_PER = 100.0    # km

# =============================================================================
# CARICAMENTO E ANALISI FILE
# =============================================================================
files = glob.glob(os.path.join(cartella_csv, "SK_*.csv"))
print(f"File trovati: {len(files)}")

database = []

for f in files:
    try:
        # sep='\s+' splitta su qualsiasi sequenza di spazi/tab,
        # gestisce i CSV GMAT con colonne a larghezza fissa separate da spazi
        df = pd.read_csv(f, sep=r'\s+', decimal='.', engine='python')
        df.columns = df.columns.str.strip()

        # Rimuovi righe di intestazione duplicate (GMAT le reinserisce a volte)
        df = df[df[COL_DAYS] != COL_DAYS].copy()

        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=[COL_DAYS, COL_RAD_APO, COL_RAD_PER, COL_INC]).reset_index(drop=True)

        if len(df) < 2:
            print(f"  WARN: {os.path.basename(f)} — righe insufficienti, skip.")
            continue

        # Conversione raggi → altitudini su tutta la serie
        df['AltApo'] = df[COL_RAD_APO] - R_LUNA
        df['AltPer'] = df[COL_RAD_PER] - R_LUNA

        # INC iniziale = target da mantenere
        inc_iniziale = df[COL_INC].iloc[0]

        # ── DEVIAZIONE QUOTE su ogni istante ──────────────────────────────
        df['Dev_AltApo'] = (df['AltApo'] - TARGET_ALT_APO).abs()
        df['Dev_AltPer'] = (df['AltPer'] - TARGET_ALT_PER).abs()
        df['Dev_Quote']  = df['Dev_AltApo'] + df['Dev_AltPer']

        # ── DEVIAZIONE INC su ogni istante (ciclica 360°) ─────────────────
        diff = (df[COL_INC] - inc_iniziale).abs() % 360
        df['Dev_INC'] = diff.where(diff <= 180, 360 - diff)

        # ── METRICHE AGGREGATE ────────────────────────────────────────────
        finale = df.iloc[-1]

        nome_parts = os.path.basename(f).replace('.csv', '').split('_')
        bf_apo = float(nome_parts[1])
        bf_per = float(nome_parts[2])

        database.append({
            'BF_Apo':           bf_apo,
            'BF_Per':           bf_per,
            # Deviazione quote
            'Dev_Quote_Mean':   round(df['Dev_Quote'].mean(), 3),
            'Dev_Quote_Max':    round(df['Dev_Quote'].max(), 3),
            'Dev_AltApo_Mean':  round(df['Dev_AltApo'].mean(), 3),
            'Dev_AltApo_Max':   round(df['Dev_AltApo'].max(), 3),
            'Dev_AltPer_Mean':  round(df['Dev_AltPer'].mean(), 3),
            'Dev_AltPer_Max':   round(df['Dev_AltPer'].max(), 3),
            # Range effettivo quote
            'AltApo_Min':       round(df['AltApo'].min(), 2),
            'AltApo_Max':       round(df['AltApo'].max(), 2),
            'AltPer_Min':       round(df['AltPer'].min(), 2),
            'AltPer_Max':       round(df['AltPer'].max(), 2),
            'AltApo_Fin':       round(finale['AltApo'], 2),
            'AltPer_Fin':       round(finale['AltPer'], 2),
            # Deviazione INC
            'Dev_INC_Mean':     round(df['Dev_INC'].mean(), 5),
            'Dev_INC_Max':      round(df['Dev_INC'].max(), 5),
            'INC_Init':         round(inc_iniziale, 5),
            'INC_Fin':          round(finale[COL_INC], 5),
            # Propellente e prestazioni
            'DeltaV_Tot':       round(finale[COL_DELTAV], 4),
            'FuelConsumed':     round(finale[COL_FUEL_CONS], 4),
            'FuelMass_Fin':     round(finale[COL_FUEL_MASS], 4),
            'BurnCount':        int(finale[COL_BURNS]),
            'ElapsedDays':      round(finale[COL_DAYS], 2),
        })

    except Exception as e:
        print(f"  ERRORE in {os.path.basename(f)}: {e}")

print(f"Record validi: {len(database)}")

# =============================================================================
# RANKING GERARCHICO
# =============================================================================
if database:
    df_r = pd.DataFrame(database)

    # Normalizza su [0,1] rispetto al range della griglia
    def norm(serie):
        r = serie.max() - serie.min()
        return (serie - serie.min()) / r if r > 0 else pd.Series(np.zeros(len(serie)), index=serie.index)

    # Score composito — logica gerarchica con pesi espliciti
    #   Priorità 1 — Quote:       55%  (media 40% + picco 15%)
    #   Priorità 2 — INC:         30%  (media 22% + picco 8%)
    #   Priorità 3 — DeltaV/Fuel: 15%  (deltav 8% + fuel 7%)
    df_r['S_Q_Mean']  = norm(df_r['Dev_Quote_Mean'])   * 0.40
    df_r['S_Q_Max']   = norm(df_r['Dev_Quote_Max'])    * 0.15
    df_r['S_I_Mean']  = norm(df_r['Dev_INC_Mean'])     * 0.22
    df_r['S_I_Max']   = norm(df_r['Dev_INC_Max'])      * 0.08
    df_r['S_DV']      = norm(df_r['DeltaV_Tot'])       * 0.08
    df_r['S_Fuel']    = norm(df_r['FuelConsumed'])     * 0.07

    df_r['Score'] = (df_r['S_Q_Mean'] + df_r['S_Q_Max'] +
                     df_r['S_I_Mean'] + df_r['S_I_Max'] +
                     df_r['S_DV']     + df_r['S_Fuel']).round(4)

    df_sorted = df_r.sort_values('Score').reset_index(drop=True)
    df_sorted.index += 1
    df_sorted.index.name = 'Rank'

    colonne_export = [
        'BF_Apo', 'BF_Per', 'Score',
        'Dev_Quote_Mean', 'Dev_Quote_Max',
        'Dev_AltApo_Mean', 'Dev_AltApo_Max',
        'Dev_AltPer_Mean', 'Dev_AltPer_Max',
        'AltApo_Min', 'AltApo_Max', 'AltPer_Min', 'AltPer_Max',
        'AltApo_Fin', 'AltPer_Fin',
        'Dev_INC_Mean', 'Dev_INC_Max', 'INC_Init', 'INC_Fin',
        'DeltaV_Tot', 'FuelConsumed', 'FuelMass_Fin',
        'BurnCount', 'ElapsedDays',
    ]
    df_export = df_sorted[[c for c in colonne_export if c in df_sorted.columns]]

    with pd.ExcelWriter(file_excel_finale, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Ranking', index=True)
        df_export.head(5).to_excel(writer, sheet_name='Top5', index=True)

    print(f"\n✓ Excel salvato: {file_excel_finale}")

    # --- REPORT CONSOLE ---
    sep = "─" * 80
    print(f"\n{'='*80}")
    print("  GRID SEARCH SK — RANKING STABILITÀ ORBITALE")
    print(f"  Pesi: Quote 55%  |  INC 30%  |  ΔV+Fuel 15%")
    print(f"{'='*80}")
    print(f"\n{'Rank':<5} {'BF_Apo':<8} {'BF_Per':<8} "
          f"{'DevQ_Mean':>10} {'DevQ_Max':>10} "
          f"{'DevINC_Mean':>12} {'ΔV(m/s)':>9} {'Fuel(kg)':>9} {'Score':>7}")
    print(sep)
    for i, row in df_export.iterrows():
        print(f"{i:<5} {row['BF_Apo']:<8} {row['BF_Per']:<8} "
              f"{row['Dev_Quote_Mean']:>10.2f} {row['Dev_Quote_Max']:>10.2f} "
              f"{row['Dev_INC_Mean']:>12.4f} {row['DeltaV_Tot']:>9.4f} "
              f"{row['FuelConsumed']:>9.4f} {row['Score']:>7.4f}")

    best = df_export.iloc[0]
    print(f"\n{sep}")
    print(f"  BEST → BF_Apo={best['BF_Apo']}  /  BF_Per={best['BF_Per']}  (Score={best['Score']:.4f})")
    print(f"  Quote:   Dev_mean={best['Dev_Quote_Mean']:.2f} km   Dev_max={best['Dev_Quote_Max']:.2f} km")
    print(f"           AltApo [{best['AltApo_Min']:.0f}–{best['AltApo_Max']:.0f}] km  (target {TARGET_ALT_APO:.0f})")
    print(f"           AltPer [{best['AltPer_Min']:.0f}–{best['AltPer_Max']:.0f}] km  (target {TARGET_ALT_PER:.0f})")
    print(f"  INC:     Dev_mean={best['Dev_INC_Mean']:.4f}°   Dev_max={best['Dev_INC_Max']:.4f}°")
    print(f"  ΔV:      {best['DeltaV_Tot']:.4f} m/s   Fuel: {best['FuelConsumed']:.4f} kg   Residuo: {best['FuelMass_Fin']:.4f} kg")
    print(f"{sep}\n")

else:
    print("❌ Nessun file trovato. Verifica il percorso.")