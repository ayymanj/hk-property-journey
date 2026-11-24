"""
ISEM2006 Group 9 - Demo front end for "The Journey of Buying a Property in Hong Kong
for a First Time Buyer".

The calculation functions below are the SAME as in Program_GRP9_SX.ipynb (Parts 1-3).
This file only adds a web interface on top of them for the presentation demo.

Run locally:   streamlit run app.py
"""

import math

import pandas as pd
import streamlit as st
from amortization.amount import calculate_amortization_amount


# =====================================================================
# PART 1 - Total expense required (same as the notebook)
# =====================================================================

def calculate_downpayment_and_loan(transaction_price, valuation_price):
    # The bank lends 90% of the LOWER of transaction price and valuation price.
    downpayment = (0.1 * min(transaction_price, valuation_price)) + max(transaction_price - valuation_price, 0)
    loan_amount = transaction_price - downpayment
    return downpayment, loan_amount


def calculate_basic_costs(transaction_price, loan_amount, rebate_percentage):
    agency_fee = 0.01 * transaction_price

    # Legal fee follows Table 1 of the assignment brief
    if transaction_price < 3000000:
        legal_fee = 5000
    elif transaction_price <= 6000000:
        legal_fee = 6500
    elif transaction_price < 10000000:
        legal_fee = 8000
    else:
        legal_fee = 0.001 * transaction_price
    legal_fee += 3000                      # disbursement fee in all situations

    bank_rebate = loan_amount * (rebate_percentage / 100)

    return {"agency_fee": agency_fee, "legal_fee": legal_fee, "bank_rebate": bank_rebate}


def calculate_stamp_duty(property_value):
    # IRSD123 Scale 2, on the HIGHER of transaction price and valuation price
    if property_value <= 0 or property_value > 15000000:
        return None

    if property_value <= 3000000:
        duty = 100
    elif property_value <= 3528240:
        duty = 100 + (property_value - 3000000) * 0.10
    elif property_value <= 4500000:
        duty = property_value * 0.015
    elif property_value <= 4935480:
        duty = 67500 + (property_value - 4500000) * 0.10
    elif property_value <= 6000000:
        duty = property_value * 0.0225
    elif property_value <= 6642860:
        duty = 135000 + (property_value - 6000000) * 0.10
    elif property_value <= 9000000:
        duty = property_value * 0.03
    elif property_value <= 10080000:
        duty = 270000 + (property_value - 9000000) * 0.10
    else:
        duty = property_value * 0.0375

    # Round up to the nearest dollar (round first to remove floating-point errors)
    duty = round(duty, 6)
    if duty > int(duty):
        duty = int(duty) + 1
    else:
        duty = int(duty)
    return duty


# =====================================================================
# PART 2 - Time required to accumulate the money (same as the notebook)
# =====================================================================

def calculate_saving_months(initial_saving, monthly_salary, saving_percentage,
                            annual_return_rate, target_amount):
    current_saving = initial_saving
    months = 0
    monthly_deposit = monthly_salary * saving_percentage / 100
    monthly_return = annual_return_rate / 100 / 12

    if current_saving >= target_amount:
        return 0

    while current_saving < target_amount and months < 1200:
        new_saving = current_saving * (1 + monthly_return) + monthly_deposit
        if new_saving <= current_saving:
            return None
        current_saving = new_saving
        months += 1

    if current_saving >= target_amount:
        return months
    return None


def saving_balance_by_month(initial_saving, monthly_salary, saving_percentage,
                            annual_return_rate, number_of_months):
    # Same formula as Part 2, but keeps every month's balance for the chart
    balances = [initial_saving]
    current_saving = initial_saving
    monthly_deposit = monthly_salary * saving_percentage / 100
    monthly_return = annual_return_rate / 100 / 12
    for month in range(number_of_months):
        current_saving = current_saving * (1 + monthly_return) + monthly_deposit
        balances.append(current_saving)
    return balances


# =====================================================================
# PART 3 - DTI ratio and stress test (same as the notebook,
# plus the bonus choice of mortgage type and total interest)
# =====================================================================

# Single premium rates (%), "70% up to 90% LTV", first time home buyer (Premium Rate Sheet)
INSURANCE_RATES = {
    "Floating rate": {
        "up_to_6m":  {10: 1.25, 15: 1.48, 20: 1.79, 25: 2.03, 30: 2.16},   # Table 1
        "up_to_15m": {10: 1.46, 15: 1.72, 20: 2.08, 25: 2.35, 30: 2.50},   # Table 3
    },
    "Fixed Adjustable Rate (FARM)": {
        "up_to_6m":  {10: 1.16, 15: 1.37, 20: 1.70, 25: 1.92, 30: 2.05},   # Table 1
        "up_to_15m": {10: 1.35, 15: 1.60, 20: 1.98, 25: 2.23, 30: 2.38},   # Table 3
    },
}


def get_insurance_rate(property_value, tenor_years, mortgage_type="Floating rate"):
    if property_value <= 6000000:
        return INSURANCE_RATES[mortgage_type]["up_to_6m"][tenor_years]
    return INSURANCE_RATES[mortgage_type]["up_to_15m"][tenor_years]


