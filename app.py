import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Bubble Resilience Screener", page_icon="📈", layout="centered")

st.title("Bubble Resilience Screener")
st.caption("Benchmark any stock against Dot-Com and AI market extremes using direct SEC/Yahoo financial tables.")

ticker_input = st.text_input("Enter Stock Ticker Symbol:", value="NVDA").upper().strip()

def evaluate_company(net_cash, ebitda, pe):
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
        with st.spinner(f"Fetching financial data for {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                
                # Fetch price from reliable chart history
                hist = stock.history(period="5d")
                current_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0

                # 1. NET CASH EXTRACTION
                total_cash_and_investments = 0.0
                total_debt = 0.0
                
                bs = stock.balance_sheet
                if not bs.empty:
                    for key in ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash Financial"]:
                        if key in bs.index:
                            total_cash_and_investments = float(bs.loc[key].iloc[0])
                            break
                    for key in ["Total Debt", "Long Term Debt And Capital Lease Obligation"]:
                        if key in bs.index:
                            total_debt = float(bs.loc[key].iloc[0])
                            break

                net_cash_m = (total_cash_and_investments - total_debt) / 1e6

                # 2. EBITDA EXTRACTION (Trailing 4 quarters or latest annual)
                ebitda = None
                q_inc = stock.quarterly_income_stmt
                if not q_inc.empty:
                    for key in ["EBITDA", "Operating Income", "Gross Profit"]:
                        if key in q_inc.index:
                            ebitda = float(q_inc.loc[key].iloc[:4].sum())
                            break
                
                if ebitda is None or ebitda == 0.0:
                    inc = stock.income_stmt
                    if not inc.empty:
                        for key in ["EBITDA", "Operating Income", "Gross Profit"]:
                            if key in inc.index:
                                ebitda = float(inc.loc[key].iloc[0])
                                break

                ebitda_m = (float(ebitda) / 1e6) if ebitda is not None else 0.0

                # 3. DIRECT TRAILING GAAP P/E CALCULATION
                pe_ratio = None
                
                # Method A: Calculate sum of EPS over trailing 4 quarters
                if not q_inc.empty:
                    for eps_key in ["Diluted EPS", "Basic EPS"]:
                        if eps_key in q_inc.index:
                            trailing_eps = float(q_inc.loc[eps_key].iloc[:4].sum())
                            if trailing_eps > 0 and current_price > 0:
                                pe_ratio = current_price / trailing_eps
                                break

                # Method B: Fallback to annual diluted EPS
                if pe_ratio is None:
                    inc = stock.income_stmt
                    if not inc.empty:
                        for eps_key in ["Diluted EPS", "Basic EPS"]:
                            if eps_key in inc.index:
                                annual_eps = float(inc.loc[eps_key].iloc[0])
                                if annual_eps > 0 and current_price > 0:
                                    pe_ratio = current_price / annual_eps
                                    break

                # Method C: Check fast_info fallback
                if pe_ratio is None:
                    try:
                        mcap = float(stock.fast_info.get("market_cap") or 0.0)
                        if not q_inc.empty and "Net Income" in q_inc.index:
                            trailing_net_inc = float(q_inc.loc["Net Income"].iloc[:4].sum())
                            if trailing_net_inc > 0 and mcap > 0:
                                pe_ratio = mcap / trailing_net_inc
                    except Exception:
                        pass

                company_name = ticker_input

                # Run evaluation
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
