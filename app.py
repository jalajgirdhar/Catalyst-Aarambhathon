"""StockWise - Streamlit app.   Run:  streamlit run app.py"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from stockwise.business import ALL as PROFILES, detect
from stockwise.data import clean_sales, last_sunday, make_demo
from stockwise.explain import explain
from stockwise.festivals import default_calendar, load_calendar
from stockwise.forecast import MODEL_LABEL, forecast_all, prophet_available
from stockwise.pipeline import build_plans, plans_table, prepare_inventory, read_inventory
from stockwise.simulate import simulate, summarise
from stockwise.trends import claude_ideas, google_trends, own_signals, pilot_units

TEAL, PINK, BLUE, AMBER = "#2dd4bf", "#ff4fa0", "#38bdf8", "#fbbf24"

st.set_page_config(page_title="StockWise", page_icon="📦", layout="wide")


def show_df(df, **kw):
    try:
        st.dataframe(df, hide_index=True, width="stretch", **kw)
    except Exception:
        st.dataframe(df, hide_index=True, use_container_width=True, **kw)


def show_fig(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def get_api_key():
    try:
        k = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets file
        k = None
    return k or os.environ.get("ANTHROPIC_API_KEY")


# ------------------------------------------------------------------ cached heavy work
@st.cache_data(show_spinner=False)
def cached_demo(end_date: str, kind: str, stores: int):
    return make_demo(end_date, kind=kind, stores=stores)


@st.cache_data(show_spinner="Forecasting every product...")
def cached_forecasts(wide, cal, horizon, use_prophet, meta, seed):
    return forecast_all(wide, cal, horizon, use_prophet, meta, seed)


@st.cache_data(show_spinner="Replaying the last 12 weeks...")
def cached_sim(wide, lead, cost, cal, service, gut_buffer):
    return simulate(wide, lead, cost, cal, 12, service, gut_buffer)


def read_any(f):
    return pd.read_excel(f) if f.name.lower().endswith((".xlsx", ".xls")) else pd.read_csv(f)


# ------------------------------------------------------------------ sidebar: data
st.sidebar.markdown("## 📦 StockWise")
st.sidebar.caption("Right stock. Right time. Right decision.")
source = st.sidebar.radio("Sales data", ["Demo (synthetic)", "Upload my sheet"])

raw = inv_raw = None
sig = source
if source == "Demo (synthetic)":
    kind_label = st.sidebar.selectbox("Demo business", ["Ethnic wear boutique", "Grocery / kirana"])
    stores = 2 if st.sidebar.radio("Stores", ["1 store", "2 stores"], horizontal=True) == "2 stores" else 1
    scenario = st.sidebar.selectbox("Demo timing", ["Before Diwali (like Meera's case)", "Today"])
    end = "2027-09-12" if scenario.startswith("Before") else str(last_sunday().date())
    raw, inv_raw = cached_demo(end, "ethnic" if kind_label.startswith("Ethnic") else "grocery", stores)
    sig += f"{kind_label}{stores}{scenario}"
    st.sidebar.caption("Made-up data: 2 years, festival spikes, a few deliberate data errors.")
else:
    f_sales = st.sidebar.file_uploader("Sales sheet (date, product, units; optional store/company)",
                                       type=["csv", "xlsx", "xls"])
    f_inv = st.sidebar.file_uploader("Inventory sheet (optional: product, stock, lead_time_days, unit_cost, store)",
                                     type=["csv", "xlsx", "xls"])
    demo_raw, _ = cached_demo("2027-09-12", "ethnic", 2)
    st.sidebar.download_button("Download a sample sales sheet", demo_raw.head(300).to_csv(index=False),
                               "sample_sales.csv", "text/csv")
    if f_sales is None:
        st.title("StockWise")
        st.info("Upload a sales sheet with columns **date, product, units** (daily or weekly). Add a **store** column "
                "if you run more than one shop. An inventory sheet is optional: StockWise reads the product names "
                "to work out what kind of business you run. Or switch to the demo data on the left.")
        st.stop()
    raw = read_any(f_sales)
    inv_raw = read_any(f_inv) if f_inv is not None else None
    sig += f_sales.name + (f_inv.name if f_inv is not None else "")

cal = default_calendar()
with st.sidebar.expander("Festival calendar"):
    f_cal = st.file_uploader("Your own festivals.csv (festival, date)", type=["csv"], key="cal")
    if f_cal is not None:
        try:
            cal = load_calendar(pd.read_csv(f_cal))
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
    st.caption("Dates are approximate for lunar festivals. Check them for real use.")
drop_repeats = st.sidebar.checkbox("Remove accidentally repeated rows", True)

# ------------------------------------------------------------------ clean + detect business
try:
    cleaned = clean_sales(raw, cal, drop_repeats)
except ValueError as e:
    st.error(str(e))
    st.stop()

labels = list(cleaned.labels)
if inv_raw is not None:
    try:
        labels += list(read_inventory(inv_raw)["product"])
    except ValueError as e:
        st.error(str(e))
        st.stop()
det = detect(labels)

st.sidebar.markdown("### Business type")
keys = list(PROFILES)
biz_key = st.sidebar.selectbox("Detected automatically, change if wrong", keys, index=keys.index(det.profile.key),
                               format_func=lambda k: PROFILES[k].label, key=f"biz_{sig}")
prof = PROFILES[biz_key]

st.sidebar.markdown("### Settings")
service = st.sidebar.slider("How careful? (chance of not running out)", 80, 99, 95, format="%d%%") / 100
cover_days = st.sidebar.slider("Each order should cover (days of sales)", 3, 45, prof.cover, key=f"cover_{prof.key}")
slow_days = st.sidebar.slider("Call it slow stock above (days of stock)", 14, 180, prof.slow, key=f"slow_{prof.key}")
horizon = st.sidebar.slider("Forecast length (weeks)", 8, 16, 12)
use_prophet = st.sidebar.checkbox("Also try Prophet", False) if prophet_available() else False

# ------------------------------------------------------------------ pipeline
meta = cleaned.meta
multi = meta["company"].nunique() > 1
companies = sorted(meta["company"].unique())
label = {e: (f"{meta.loc[e, 'item']} ({meta.loc[e, 'company']})" if multi else meta.loc[e, "item"]) for e in meta.index}

fcs = cached_forecasts(cleaned.wide, cal, horizon, use_prophet, meta, prof.festivals)
inv0 = prepare_inventory(cleaned, inv_raw, prof.lead)

st.title("StockWise")
st.caption(f"Sales up to {cleaned.as_of - pd.Timedelta(days=1):%d %b %Y} · {len(meta)} product series"
           f"{f' across {len(companies)} companies' if multi else ''} · "
           f"{cleaned.wide.shape[0]} weeks of history · plan starts {cleaned.as_of:%d %b %Y}")

if prof.key == "general":
    st.warning("Could not tell what kind of business this is from the product names, so neutral defaults are used. "
              "You can pick a business type in the sidebar.")
else:
    why = f" Spotted from: {', '.join(det.matched)}." if det.matched and prof.key == det.profile.key else ""
    st.success(f"**Looks like: {prof.label}.**{why} Settings adapted: supplier time {prof.lead} days, each order covers "
               f"{prof.cover} days, slow stock above {prof.slow} days. {prof.note}")
    if prof.festivals:
        st.caption("Starting festival assumptions for products with little history: "
                   + ", ".join(f"{k} ×{v}" for k, v in prof.festivals.items())
                   + ". Your own sales replace these as soon as there is enough history.")

tab_names = ["🛒 Shopping list", "📈 Item forecast"] + (["🏬 Companies"] if multi else []) + \
            ["💡 New product ideas", "🧪 Does it work?", "🧹 Data check"]
tabs = dict(zip(tab_names, st.tabs(tab_names)))

with tabs["🛒 Shopping list"]:
    st.markdown("**Your numbers.** Change anything you disagree with (stock, supplier days, a % change to the forecast, "
                "or type your own order quantity) and the whole plan updates.")
    inv = st.data_editor(
        inv0, key=f"inv_{sig}", hide_index=True, num_rows="fixed",
        disabled=["product", "item", "company"],
        column_order=(["company"] if multi else []) + ["item", "stock", "on_order", "lead_time_days", "unit_cost",
                                                        "forecast_change_pct", "my_order_qty"],
        column_config={
            "item": "Product",
            "company": "Company",
            "stock": st.column_config.NumberColumn("Stock on hand", min_value=0, step=1),
            "on_order": st.column_config.NumberColumn("Already on order", min_value=0, step=1),
            "lead_time_days": st.column_config.NumberColumn("Supplier days", min_value=0, max_value=120, step=1),
            "unit_cost": st.column_config.NumberColumn("Unit cost (Rs)", min_value=0, step=1),
            "forecast_change_pct": st.column_config.NumberColumn("Forecast change %", min_value=-90, max_value=300,
                                                                 step=5, help="Your gut feel on top of the forecast"),
            "my_order_qty": st.column_config.NumberColumn("My order qty", min_value=0, step=1,
                                                          help="Leave blank to use the suggestion"),
        },
    )
    plans = build_plans(inv, fcs, cleaned.dow, service, cover_days, slow_days)
    sel = "All"
    if multi:
        sel = st.selectbox("Show company", ["All"] + companies)
    view = [p for p in plans if sel == "All" or meta.loc[p.product, "company"] == sel]
    table = plans_table(view, meta)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Order now", sum(p.urgency == 0 for p in view))
    c2.metric("Order this week", sum(p.urgency == 1 for p in view))
    c3.metric("Total of these orders (Rs)", f"{sum(p.order_cost for p in view):,.0f}")
    c4.metric("Cash sitting in slow stock (Rs)", f"{sum(p.stock_value for p in view if p.slow):,.0f}")
    st.subheader("Shopping list, most urgent first")
    show_df(table)
    st.download_button("Download shopping list (CSV)", table.to_csv(index=False), "stockwise_shopping_list.csv", "text/csv")
    for p in view:
        if p.gap_days > 0:
            st.warning(f"**{label[p.product]}** will run out in about {p.cover_days:.0f} days but your supplier needs "
                       f"{p.lead_days}. Order now and expect a gap of roughly {p.gap_days:.0f} days.")
        if p.slow:
            st.info(f"**{label[p.product]}**: {p.cover_days if p.cover_days < 999 else '250+'} days of stock "
                    f"(Rs {p.stock_value:,.0f}). Hold new orders and consider a discount.")

by_name = {p.product: p for p in plans}
inv_by = inv.set_index("product")


def adj_of(e):
    return float(inv_by.loc[e, "forecast_change_pct"] or 0)


with tabs["📈 Item forecast"]:
    name = st.selectbox("Product", [p.product for p in plans], format_func=lambda e: label[e])
    fc, plan = fcs[name], by_name[name]
    adj = adj_of(name)
    k1, k2, k3 = st.columns(3)
    k1.metric("Reorder by", "No order needed" if plan.reorder_date is None else f"{plan.reorder_date:%d %b}")
    k2.metric("Order qty", plan.final_qty)
    k3.metric("Stock cover", ">250 days" if plan.cover_days >= 999 else f"{plan.cover_days:.0f} days")

    hist = fc.history.iloc[-16:]
    mean = fc.mean * (1 + adj / 100)
    low, high = fc.low * (1 + adj / 100), fc.high * (1 + adj / 100)
    hx = [d.strftime("%d %b") for d in hist.index]
    fx = [d.strftime("%d %b") for d in fc.weeks]
    fig = go.Figure()
    fig.add_bar(x=hx, y=hist.values, name="Past sales", marker_color=BLUE)
    fig.add_bar(x=fx, y=mean, name="Forecast", marker_color=AMBER,
                error_y=dict(type="data", symmetric=False, array=high - mean, arrayminus=mean - low, color="#94a3b8"))
    seen = set()
    for i, t in enumerate(fc.future_tags):
        if t is not None and t[0] not in seen:
            seen.add(t[0])
            fig.add_annotation(x=fx[i], y=float(high[i]), text=t[0], showarrow=True, arrowhead=2, ay=-30,
                               font=dict(color=PINK))
    if plan.reorder_in_days is not None:
        j = min(plan.reorder_in_days // 7, len(fx) - 1)
        fig.add_annotation(x=fx[j], y=0, text=f"▲ reorder by {plan.reorder_date:%d %b}", showarrow=False,
                           yshift=-28, font=dict(color=TEAL))
    fig.update_layout(title=f"{label[name]}: weekly units (bars on the forecast show the likely range)",
                      barmode="group", height=430, margin=dict(t=60, b=50), legend=dict(orientation="h", y=1.1))
    show_fig(fig)

    st.subheader("Why we suggest this")
    for lab, color, text in explain(fc, plan, adj):
        st.markdown(f"<span style='color:{color};font-weight:700'>{lab}:</span> {text}", unsafe_allow_html=True)
    st.caption("To disagree, edit the numbers in the Shopping list tab. The plan updates straight away.")

if multi:
    with tabs["🏬 Companies"]:
        st.markdown("**Each company forecast on its own**, then rolled up. A product that is new in one store "
                    "borrows the festival pattern of the same product in your other stores.")
        rows = []
        for comp in companies:
            ps = [p for p in plans if meta.loc[p.product, "company"] == comp]
            nxt4 = sum(float(np.sum(fcs[p.product].mean[:4])) * (1 + adj_of(p.product) / 100) for p in ps)
            rows.append({"Company": comp, "Products": len(ps),
                         "Order now / this week": sum(p.urgency <= 1 for p in ps),
                         "Orders total (Rs)": round(sum(p.order_cost for p in ps)),
                         "Cash in slow stock (Rs)": round(sum(p.stock_value for p in ps if p.slow)),
                         "Expected sales, next 4 weeks (units)": round(nxt4)})
        show_df(pd.DataFrame(rows))

        fig3 = go.Figure()
        palette = [BLUE, PINK, TEAL, AMBER, "#8b5cf6"]
        wk_fut = [d.strftime("%d %b") for d in next(iter(fcs.values())).weeks]
        for ci, comp in enumerate(companies):
            ents = list(meta.index[meta["company"] == comp])
            h = cleaned.wide[ents].sum(axis=1).iloc[-16:]
            f_ = np.sum([fcs[e].mean * (1 + adj_of(e) / 100) for e in ents], axis=0)
            col = palette[ci % len(palette)]
            fig3.add_scatter(x=[d.strftime("%d %b") for d in h.index], y=h.values, mode="lines", name=comp,
                             line=dict(color=col), legendgroup=comp)
            fig3.add_scatter(x=wk_fut, y=f_, mode="lines", name=f"{comp} forecast", line=dict(color=col, dash="dash"),
                             legendgroup=comp)
        fig3.update_layout(title="Weekly units per company: past (solid) and forecast (dashed)", height=420)
        show_fig(fig3)

        st.markdown("**Which store sells what** (expected units, next 4 weeks)")
        pv = {}
        for e in meta.index:
            pv.setdefault(meta.loc[e, "item"], {})[meta.loc[e, "company"]] = round(
                float(np.sum(fcs[e].mean[:4])) * (1 + adj_of(e) / 100))
        show_df(pd.DataFrame(pv).T.rename_axis("Product").reset_index())

with tabs["💡 New product ideas"]:
    pilot = pilot_units(cleaned.wide)
    st.markdown("**What new product could you add?** These are ideas to test with a small batch "
                f"(about **{pilot} units** to start), not sales forecasts: a product with no history cannot be forecast. "
                "Each idea shows the evidence behind it.")

    st.subheader("1. From your own sales")
    own = own_signals(fcs, meta)
    if own.empty:
        st.caption("No strong signals in your own sales yet.")
    else:
        show_df(own)

    st.subheader("2. What is trending outside your shop")
    seeds_txt = st.text_input("Keywords to check (up to 5, separated by commas)", ", ".join(prof.seeds),
                              key=f"seeds_{prof.key}")
    seeds = [s.strip() for s in seeds_txt.split(",") if s.strip()][:5]
    gcol, ccol = st.columns(2)

    with gcol:
        st.markdown("**Google Trends** (free, India)")
        if st.button("Check Google Trends"):
            with st.spinner("Asking Google Trends..."):
                st.session_state[f"gt_{prof.key}"] = google_trends(seeds)
        res = st.session_state.get(f"gt_{prof.key}")
        if res:
            ideas, _raw, err = res
            if err:
                st.warning(err)
            elif ideas.empty:
                st.caption("Nothing rising strongly for these keywords right now.")
            else:
                show_df(ideas)

    with ccol:
        st.markdown("**Claude with web search** (needs an API key; costs a little per run)")
        key = get_api_key()
        if not key:
            key = st.text_input("Anthropic API key", type="password", help="Kept only for this session. "
                                "On a deployed app, add ANTHROPIC_API_KEY to the app's secrets instead.")
        if st.button("Ask Claude what is trending", disabled=not key):
            first = next(iter(fcs.values()))
            fests = sorted({f"{t[0]} on {t[1]:%d %b}" for t in first.future_tags if t is not None})
            summary = "; ".join(f"{r.Idea} ({r.Evidence})" for r in own.head(5).itertuples()) if not own.empty else ""
            with st.spinner("Searching the web..."):
                st.session_state[f"cl_{prof.key}"] = claude_ideas(
                    key, prof.label, seeds, summary, ", ".join(fests), f"{pd.Timestamp.today():%d %b %Y}")
        res = st.session_state.get(f"cl_{prof.key}")
        if res:
            ideas, raw_text, err = res
            if err:
                st.warning(err)
            if not ideas.empty:
                show_df(ideas)
                st.caption("Generated by an AI model from web search results. Open the sources and judge for yourself before buying stock.")
            elif raw_text:
                st.text(raw_text)

with tabs["🧪 Does it work?"]:
    st.markdown("**How accurate are the forecasts?** Each model forecasts weeks it has not seen. "
                "Lower error is better. A plain 4-week average is the baseline to beat.")
    rows = []
    for fc_ in fcs.values():
        rows.append({"Product": label[fc_.product], "Model kept": MODEL_LABEL[fc_.model],
                     "Error % (MAPE)": None if fc_.mape is None else round(fc_.mape, 1),
                     "Plain average error %": None if fc_.baseline_mape is None else round(fc_.baseline_mape, 1),
                     "Error (units/week)": None if fc_.mae is None else round(fc_.mae, 1),
                     "Plain average (units/week)": None if fc_.baseline_mae is None else round(fc_.baseline_mae, 1),
                     "Weeks of history": len(fc_.history)})
    acc = pd.DataFrame(rows)
    show_df(acc)
    if acc["Error (units/week)"].notna().any():
        a, b = acc["Error (units/week)"].mean(), acc["Plain average (units/week)"].mean()
        st.metric("Average error vs plain average", f"{a:.1f} vs {b:.1f} units/week",
                  delta=f"{(a - b) / b * 100:.0f}%" if b else None, delta_color="inverse")
    st.caption("Products with under 14 weeks of history cannot be tested, so they use a simple method and a wider range.")

    st.markdown("---")
    st.markdown("**Order with StockWise vs ordering by gut feeling**, replayed on the last 12 weeks. "
                "Both start with the same stock and face the same real demand. "
                "Gut feeling here means: repeat the last 4 weeks' average plus a safety buffer.")
    gut_buffer = st.slider("Gut-feeling safety buffer", 0, 100, 25, format="%d%%") / 100
    if st.button("Run the replay"):
        lead = {p: float(v) for p, v in zip(inv["product"], inv["lead_time_days"])}
        cost = {p: float(v) for p, v in zip(inv["product"], inv["unit_cost"])}
        res = cached_sim(cleaned.wide, lead, cost, cal, service, gut_buffer)
        if res.empty:
            st.warning("Need at least 28 weeks of history per product for this replay.")
        else:
            s = summarise(res)
            show_df(s.rename(columns={"policy": "Method", "lost_sales_units": "Sales lost (units)",
                                      "avg_unsold_units": "Average unsold stock (units)",
                                      "avg_stock_value": "Average stock value (Rs)",
                                      "fill_rate_pct": "Customers served %"}).round(1))
            fig2 = go.Figure()
            res["label"] = res["product"].map(label)
            for pol, col in [("Gut feeling", PINK), ("StockWise", TEAL)]:
                d = res[res.policy == pol]
                fig2.add_bar(x=d["label"], y=d["lost_sales_units"], name=pol, marker_color=col)
            fig2.update_layout(title="Sales lost to stock-outs (units, lower is better)", barmode="group", height=380)
            show_fig(fig2)
            st.caption("Synthetic data, so treat the numbers as a demo of the method. A higher 'how careful' setting "
                       "means fewer stock-outs but more stock on the shelf.")

with tabs["🧹 Data check"]:
    st.markdown("**What the cleaner found and fixed**")
    n = cleaned.notes
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Repeated rows removed", n.get("repeated_rows_removed", 0))
    d2.metric("Odd spikes capped", n.get("odd_spikes_capped", 0))
    d3.metric("Empty weeks set to 0", n.get("empty_weeks_filled_with_zero", 0))
    d4.metric("Unreadable rows dropped", n.get("unreadable_rows_dropped", 0) + n.get("negative_rows_dropped", 0))
    st.caption("Weekday pattern used (Mon to Sun): " + ", ".join(str(x) for x in n["weekday_pattern"]))
    ups = pd.DataFrame({label[c]: {k: round(v, 2) for k, v in f.uplifts.items() if k != "_all"}
                        for c, f in fcs.items()}).T
    st.markdown("**How much each product sells in the run-up to each festival (1.0 = normal, 1.5 = 50% more)**")
    show_df(ups.rename_axis("Product").reset_index())
    st.markdown("**Weekly sales (last 12 weeks)**")
    show_df(cleaned.wide.iloc[-12:].rename(columns=label).rename_axis("Week starting").reset_index().round(0))
