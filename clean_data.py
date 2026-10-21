"""Limpieza y tablas de métricas para el dashboard de precios de modelos de IA.

Entrada : data/ai_models_2026.csv y data/ai_model_price_history.csv  (fuente: LiteLLM, MIT)
Salida  : carpeta output/ con CSVs listos para graficar
"""
from pathlib import Path
import pandas as pd

# Rutas relativas a la carpeta del script, así funciona en cualquier computadora:
#   proyecto/
#     clean_data.py
#     data/    <- poner acá los dos CSV descargados de Kaggle
#     output/  <- se crea sola
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

MODELS_CSV = DATA / "ai_models_2026.csv"
HISTORY_CSV = DATA / "ai_model_price_history.csv"
for f in (MODELS_CSV, HISTORY_CSV):
    if not f.exists():
        raise SystemExit(f"Falta el archivo {f}. Copiá ahí los CSV descargados de Kaggle.")

IN, OUTP = "input_price_per_1m_tokens", "output_price_per_1m_tokens"

# ───────────────────────── 1. CARGA Y LIMPIEZA ─────────────────────────
m = pd.read_csv(MODELS_CSV,
                parse_dates=["first_listed_week", "deprecation_date"])
h = pd.read_csv(HISTORY_CSV,
                parse_dates=["week_start"])

# columnas que no usamos en este dashboard
m = m.drop(columns=[c for c in m.columns if c.startswith("supports_")]
           + ["source_url", "price_per_image", "input_price_per_second",
              "output_price_per_second"])

# texto: espacios y mayúsculas consistentes
for df in (m, h):
    for c in ["model_name", "developer", "provider", "mode"]:
        df[c] = df[c].astype(str).str.strip()
m["developer_country"] = m["developer_country"].str.strip()

# "Other"/"Unknown" no son un desarrollador/país real: se marcan como NaN
m["developer"] = m["developer"].replace("Other", pd.NA)
m["developer_country"] = m["developer_country"].replace("Unknown", pd.NA)
h["developer"] = h["developer"].replace("Other", pd.NA)

# precios: negativos no tienen sentido; 0 = modelo gratuito (se marca, no se borra)
for c in [IN, OUTP]:
    m.loc[m[c] < 0, c] = pd.NA
    h.loc[h[c] < 0, c] = pd.NA
m["is_free"] = (m[IN] == 0) & (m[OUTP] == 0)
m["is_deprecated"] = m["deprecation_date"].notna()
m["has_token_price"] = m[IN].notna() & m[OUTP].notna()

# duplicados exactos
m = m.drop_duplicates(subset=["model_id"])
h = h.drop_duplicates(subset=["week_start", "model_id"])

m.to_csv(OUT / "models_clean.csv", index=False)

# vista de chat con precio (base para todo lo de precios)
chat = m[(m["mode"] == "chat") & m["has_token_price"] & ~m["is_free"]].copy()
chat["out_in_ratio"] = chat[OUTP] / chat[IN].where(chat[IN] > 0)

# ───────────────────────── 2. KPIs ─────────────────────────
kpis = pd.DataFrame({
    "metrica": ["modelos_unicos", "desarrolladores", "proveedores",
                "precio_mediano_entrada_chat", "precio_mediano_salida_chat",
                "pct_deprecados", "pct_gratuitos_chat"],
    "valor": [
        m["model_name"].nunique(),
        m["developer"].nunique(),
        m["provider"].nunique(),
        chat[IN].median(),
        chat[OUTP].median(),
        round(m["is_deprecated"].mean() * 100, 1),
        round(m.loc[m["mode"] == "chat", "is_free"].mean() * 100, 1),
    ],
})
kpis.to_csv(OUT / "kpis.csv", index=False)

# ───────────────────────── 3. MERCADO ─────────────────────────
# se cuenta por model_name único para no inflar con los revendedores
(m.dropna(subset=["developer"]).groupby("developer")["model_name"].nunique()
   .sort_values(ascending=False).rename("modelos").reset_index()
   .to_csv(OUT / "modelos_por_desarrollador.csv", index=False))

