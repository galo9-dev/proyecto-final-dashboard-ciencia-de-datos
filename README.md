# Mercado de modelos de IA — Dashboard

Dashboard interactivo en **Streamlit + Plotly** para explorar el mercado de modelos de IA: quién los desarrolla, cuánto cuestan y cómo evolucionaron los precios en el tiempo.

Los datos provienen del catálogo de [LiteLLM](https://github.com/BerriAI/litellm) (Berri AI, licencia MIT), descargados de Kaggle, y llegan hasta septiembre de 2026. Todos los precios están en **USD por millón de tokens** y, salvo aclaración, corresponden a modelos de chat.

<!-- Agregá acá una captura del dashboard:
![Dashboard](docs/screenshot.png)
-->

## Qué se puede ver

| Solapa               | Contenido                                                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Mercado**    | Modelos únicos por desarrollador, por país y por tipo (chat, embedding, etc.)                                                |
| **Precios**    | Distribución del precio de salida (escala log), relación salida/entrada y comparación de medianas por desarrollador o país |
| **Evolución** | Precio de entrada/salida, contexto y modelos disponibles por trimestre; cambios de precio y altas de modelos por cuatrimestre  |

**KPIs:** modelos únicos, desarrolladores y proveedores.
**Filtros (sidebar):** desarrollador, país del desarrollador y ocultar modelos deprecados.

## Estructura

```
.
├── app.py                          # Dashboard (Streamlit)
├── clean_data.py                   # Limpieza + generación de tablas de métricas
├── requirements.txt
├── Informe_Mercado_Modelos_IA.pdf  # Informe con las conclusiones
├── data/
│   ├── ai_models_2026.csv          # Catálogo de modelos
│   └── ai_model_price_history.csv  # Historial semanal de precios
└── output/                         # CSVs generados por clean_data.py
```

## Cómo correrlo

**1. Clonar e instalar dependencias**

```bash
git clone https://github.com/devmayra/<https://github.com/devmayra/Dashboard-Modelos-IA>.git
cd <Dashboard-Modelos-IA>
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
python -m pip install -r requirements.txt
```

**2. Datos**

Los dos CSV tienen que estar en la carpeta `data/`:

- `ai_models_2026.csv`
- `ai_model_price_history.csv`

**3. Generar las tablas de métricas**

```bash
python clean_data.py
```

Crea la carpeta `output/` con los CSV que consume el dashboard.

**4. Levantar el dashboard**

```bash
streamlit run app.py
```

## Decisiones de limpieza

`clean_data.py` aplica estas reglas antes de graficar:

- Se eliminan columnas que el dashboard no usa (`supports_*`, `source_url`, precios por imagen/segundo).
- Se normalizan espacios en los campos de texto.
- `Other` (desarrollador) y `Unknown` (país) se marcan como nulos: no son valores reales.
- Los precios negativos se descartan; un precio `0` se marca como modelo **gratuito** (no se borra).
- Se eliminan duplicados exactos (`model_id` en el catálogo; `week_start` + `model_id` en el historial).
- Los modelos se cuentan por `model_name` único para no inflar los números con revendedores.
- Las comparaciones de precio usan **mediana** (hay valores extremos, de hasta USD 600) y exigen un mínimo de modelos por grupo.

## Limitaciones

- 2026 C3 (sep–dic) está incompleto: los datos terminan a fines de septiembre.
- `first_listed_week` indica cuándo el modelo entró al catálogo de LiteLLM, **no** su fecha de lanzamiento; los picos recientes probablemente reflejan cómo se recolectaron los datos.
- El análisis de precios excluye modelos gratuitos y modelos sin precio por token.

## Tecnologías

Python · pandas · Streamlit · Plotly

## Datos y licencia

Fuente de los datos: catálogo de LiteLLM (MIT). Revisá la licencia del dataset de Kaggle antes de redistribuir los CSV.
