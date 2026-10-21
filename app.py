"""Dashboard: precios y mercado de modelos de IA (datos LiteLLM, licencia MIT).

Correr:  streamlit run app.py
Requiere haber corrido antes clean_data.py (genera la carpeta output/).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

OUT = Path(__file__).parent / "output"
IN, OUTP = "input_price_per_1m_tokens", "output_price_per_1m_tokens"

# Paleta
INDIGO, VIOLET, CYAN, EMERALD, AMBER, ROSE, GREY = (
    "#4F46E5", "#7C3AED", "#06B6D4", "#10B981", "#F59E0B", "#F43F5E", "#94A3B8")
SERIES = [INDIGO, ROSE, EMERALD, AMBER, VIOLET, CYAN, "#EC4899", "#84CC16"]

st.set_page_config(page_title="Mercado de modelos de IA", page_icon="📊", layout="wide")

# ───────────── Estilos ─────────────
st.markdown(f"""
<style>
.block-container {{ padding-top: 4rem; max-width: 1280px; }}

/* Banner */
.hero {{ background: linear-gradient(120deg, {INDIGO} 0%, {VIOLET} 55%, #DB2777 100%);
        border-radius: 20px; padding: 28px 34px; margin-bottom: 22px; color: #fff;
        box-shadow: 0 10px 30px rgba(79,70,229,.30); }}
.hero h1 {{ margin: 0; font-size: 2.1rem; font-weight: 800; color: #fff; padding: 0; }}
.hero p {{ margin: 6px 0 0; opacity: .88; font-size: .98rem; }}

/* Tarjetas KPI */
.kpi {{ border-radius: 18px; padding: 20px 24px; color: #fff; position: relative; overflow: hidden;
       box-shadow: 0 8px 22px rgba(0,0,0,.16); }}
.kpi .icon {{ position: absolute; right: 18px; top: 10px; font-size: 2.8rem; opacity: .28; }}
.kpi .label {{ font-size: .88rem; font-weight: 600; letter-spacing: .04em;
              text-transform: uppercase; opacity: .92; }}
.kpi .value {{ font-size: 2.7rem; font-weight: 800; line-height: 1.15; margin-top: 4px; }}

/* Solapas */
[role="tablist"] {{ gap: 12px !important; padding: 6px 2px 14px !important;
        border-bottom: none !important; box-shadow: none !important; }}
[role="tab"] {{ height: auto !important; padding: 12px 30px !important; border-radius: 999px !important;
        background: rgba(127,127,127,.14) !important; transition: all .15s ease; cursor: pointer; }}
[role="tab"]:hover {{ background: rgba(124,58,237,.24) !important; }}
[role="tab"] p {{ font-size: 1.08rem !important; font-weight: 700 !important; white-space: nowrap; }}
[role="tab"][aria-selected="true"] {{ background: linear-gradient(120deg, {INDIGO}, {VIOLET}) !important;
        box-shadow: 0 6px 16px rgba(79,70,229,.38); }}
[role="tab"][aria-selected="true"] p {{ color: #fff !important; }}
.react-aria-SelectionIndicator, [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display: none !important; }}

/* Barra lateral */
section[data-testid="stSidebar"] {{ border-right: 3px solid {VIOLET}; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load():
    m = pd.read_csv(OUT / "models_clean.csv", parse_dates=["first_listed_week", "deprecation_date"])
    evol = pd.read_csv(OUT / "evolucion_trimestral.csv")
    evol_dev = pd.read_csv(OUT / "evolucion_trimestral_por_desarrollador.csv")
    cambios = pd.read_csv(OUT / "cambios_de_precio.csv", parse_dates=["week_start"])
    return m, evol, evol_dev, cambios


m, evol, evol_dev, cambios = load()


def style(fig, h=380):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=50, b=10), legend_title_text="",
                      title_font=dict(size=16), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", bargap=0.18)
    fig.update_xaxes(gridcolor="rgba(127,127,127,.18)")
    fig.update_yaxes(gridcolor="rgba(127,127,127,.18)")
    return fig


def cuatrimestre(dates: pd.Series) -> pd.Series:
    """Cuatrimestre calendario: C1 = ene-abr, C2 = may-ago, C3 = sep-dic."""
    year = dates.dt.year.astype("Int64").astype(str)
    cuat = ((dates.dt.month - 1) // 4 + 1).astype("Int64").astype(str)
    return (year + " C" + cuat).where(dates.notna())


def fmt(n) -> str:
    return f"{n:,.0f}".replace(",", ".")


# ───────────── Sidebar: filtros ─────────────
st.sidebar.header("🎛️ Filtros")
devs = sorted(m["developer"].dropna().unique())
countries = sorted(m["developer_country"].dropna().unique())
sel_dev = st.sidebar.multiselect("Desarrollador", devs, placeholder="Todos")
sel_country = st.sidebar.multiselect("País del desarrollador", countries, placeholder="Todos")
hide_dep = st.sidebar.checkbox("Ocultar modelos deprecados", value=False)
st.sidebar.caption("Los filtros afectan KPIs, mercado y precios. "
                   "En *Evolución*, los desarrolladores elegidos se comparan contra el total.")

f = m.copy()
if sel_dev:
    f = f[f["developer"].isin(sel_dev)]
if sel_country:
    f = f[f["developer_country"].isin(sel_country)]
if hide_dep:
    f = f[~f["is_deprecated"]]

chat = f[(f["mode"] == "chat") & f["has_token_price"] & ~f["is_free"]].copy()
chat["out_in_ratio"] = chat[OUTP] / chat[IN].where(chat[IN] > 0)

# ───────────── Encabezado y KPIs ─────────────
st.markdown("""
<div class="hero">
  <h1>📊 Mercado de modelos de IA</h1>
  <p>Precios y evolución · Fuente: catálogo LiteLLM (Berri AI, MIT) · datos hasta septiembre de 2026 ·
     precios en USD por millón de tokens, modelos de chat</p>
</div>
""", unsafe_allow_html=True)

if f.empty:
    st.warning("Los filtros no dejan ningún modelo. Probá con otra combinación.")
    st.stop()


def kpi(col, icon, label, value, c1, c2):
    col.markdown(f'<div class="kpi" style="background:linear-gradient(135deg,{c1},{c2})">'
                 f'<div class="icon">{icon}</div><div class="label">{label}</div>'
                 f'<div class="value">{value}</div></div>', unsafe_allow_html=True)


k = st.columns(3)
kpi(k[0], "🤖", "Modelos únicos", fmt(f["model_name"].nunique()), INDIGO, "#6366F1")
kpi(k[1], "🏢", "Desarrolladores", fmt(f["developer"].nunique()), VIOLET, "#A855F7")
kpi(k[2], "🌐", "Proveedores", fmt(f["provider"].nunique()), "#0891B2", CYAN)
st.write("")

tab_mercado, tab_precios, tab_evol = st.tabs(["🌍  Mercado", "💰  Precios", "📈  Evolución"])

# ───────────── Mercado ─────────────
with tab_mercado:
    c1, c2 = st.columns(2)
    top_n = c1.slider("Cantidad de desarrolladores a mostrar", 5, 25, 12)
    by_dev = (f.dropna(subset=["developer"]).groupby("developer")["model_name"].nunique()
                .nlargest(top_n).sort_values().reset_index(name="modelos"))
    fig = px.bar(by_dev, x="modelos", y="developer", orientation="h", text="modelos",
                 color="modelos", color_continuous_scale=[CYAN, INDIGO, VIOLET],
                 title="Modelos únicos por desarrollador")
    fig.update_coloraxes(showscale=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="", yaxis_title="")
    c1.plotly_chart(style(fig, 460), width="stretch")

    by_country = (f.dropna(subset=["developer_country"]).groupby("developer_country")["model_name"]
                    .nunique().sort_values().reset_index(name="modelos"))
    fig = px.bar(by_country, x="modelos", y="developer_country", orientation="h", text="modelos",
                 color="modelos", color_continuous_scale=[AMBER, ROSE, VIOLET],
                 title="Modelos únicos por país")
    fig.update_coloraxes(showscale=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="", yaxis_title="")
    c2.plotly_chart(style(fig, 460), width="stretch")

    by_mode = f.groupby("mode")["model_name"].nunique().sort_values(ascending=False).reset_index(name="modelos")
    fig = px.bar(by_mode, x="mode", y="modelos", text="modelos", color="mode",
                 color_discrete_sequence=SERIES, title="Modelos únicos por tipo")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
    st.plotly_chart(style(fig, 340), width="stretch")

# ───────────── Precios ─────────────
with tab_precios:
    if chat.empty:
        st.info("No hay modelos de chat con precio para los filtros elegidos.")
    else:
        c1, c2 = st.columns(2)

        # Histograma en escala log: se agrupa en log10 y se rotulan los ejes en USD
        vals = chat.loc[chat[OUTP] > 0, OUTP]
        lo, hi = np.log10(vals.min()), np.log10(vals.max())
        edges = np.linspace(lo, hi + 1e-9, 31)
        counts, _ = np.histogram(np.log10(vals), bins=edges)
        centers = (edges[:-1] + edges[1:]) / 2
        hover = [f"${10 ** a:.3g} – ${10 ** b:.3g}<br>{c} modelos"
                 for a, b, c in zip(edges[:-1], edges[1:], counts)]
        fig = go.Figure(go.Bar(x=centers, y=counts, width=(edges[1] - edges[0]) * 0.92,
                               marker=dict(color=counts, colorscale=[CYAN, INDIGO, VIOLET]),
                               hovertext=hover, hoverinfo="text"))
        ticks = [t for t in [0.01, 0.1, 1, 10, 100, 1000] if lo - 0.3 <= np.log10(t) <= hi + 0.3]
        fig.update_xaxes(tickvals=[np.log10(t) for t in ticks], ticktext=[f"${t:g}" for t in ticks],
                         title="USD por millón de tokens (escala logarítmica)")
        fig.update_layout(title="Distribución del precio de salida", yaxis_title="modelos")
        c1.plotly_chart(style(fig), width="stretch")

        ratio = chat["out_in_ratio"].dropna()
        fig = px.histogram(ratio[ratio <= ratio.quantile(0.98)], nbins=30,
                           title="Cuántas veces más cuesta la salida que la entrada")
        fig.update_traces(marker_color=EMERALD)
        fig.update_layout(xaxis_title="salida / entrada (veces)", yaxis_title="modelos", showlegend=False)
        c2.plotly_chart(style(fig), width="stretch")

        min_models = st.slider("Mínimo de modelos para comparar", 1, 20, 5,
                               help="Evita medianas armadas con 1 o 2 modelos.")
        grp = st.radio("Comparar por", ["developer", "developer_country"], horizontal=True,
                       format_func=lambda x: "Desarrollador" if x == "developer" else "País")
        t = (chat.dropna(subset=[grp]).groupby(grp)
                 .agg(modelos=("model_name", "nunique"), entrada=(IN, "median"), salida=(OUTP, "median"))
                 .query("modelos >= @min_models").reset_index())
        if t.empty:
            st.info("Ningún grupo llega al mínimo de modelos. Bajá el mínimo.")
        else:
            t = t.melt(id_vars=[grp, "modelos"], value_vars=["entrada", "salida"],
                       var_name="tipo", value_name="usd")
            order = t[t["tipo"] == "salida"].sort_values("usd")[grp].tolist()
            fig = px.bar(t, x="usd", y=grp, color="tipo", barmode="group", hover_data=["modelos"],
                         category_orders={grp: order},
                         color_discrete_map={"entrada": CYAN, "salida": VIOLET},
                         title="Precio mediano de entrada y salida (USD por millón de tokens)")
            fig.update_layout(xaxis_title="", yaxis_title="")
            st.plotly_chart(style(fig, max(380, 26 * len(order) + 120)), width="stretch")
        st.caption("Se excluyen modelos gratuitos y sin precio por token. Se usa la mediana "
                   "porque hay precios extremos (hasta USD 600). En el gráfico de salida/entrada "
                   "se recorta el 2 % de valores más extremos para que se vea la forma.")

# ───────────── Evolución ─────────────
with tab_evol:
    metric = st.radio("Métrica", ["Precio de entrada", "Precio de salida", "Contexto", "Modelos disponibles"],
                      horizontal=True)
    col, unit = {"Precio de entrada": ("entrada_mediana", "USD por millón de tokens (mediana)"),
                 "Precio de salida": ("salida_mediana", "USD por millón de tokens (mediana)"),
                 "Contexto": ("contexto_mediano", "tokens de contexto (mediana)"),
                 "Modelos disponibles": ("modelos_disponibles", "modelos de chat")}[metric]

    g = evol[["trimestre", col]].assign(serie="Total mercado")
    if sel_dev and col != "modelos_disponibles":
        dcol = col if col in evol_dev.columns else "modelos"
        d = evol_dev[evol_dev["developer"].isin(sel_dev)][["trimestre", "developer", dcol]]
        d = d.rename(columns={"developer": "serie", dcol: col})
        g = pd.concat([g, d])
    fig = px.line(g, x="trimestre", y=col, color="serie", markers=True,
                  color_discrete_sequence=SERIES, color_discrete_map={"Total mercado": GREY},
                  title=f"{metric} por trimestre")
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.update_layout(yaxis_title=unit, xaxis_title="")
    st.plotly_chart(style(fig, 440), width="stretch")

    c1, c2 = st.columns(2)
    cb = cambios.assign(sentido=lambda d: d["variacion_pct"].apply(lambda v: "Baja" if v < 0 else "Suba"))
    cb["cuatrimestre"] = cuatrimestre(cb["week_start"])
    cnt = cb.groupby(["cuatrimestre", "sentido"]).size().reset_index(name="cambios")
    fig = px.bar(cnt, x="cuatrimestre", y="cambios", color="sentido", barmode="group",
                 color_discrete_map={"Baja": EMERALD, "Suba": ROSE},
                 title="Cambios de precio de salida por cuatrimestre")
    fig.update_layout(xaxis_title="Cuatrimestre", yaxis_title="cambios")
    c1.plotly_chart(style(fig), width="stretch")

    altas = (m.assign(cuatrimestre=cuatrimestre(m["first_listed_week"]))
               .groupby("cuatrimestre")["model_name"].nunique().reset_index(name="modelos_nuevos"))
    fig = px.bar(altas, x="cuatrimestre", y="modelos_nuevos", color="modelos_nuevos",
                 color_continuous_scale=[AMBER, ROSE, VIOLET],
                 title="Modelos nuevos en el catálogo por cuatrimestre")
    fig.update_coloraxes(showscale=False)
    fig.update_layout(xaxis_title="Cuatrimestre", yaxis_title="modelos nuevos")
    c2.plotly_chart(style(fig), width="stretch")
    st.caption("Cuatrimestres: C1 = ene–abr, C2 = may–ago, C3 = sep–dic. El 2026 C3 está incompleto "
               "(los datos llegan hasta fines de septiembre). Además, 'primera aparición' es cuando el modelo "
               "entró al catálogo de LiteLLM, no su fecha de lanzamiento: los picos recientes probablemente "
               "reflejan cómo se recolectaron los datos.")
