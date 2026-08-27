import streamlit as st
import yfinance as yf

# Page Setup
st.set_page_config(page_title="Bubble Resilience Screener", page_icon="📈", layout="centered")

st.title("Bubble Resilience Screener")
st.caption("Benchmark any stock against Dot-Com and AI market extremes using direct SEC/Yahoo financial tables.")

# Search Input
ticker_input = st.text_input("Enter Stock Ticker Symbol:", value="NVDA").upper().strip()

def evaluate_company(net_cash, ebitda, pe):
    """Evaluates stock fundamentals against dot-com survival profiles."""
    if net_cash < 0 and ebitda < 0:
        return {
            "status": "red",
            "badge": "🔴 High Fragility (Red)",
            "title": "Dot-Com Crash Fragility",
            "desc": "The company is burning cash while holding negative net cash. Without sustained external capital, this mirrors classic dot-com casualty profiles.",
            "parallel": "Pets.com / Webvan (1999)",
            "parallel_notes": "Deep operating deficits combined with insufficient cash runway to survive a market downturn."
        }
    elif ebitda < 0 and net_cash > 0:
        return {
            "status": "yellow",
            "badge": "🟡 Speculative Burn (Yellow)",
            "title": "Speculative Burn (High Cash Runway)",
            "desc": "The company is operating at an EBITDA loss but holds a net cash balance to self-fund near-term expansion.",
            "parallel": "Amazon (1999) / Priceline (1999)",
            "parallel_notes": "Heavy growth investments suppressing earnings, sustained by existing balance sheet reserves."
        }
    elif ebitda > 0 and net_cash < 0:
        return {
            "status": "yellow",
            "badge": "🟡 Caution / Leveraged (Yellow)",
            "title": "Leveraged Operating Producer",
            "desc": "Generates positive operating cash flow, but net debt exposure creates sensitivity to interest rates and credit markets.",
            "parallel": "Super Micro Computer / Telecom Survivors",
            "parallel_notes": "Operating profit offsets debt obligations, but balance sheet flexibility is constrained."
        }
    else:  # Net Cash >= 0 and EBITDA >= 0
        if pe is not None and 0 < pe <= 60:
            return {
                "status": "green",
                "badge": "🟢 Resilient Leader (Green)",
                "title": "Durable Fundamental Leader",
                "desc": "Strong cash surplus, positive core operating profits, and a grounded trailing GAAP valuation.",
                "parallel": "NVIDIA / Microsoft / TSMC",
                "parallel_notes": "Defensive balance sheet paired with high cash generation and reasonable pricing multiples."
            }
        elif pe is not None and pe > 60:
            return {
                "status": "yellow",
                "badge": "🟡 Valuation Stretched (Yellow)",
                "title": "Fundamental Winner (Stretched Multiple)",
                "desc": "Solid cash and positive EBITDA, but trailing GAAP multiple prices in aggressive forward execution.",
                "parallel": "Palantir / AMD / eBay (1999)",
                "parallel_notes": "Solid operational foundation, but trading at premium growth multiples."
            }
        else:
            return {
                "status": "yellow",
                "badge": "🟡 Profitable Baseline (Yellow)",
                "title": "Profitable Baseline (Multiple Non-Meaningful)",
                "desc": "Positive cash reserves and operating earnings, though GAAP net losses or missing data make P/E non-meaningful.",
                "parallel": "eBay (Q2 1999 baseline)",
                "parallel_notes": "Positive operational capture with early-stage net income fluctuations."
            }

