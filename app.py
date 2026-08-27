import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Bubble Resilience Screener", page_icon="📈", layout="centered")

st.title("Bubble Resilience Screener")
st.caption("Benchmark any stock against Dot-Com and AI market extremes using real-time Yahoo Finance data.")

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
    else:  # Net Cash > 0 and EBITDA > 0
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
                "desc": "Positive cash reserves and operating earnings, though GAAP net losses make P/E non-meaningful.",
                "parallel": "eBay (Q2 1999 baseline)",
                "parallel_notes": "Positive operational capture with early-stage net income fluctuations."
            }

if st.button("Evaluate Stock", type="primary") or ticker_input:
    if ticker_input:
        with st.spinner(f"Fetching financial data for {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info

                company_name = info.get("shortName") or info.get("longName") or ticker_input

                # 1. Trailing P/E extraction with direct calculation fallback
                pe_ratio = info.get("trailingPE")
                if pe_ratio is None:
                    market_cap = info.get("marketCap")
                    net_income = info.get("netIncomeToCommon")
                    if market_cap and net_income and net_income > 0:
                        pe_ratio = market_cap / net_income

                # 2. Extract EBITDA
                ebitda = info.get("ebitda")
                if ebitda is None:
                    income_stmt = stock.income_stmt
                    if not income_stmt.empty and "EBITDA" in income_stmt.index:
                        ebitda = float(income_stmt.loc["EBITDA"].iloc[0])
                    elif not income_stmt.empty and "Operating Income" in income_stmt.index:
                        ebitda = float(income_stmt.loc["Operating Income"].iloc[0])

                # 3. Extract Cash & Debt for Net Cash
                total_cash = info.get("totalCash")
                total_debt = info.get("totalDebt")

                if total_cash is None or total_debt is None:
                    bs = stock.balance_sheet
                    if not bs.empty:
                        cash_keys = ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]
                        for key in cash_keys:
                            if key in bs.index:
                                total_cash = float(bs.loc[key].iloc[0])
                                break
                        if "Total Debt" in bs.index:
                            total_debt = float(bs.loc["Total Debt"].iloc[0])

                total_cash = total_cash or 0
                total_debt = total_debt or 0
                net_cash = total_cash - total_debt

                # Convert to Millions
                net_cash_m = net_cash / 1e6
                ebitda_m = (ebitda / 1e6) if ebitda is not None else 0

                result = evaluate_company(net_cash_m, ebitda_m, pe_ratio)

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
                        label="Net Cash",
                        value=f"${net_cash_m:,.1f}M",
                        delta="Positive Cushion" if net_cash_m >= 0 else "Net Debt",
                        delta_color="normal" if net_cash_m >= 0 else "inverse"
                    )

                with col2:
                    st.metric(
                        label="EBITDA",
                        value=f"${ebitda_m:,.1f}M",
                        delta="Profitable" if ebitda_m >= 0 else "Operating Deficit",
                        delta_color="normal" if ebitda_m >= 0 else "inverse"
                    )

                with col3:
                    pe_display = f"{pe_ratio:.1f}x" if pe_ratio is not None else "N/M (Loss)"
                    st.metric(
                        label="Trailing GAAP P/E",
                        value=pe_display,
                        delta="Grounding <= 60x" if (pe_ratio and pe_ratio <= 60) else "Elevated / Speculative",
                        delta_color="normal" if (pe_ratio and pe_ratio <= 60) else "off"
                    )

            except Exception as e:
                st.error(f"Could not retrieve data for '{ticker_input}'. Error: {e}")