def calculate_mortgage_loan(transaction_price, valuation_price, tenor_years, mortgage_type="Floating rate"):
    property_value = min(transaction_price, valuation_price)
    base_loan = 0.9 * property_value
    insurance_rate = get_insurance_rate(property_value, tenor_years, mortgage_type)
    insurance_premium = math.ceil(round(base_loan * insurance_rate / 100, 2))
    total_loan = base_loan + insurance_premium
    return base_loan, insurance_premium, total_loan


def assess_tenor(transaction_price, valuation_price, monthly_salary, mortgage_interest_rate,
                 tenor_years, mortgage_type="Floating rate"):
    DTI_LIMIT = 0.50
    STRESS_LIMIT = 0.60
    STRESS_EXTRA_RATE = 2

    base_loan, insurance_premium, total_loan = calculate_mortgage_loan(
        transaction_price, valuation_price, tenor_years, mortgage_type)
    months = tenor_years * 12

    normal_payment = calculate_amortization_amount(total_loan, mortgage_interest_rate / 100, months)
    stress_payment = calculate_amortization_amount(
        total_loan, (mortgage_interest_rate + STRESS_EXTRA_RATE) / 100, months)

    dti_ratio = normal_payment / monthly_salary
    stress_ratio = stress_payment / monthly_salary
    minimum_salary = math.ceil(round(max(normal_payment / DTI_LIMIT, stress_payment / STRESS_LIMIT), 2))

    return {
        "tenor_years": tenor_years,
        "insurance_premium": insurance_premium,
        "total_loan": total_loan,
        "monthly_payment": normal_payment,
        "dti_ratio": dti_ratio,
        "passes_dti": dti_ratio <= DTI_LIMIT,
        "stress_payment": stress_payment,
        "stress_ratio": stress_ratio,
        "passes_stress": stress_ratio <= STRESS_LIMIT,
        "minimum_salary": minimum_salary,
        # Bonus: total interest paid over the whole loan
        "total_interest": normal_payment * months - total_loan,
    }


def assess_affordability(transaction_price, valuation_price, monthly_salary,
                         mortgage_interest_rate, mortgage_type="Floating rate"):
    results = []
    for tenor_years in range(10, 31, 5):
        results.append(assess_tenor(transaction_price, valuation_price, monthly_salary,
                                    mortgage_interest_rate, tenor_years, mortgage_type))
    return results


# =====================================================================
# Helpers for the page
# =====================================================================

def money(amount):
    if amount < 0:
        return f"-${-amount:,.0f}"
    return f"${amount:,.0f}"


def describe_months(months):
    years = months // 12
    remaining_months = months % 12
    parts = []
    if years > 0:
        parts.append(f"{years} year" + ("s" if years != 1 else ""))
    if remaining_months > 0 or years == 0:
        parts.append(f"{remaining_months} month" + ("s" if remaining_months != 1 else ""))
    return " ".join(parts)


# =====================================================================
# Web page
# =====================================================================