(m.dropna(subset=["developer_country"]).groupby("developer_country")["model_name"]
   .nunique().sort_values(ascending=False).rename("modelos").reset_index()
   .to_csv(OUT / "modelos_por_pais.csv", index=False))

(m.groupby("mode")["model_name"].nunique().sort_values(ascending=False)
   .rename("modelos").reset_index().to_csv(OUT / "modelos_por_tipo.csv", index=False))

# ───────────────────────── 4. PRECIOS ─────────────────────────
def resumen_precios(col):
    g = chat.dropna(subset=[col]).groupby(col)
    return (g.agg(modelos=("model_name", "nunique"),
                  entrada_mediana=(IN, "median"),
                  salida_mediana=(OUTP, "median"),
                  ratio_salida_entrada=("out_in_ratio", "median"))
              .query("modelos >= 5")          # evita medianas de 1-2 modelos
              .sort_values("salida_mediana", ascending=False).round(3).reset_index())

resumen_precios("developer").to_csv(OUT / "precios_por_desarrollador.csv", index=False)
resumen_precios("developer_country").to_csv(OUT / "precios_por_pais.csv", index=False)
chat[[ "model_name", "developer", IN, OUTP, "out_in_ratio"]].to_csv(
    OUT / "precios_distribucion_chat.csv", index=False)   # para histograma/boxplot log

# ───────────────────────── 5. EVOLUCIÓN EN EL TIEMPO ─────────────────────────
hc = h[(h["mode"] == "chat")].copy()
hc["trimestre"] = hc["week_start"].dt.to_period("Q").astype(str)

hc_priced = hc[hc[IN].notna() & (hc[IN] > 0)]
evol = (hc.groupby("trimestre").agg(modelos_disponibles=("model_id", "nunique"),
                                    contexto_mediano=("max_input_tokens", "median"))
          .join(hc_priced.groupby("trimestre").agg(entrada_mediana=(IN, "median"),
                                                  salida_mediana=(OUTP, "median")))
          .round(3).reset_index())
evol.to_csv(OUT / "evolucion_trimestral.csv", index=False)

# evolución por desarrollador (para filtrar en el dashboard)
(hc_priced.dropna(subset=["developer"])
   .groupby(["trimestre", "developer"])
   .agg(modelos=("model_id", "nunique"), entrada_mediana=(IN, "median"),
        salida_mediana=(OUTP, "median"), contexto_mediano=("max_input_tokens", "median"))
   .round(3).reset_index().to_csv(OUT / "evolucion_trimestral_por_desarrollador.csv", index=False))

# cambios de precio por modelo (salida), solo entre semanas consecutivas con dato
s = h[h[OUTP].notna()].sort_values(["model_id", "week_start"]).copy()
s["precio_anterior"] = s.groupby("model_id")[OUTP].shift()
s["variacion_pct"] = ((s[OUTP] / s["precio_anterior"] - 1) * 100).round(1)
cambios = s[(s["precio_anterior"] > 0) & (s[OUTP] != s["precio_anterior"])]
cambios[["week_start", "model_id", "model_name", "developer", "precio_anterior",
         OUTP, "variacion_pct"]].to_csv(OUT / "cambios_de_precio.csv", index=False)

# nuevos modelos por trimestre (según catálogo)
(m.assign(trimestre=m["first_listed_week"].dt.to_period("Q").astype(str))
   .groupby("trimestre")["model_name"].nunique().rename("modelos_nuevos")
   .reset_index().to_csv(OUT / "altas_por_trimestre.csv", index=False))

# ───────────────────────── CHEQUEOS ─────────────────────────
print(kpis.to_string(index=False))
print("\nCambios de precio:", len(cambios),
      "| bajas:", (cambios.variacion_pct < 0).sum(),
      "| subas:", (cambios.variacion_pct > 0).sum())
print("\n", evol.to_string(index=False))
print("\nArchivos:", sorted(p.name for p in OUT.iterdir()))