if st.button("Evaluate Stock", type="primary") or ticker_input:
    if ticker_input:
        with st.spinner(f"Fetching verified financial statements for {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                
                # 1. Fetch real-time / latest closing price
                hist = stock.history(period="5d")
                current_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0

                # 2. Extract Net Cash (Cash + Short Term Investments - Total Debt)
                total_cash_and_investments = 0.0
                total_debt = 0.0
                
                bs = stock.balance_sheet
                if not bs.empty:
                    cash_keys = [
                        "Cash Cash Equivalents And Short Term Investments",
                        "Cash And Cash Equivalents",
                        "Cash Financial"
                    ]
                    for key in cash_keys:
                        if key in bs.index:
                            total_cash_and_investments = float(bs.loc[key].iloc[0])
                            break
                    for key in ["Total Debt", "Long Term Debt And Capital Lease Obligation"]:
                        if key in bs.index:
                            total_debt = float(bs.loc[key].iloc[0])
                            break

                net_cash_m = (total_cash_and_investments - total_debt) / 1e6

                # 3. Extract True EBITDA (Operating Income + Depreciation & Amortization over TTM)
                ebitda = None
                q_inc = stock.quarterly_income_stmt
                q_cf = stock.quarterly_cash_flow
                
                if not q_inc.empty and "Operating Income" in q_inc.index:
                    trailing_op_inc = float(q_inc.loc["Operating Income"].iloc[:4].sum())
                    
                    da = 0.0
                    if not q_cf.empty:
                        for da_key in ["Depreciation And Amortization", "Depreciation & Amortization", "Depreciation"]:
                            if da_key in q_cf.index:
                                da = float(q_cf.loc[da_key].iloc[:4].sum())
                                break
                    
                    ebitda = trailing_op_inc + da
                elif not q_inc.empty and "EBITDA" in q_inc.index:
                    ebitda = float(q_inc.loc["EBITDA"].iloc[:4].sum())
                else:
                    # Fallback to annual statement if quarterly is unavailable
                    inc = stock.income_stmt
                    if not inc.empty and "Operating Income" in inc.index:
                        ebitda = float(inc.loc["Operating Income"].iloc[0])

                ebitda_m = (float(ebitda) / 1e6) if ebitda is not None else 0.0

                # 4. Trailing GAAP P/E Calculation
                pe_ratio = None
                
                if not q_inc.empty:
                    for eps_key in ["Diluted EPS", "Basic EPS"]:
                        if eps_key in q_inc.index:
                            trailing_eps = float(q_inc.loc[eps_key].iloc[:4].sum())
                            if trailing_eps > 0 and current_price > 0:
                                pe_ratio = current_price / trailing_eps
                                break

                # Fallback to annual diluted EPS
                if pe_ratio is None:
                    inc = stock.income_stmt
                    if not inc.empty:
                        for eps_key in ["Diluted EPS", "Basic EPS"]:
                            if eps_key in inc.index:
                                annual_eps = float(inc.loc[eps_key].iloc[0])
                                if annual_eps > 0 and current_price > 0:
                                    pe_ratio = current_price / annual_eps
                                    break

                company_name = ticker_input

                # Run evaluation logic
                result = evaluate_company(net_cash_m, ebitda_m, pe_ratio)

                # UI Display
                st.markdown("---")
                if result["status"] == "green":
                    st.success(f"### {result['badge']}\n**{company_name} ({ticker_input})** — {result['title']}")
                elif result["status"] == "yellow":
                    st.warning(f"### {result['badge']}\n**{company_name} ({ticker_input})** — {result['title']}")
                else:
                    st.error(f"### {result['badge']}\n**{company_name} ({ticker_input})** — {result['title']}")

                st.write(result["desc"])
                st.info(f"**Historical Parallel:** {result['parallel']}\n\n*{result['parallel_notes']}*")

                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="Net Cash (Cash - Debt)",
                        value=f"${net_cash_m:,.1f}M",
                        delta="Positive Cushion" if net_cash_m >= 0 else "Net Debt",
                        delta_color="normal" if net_cash_m >= 0 else "inverse"
                    )

                with col2:
                    st.metric(
                        label="EBITDA (TTM)",
                        value=f"${ebitda_m:,.1f}M",
                        delta="Profitable" if ebitda_m >= 0 else "Deficit",
                        delta_color="normal" if ebitda_m >= 0 else "inverse"
                    )

                with col3:
                    pe_display = f"{pe_ratio:.1f}x" if (pe_ratio is not None and pe_ratio > 0) else "N/M (Loss)"
                    st.metric(
                        label="Trailing GAAP P/E",
                        value=pe_display,
                        delta="Grounding <= 60x" if (pe_ratio and 0 < pe_ratio <= 60) else "Elevated / Speculative",
                        delta_color="normal" if (pe_ratio and 0 < pe_ratio <= 60) else "off"
                    )

            except Exception as e:
                st.error(f"Could not retrieve data for '{ticker_input}'. Error: {e}")
