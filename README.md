# StockWise (Aarambhathon 2.0, PS 01)

Explainable demand forecasting + reorder planning for small sellers.

## Run (works offline once installed)
    pip install -r requirements.txt
    streamlit run app.py

Pick "Demo (synthetic)" on the left to see it straight away, or upload a sheet with columns
`date, product, units` (daily or weekly; names like item/qty also work). Optional stock sheet:
`product, stock, lead_time_days, unit_cost, on_order`.

## New in v2
- **Business detection** (`business.py`): reads product names (and any category column) from the sales and inventory
  files, labels the business, and adapts supplier time, order cover, slow-stock limit and starting festival assumptions.
  You can override it in the sidebar.
- **Per company / store**: add a `store` (or company, branch, outlet) column. Each product is forecast per store, rolled up
  on the Companies tab, and a product new in one store borrows the pattern of the same product in other stores.
- **New product ideas** (`trends.py`): (1) from your own sales, (2) Google Trends via pytrends, (3) Claude with web search.
  These are ideas to test with a small batch, not forecasts.

### Using the Claude source when deployed
Streamlit Cloud: app menu > Settings > Secrets, add `ANTHROPIC_API_KEY = "sk-ant-..."`.
Locally: `export ANTHROPIC_API_KEY=...` or paste it into the box in the app. Never commit the key to GitHub.

## How it maps to the deck
| Deck step | Code |
|---|---|
| 01 Collect / 02 Prepare | `stockwise/data.py` (clean, weekly series, weekday pattern), `stockwise/festivals.py` |
| 03 Forecast | `stockwise/forecast.py` (simple average vs festival-adjusted average vs ETS, optional Prophet; backtested) |
| 04 Plan | `stockwise/inventory.py` (SS = Z x sigma x sqrt(L), ROP = d x L + SS, order qty, slow-item flag) |
| 05 Explain | `stockwise/explain.py` |
| 06 Show | `app.py` (Streamlit + Plotly, editable table, CSV export) |
| "How we will know it works" | "Does it work?" tab + `stockwise/simulate.py` |

## Things to check before the demo
- Festival dates in `festivals.py` are approximate. Verify, or upload your own festivals.csv.
- Demo numbers are synthetic: describe them as a demo of the method, not as measured accuracy.
- The simple average is kept as the baseline and only wins if it is clearly better (it cannot see festivals coming).
