import pandas as pd
import glob
import os

# --- CONFIGURAZIONE PERCORSI ---
cartella_csv = r'C:\Users\crist\OneDrive\Documenti\PoliTo\output\GridSearch'
file_excel_finale = r'C:\Users\crist\OneDrive\Documenti\PoliTo\Analisi_Ottimizzata_Ciclica.xlsx'

colonne_gmat = ['Days', 'DeltaV', 'FuelConsumed', 'INC', 'AOP', 'RAAN', 'AltApo', 'AltPer']

# Funzione per calcolare la distanza minima su un cerchio di 360 gradi
def distanza_angolare(valore, target):
    diff = abs(valore - target) % 360
    return diff if diff <= 180 else 360 - diff

files = glob.glob(os.path.join(cartella_csv, "Risultato_*.csv"))
database = []

for f in files:
    try:
        df = pd.read_csv(f, sep=';', decimal='.', header=None, skiprows=1, names=colonne_gmat, engine='python')
        if not df.empty:
            record = df.iloc[0].to_dict()
            nome_file = os.path.basename(f).replace('.csv', '').split('_')
            record['BF1'] = float(nome_file[1])
            record['BF2'] = float(nome_file[2])
            database.append(record)
    except Exception as e:
        print(f"Errore nel file {f}: {e}")

if database:
    df_f = pd.DataFrame(database)
    for col in df_f.columns:
        df_f[col] = pd.to_numeric(df_f[col], errors='coerce')

    # --- CALCOLO ERRORI CON LOGICA CICLICA ---
    
    # 1. Errore Quote (Lineare, non ciclico)
    df_f['Err_Quote'] = abs(df_f['AltApo'] - 4000) + abs(df_f['AltPer'] - 100)
    
    # 2. Errori Angolari Ciclici
    df_f['Err_INC']  = df_f['INC'].apply(lambda x: distanza_angolare(x, 86))
    df_f['Err_AOP']  = df_f['AOP'].apply(lambda x: distanza_angolare(x, 270))
    df_f['Err_RAAN'] = df_f['RAAN'].apply(lambda x: distanza_angolare(x, 0))

    # Somma degli errori angolari (Priorità 3)
    df_f['Err_Parametri_Orbitali'] = df_f['Err_INC'] + df_f['Err_AOP'] + df_f['Err_RAAN']

    # --- ORDINAMENTO GERARCHICO ---
    df_risultato = df_f.sort_values(by=[
        'Err_Quote', 
        'FuelConsumed', 
        'DeltaV', 
        'Days', 
        'Err_Parametri_Orbitali'
    ])

    # Riordino colonne per l'Excel
    ordine_col = [
        'BF1', 'BF2', 'Err_Quote', 'AltApo', 'AltPer', 
        'FuelConsumed', 'DeltaV', 'Days', 
        'Err_INC', 'Err_AOP', 'Err_RAAN', 'Err_Parametri_Orbitali'
    ]
    df_risultato = df_risultato[[c for c in ordine_col if c in df_risultato.columns]]

    df_risultato.to_excel(file_excel_finale, index=False)
    
    print("\n" + "="*60)
    print("ANALISI CICLICA COMPLETATA")
    print(f"I parametri INC, AOP e RAAN sono ora trattati come angoli su 360°.")
    print("="*60)