def main():
    st.set_page_config(page_title="HK First Home Journey", page_icon="🏠", layout="wide")

    st.title("🏠 The Journey of Buying a Property in Hong Kong")
    st.caption("ISEM2006 Group 9 · First time buyer · 90% LTV with mortgage insurance · "
               "Calculations use the same Python functions as our notebook")

    # ---------------- Inputs (sidebar) ----------------
    with st.sidebar:
        st.header("Buyer inputs")
        transaction_price = st.number_input("Transaction price ($)", min_value=1, max_value=15000000,
                                            value=5000000, step=100000)
        valuation_price = st.number_input("Valuation price ($)", min_value=1, max_value=15000000,
                                          value=5000000, step=100000)
        initial_saving = st.number_input("Initial saving ($)", min_value=0, value=200000, step=10000)
        monthly_salary = st.slider("Monthly salary ($)", min_value=10000, max_value=300000,
                                   value=40000, step=1000)
        rebate_percentage = st.slider("Bank rebate (%)", 0.5, 2.5, 1.0, 0.1)
        saving_percentage = st.slider("Monthly saving (% of salary)", 1, 100, 30)
        annual_return_rate = st.slider("Annual return on savings (%)", 0.0, 10.0, 4.0, 0.5)
        mortgage_interest_rate = st.slider("Mortgage interest rate (%)", 0.5, 10.0, 3.5, 0.125)

        st.header("Bonus option")
        mortgage_type = st.radio("Mortgage type (insurance rates)",
                                 ["Floating rate", "Fixed Adjustable Rate (FARM)"])

    # ---------------- Part 1 ----------------
    downpayment, loan_amount = calculate_downpayment_and_loan(transaction_price, valuation_price)
    costs = calculate_basic_costs(transaction_price, loan_amount, rebate_percentage)
    stamp_duty = calculate_stamp_duty(max(transaction_price, valuation_price))
    total_expense = (downpayment + costs["agency_fee"] + costs["legal_fee"]
                     + stamp_duty - costs["bank_rebate"])

    st.header("Step 1 · Total cash needed upfront")
    if valuation_price < transaction_price:
        st.warning(f"The bank values the flat {money(transaction_price - valuation_price)} below the price, "
                   "so the buyer pays that gap in the downpayment.")

    metric_columns = st.columns(3)
    metric_columns[0].metric("Total expense required", money(total_expense))
    metric_columns[1].metric("Loan from bank (90% LTV)", money(loan_amount))
    metric_columns[2].metric("Stamp duty", money(stamp_duty))

    breakdown_table = pd.DataFrame({
        "Item": ["Downpayment", "Agency fee", "Legal fee", "Stamp duty", "Bank rebate"],
        "Amount ($)": [downpayment, costs["agency_fee"], costs["legal_fee"], stamp_duty, -costs["bank_rebate"]],
    })
    chart_column, table_column = st.columns([3, 2])
    chart_column.bar_chart(breakdown_table, x="Item", y="Amount ($)", sort=False)
    table_column.dataframe(
        breakdown_table.assign(**{"Amount ($)": breakdown_table["Amount ($)"].map(money)}),
        hide_index=True)

    # ---------------- Part 2 ----------------
    st.header("Step 2 · Time to save the money")
    months_needed = calculate_saving_months(initial_saving, monthly_salary, saving_percentage,
                                            annual_return_rate, total_expense)
    monthly_deposit = monthly_salary * saving_percentage / 100

    if months_needed is None:
        st.error("With this saving plan the target cannot be reached within 100 years.")
    elif months_needed == 0:
        st.success("The initial saving already covers the total expense — ready to buy now!")
    else:
        st.success(f"Ready to buy in **{describe_months(months_needed)}** "
                   f"({months_needed} months), saving {money(monthly_deposit)} per month.")
        balances = saving_balance_by_month(initial_saving, monthly_salary, saving_percentage,
                                           annual_return_rate, months_needed)
        savings_chart = pd.DataFrame({
            "Month": list(range(len(balances))),
            "Savings ($)": balances,
            "Target ($)": [total_expense] * len(balances),
        })
        st.line_chart(savings_chart, x="Month", y=["Savings ($)", "Target ($)"])

    # ---------------- Part 3 ----------------
    st.header("Step 3 · Can the salary support the mortgage?")
    st.caption(f"DTI test: payment ≤ 50% of salary at {mortgage_interest_rate}% · "
               f"Stress test: payment ≤ 60% of salary at {mortgage_interest_rate + 2}% · "
               f"Insurance: {mortgage_type}, single premium added to the loan")

    results = assess_affordability(transaction_price, valuation_price, monthly_salary,
                                   mortgage_interest_rate, mortgage_type)

    table_rows = []
    passing_tenors = []
    for result in results:
        passes_both = result["passes_dti"] and result["passes_stress"]
        if passes_both:
            passing_tenors.append(result["tenor_years"])
        table_rows.append({
            "Tenor": f"{result['tenor_years']} years",
            "Insurance": money(result["insurance_premium"]),
            "Total loan": money(result["total_loan"]),
            "Monthly payment": money(result["monthly_payment"]),
            "DTI": f"{result['dti_ratio']:.1%} " + ("✅" if result["passes_dti"] else "❌"),
            "Stress payment": money(result["stress_payment"]),
            "Stress ratio": f"{result['stress_ratio']:.1%} " + ("✅" if result["passes_stress"] else "❌"),
            "Result": "✅ PASS" if passes_both else "❌ FAIL",
            "Min salary to pass": money(result["minimum_salary"]),
            "Total interest (bonus)": money(result["total_interest"]),
        })
    st.dataframe(pd.DataFrame(table_rows), hide_index=True)

    if passing_tenors:
        st.success(f"The buyer passes both tests for: {', '.join(str(t) for t in passing_tenors)} years.")
    else:
        lowest_minimum = min(result["minimum_salary"] for result in results)
        st.error(f"The buyer does not pass for any tenor. "
                 f"A salary of at least {money(lowest_minimum)} is needed (30-year loan).")

    # ---------------- Bonus: insight and timeline ----------------
    st.header("Bonus · Trade-off and timeline")
    shortest = results[0]
    longest = results[-1]
    insight_columns = st.columns(2)
    insight_columns[0].metric(
        "30 vs 10 years: monthly payment",
        money(longest["monthly_payment"]),
        delta=f"-{money(shortest['monthly_payment'] - longest['monthly_payment'])} per month",
        delta_color="inverse")
    insight_columns[1].metric(
        "30 vs 10 years: total interest",
        money(longest["total_interest"]),
        delta=f"+{money(longest['total_interest'] - shortest['total_interest'])} more interest",
        delta_color="inverse")

    if months_needed is not None and passing_tenors:
        chosen_tenor = passing_tenors[0]
        total_months = months_needed + chosen_tenor * 12
        st.info(f"🗓️ Save for {describe_months(months_needed) if months_needed else '0 months'}, "
                f"then take the shortest passing loan ({chosen_tenor} years): "
                f"the flat is fully paid off in **{describe_months(total_months)}** from today.")


if __name__ == "__main__":
    main()
