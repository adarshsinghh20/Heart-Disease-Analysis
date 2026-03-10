"""
analysis.py - Heart Disease Analysis
All data analysis and Plotly chart generation functions.
Returns JSON-serializable chart specs for Flask→JS embedding.
"""

import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.utils

from db_setup import run_query, get_full_df

# ─── Colour palette ────────────────────────────────────────────────
COLORS = {
    "primary":   "#E74C3C",
    "secondary": "#2C3E50",
    "safe":      "#27AE60",
    "warning":   "#F39C12",
    "info":      "#2980B9",
    "light":     "#ECF0F1",
    "palette":   px.colors.qualitative.Set2,
    "seq_red":   px.colors.sequential.Reds,
    "seq_blue":  px.colors.sequential.Blues,
}

AGE_ORDER = ["18-24","25-29","30-34","35-39","40-44","45-49",
             "50-54","55-59","60-64","65-69","70-74","75-79","80 or older"]
HEALTH_ORDER = ["Poor","Fair","Good","Very good","Excellent"]

def _to_json(fig):
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def _layout(fig, title, height=420):
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS["secondary"]), x=0.04),
        paper_bgcolor="white",
        plot_bgcolor="#F8F9FA",
        font=dict(family="Segoe UI, sans-serif", size=12),
        margin=dict(l=50, r=30, t=60, b=50),
        height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)")
    )
    return fig

# ────────────────────────────────────────────────────────────────────
# KPI CARDS
# ────────────────────────────────────────────────────────────────────
def get_kpis():
    df = run_query("SELECT * FROM v_risk_counts")
    row = df.iloc[0]
    total      = int(row["total"])
    hd_yes     = int(row["hd_yes"])
    hd_pct     = round(hd_yes / total * 100, 1)
    smokers_pct= round(int(row["smokers"])  / total * 100, 1)
    diabetic_pct= round(int(row["diabetic"]) / total * 100, 1)
    active_pct  = round(int(row["active"])   / total * 100, 1)
    return dict(total=total, hd_yes=hd_yes, hd_pct=hd_pct,
                smokers_pct=smokers_pct, diabetic_pct=diabetic_pct,
                active_pct=active_pct)

# ────────────────────────────────────────────────────────────────────
# 1. HEART DISEASE DISTRIBUTION (Donut)
# ────────────────────────────────────────────────────────────────────
def chart_hd_distribution():
    df = run_query("SELECT HeartDisease, COUNT(*) as cnt FROM heart_records GROUP BY HeartDisease")
    fig = go.Figure(go.Pie(
        labels=df["HeartDisease"], values=df["cnt"],
        hole=0.55,
        marker=dict(colors=[COLORS["primary"], COLORS["safe"]],
                    line=dict(color="white", width=2)),
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>"
    ))
    fig.add_annotation(text="Heart<br>Disease", x=0.5, y=0.5,
                       font=dict(size=14, color=COLORS["secondary"]), showarrow=False)
    _layout(fig, "Heart Disease Prevalence")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 2. AGE VS HEART DISEASE (Grouped bar)
# ────────────────────────────────────────────────────────────────────
def chart_hd_by_age():
    df = run_query("""
        SELECT AgeCategory,
               SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END) AS hd_yes,
               COUNT(*) AS total
        FROM heart_records
        GROUP BY AgeCategory
    """)
    df["hd_pct"] = (df["hd_yes"] / df["total"] * 100).round(1)
    # preserve age order
    df["AgeCategory"] = pd.Categorical(df["AgeCategory"], categories=AGE_ORDER, ordered=True)
    df = df.sort_values("AgeCategory")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=df["AgeCategory"], y=df["total"],
        name="Total Patients",
        marker_color=COLORS["info"],
        opacity=0.7,
        hovertemplate="%{x}<br>Total: %{y}<extra></extra>"
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df["AgeCategory"], y=df["hd_pct"],
        name="HD Rate (%)",
        mode="lines+markers",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=7),
        hovertemplate="%{x}<br>HD Rate: %{y:.1f}%<extra></extra>"
    ), secondary_y=True)
    fig.update_yaxes(title_text="Number of Patients", secondary_y=False)
    fig.update_yaxes(title_text="Heart Disease Rate (%)", secondary_y=True)
    _layout(fig, "Heart Disease Rate by Age Category")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 3. BMI DISTRIBUTION (Violin/Box)
# ────────────────────────────────────────────────────────────────────
def chart_bmi_distribution():
    df = run_query("SELECT BMI, HeartDisease FROM heart_records")
    fig = go.Figure()
    for label, color in [("Yes", COLORS["primary"]), ("No", COLORS["safe"])]:
        sub = df[df["HeartDisease"] == label]["BMI"]
        fig.add_trace(go.Violin(
            y=sub, name=f"HD: {label}",
            box_visible=True, meanline_visible=True,
            fillcolor=color, opacity=0.7,
            line_color=color,
            hoverinfo="y"
        ))
    _layout(fig, "BMI Distribution – Heart Disease vs No Heart Disease")
    fig.update_layout(violinmode="group")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 4. RISK FACTORS COMPARISON (Horizontal bar chart)
# ────────────────────────────────────────────────────────────────────
def chart_risk_factors():
    factors = ["Smoking", "AlcoholDrinking", "Stroke", "Diabetic",
               "PhysicalActivity", "DiffWalking", "Asthma", "KidneyDisease", "SkinCancer"]
    rows = []
    for f in factors:
        q = f"""
            SELECT
              ROUND(100.0*SUM(CASE WHEN HeartDisease='Yes' AND {f}='Yes' THEN 1 ELSE 0 END)/
                    NULLIF(SUM(CASE WHEN {f}='Yes' THEN 1 ELSE 0 END),0),1) AS pct_yes,
              ROUND(100.0*SUM(CASE WHEN HeartDisease='Yes' AND {f}='No' THEN 1 ELSE 0 END)/
                    NULLIF(SUM(CASE WHEN {f}='No' THEN 1 ELSE 0 END),0),1) AS pct_no
            FROM heart_records
        """
        r = run_query(q).iloc[0]
        rows.append({"Factor": f, "With Factor": r["pct_yes"], "Without Factor": r["pct_no"]})
    df = pd.DataFrame(rows)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["Factor"], x=df["With Factor"], name="With Factor",
        orientation="h", marker_color=COLORS["primary"],
        hovertemplate="<b>%{y}</b><br>HD Rate with factor: %{x:.1f}%<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        y=df["Factor"], x=df["Without Factor"], name="Without Factor",
        orientation="h", marker_color=COLORS["info"],
        hovertemplate="<b>%{y}</b><br>HD Rate without factor: %{x:.1f}%<extra></extra>"
    ))
    fig.update_layout(barmode="group")
    _layout(fig, "Heart Disease Rate by Risk Factor Presence (%)", height=460)
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 5. GENDER DISTRIBUTION (Stacked bar)
# ────────────────────────────────────────────────────────────────────
def chart_hd_by_sex():
    df = run_query("""
        SELECT Sex, HeartDisease, COUNT(*) AS cnt FROM heart_records
        GROUP BY Sex, HeartDisease
    """)
    fig = px.bar(df, x="Sex", y="cnt", color="HeartDisease",
                 color_discrete_map={"Yes": COLORS["primary"], "No": COLORS["safe"]},
                 barmode="stack",
                 labels={"cnt": "Count", "HeartDisease": "Heart Disease"},
                 text_auto=True)
    _layout(fig, "Heart Disease Distribution by Gender")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 6. GENERAL HEALTH vs HD (Heatmap-style)
# ────────────────────────────────────────────────────────────────────
def chart_genhealth_hd():
    df = run_query("""
        SELECT GenHealth,
               ROUND(100.0*SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END)/COUNT(*),1) AS hd_rate,
               COUNT(*) as cnt
        FROM heart_records GROUP BY GenHealth
    """)
    df["GenHealth"] = pd.Categorical(df["GenHealth"], categories=HEALTH_ORDER, ordered=True)
    df = df.sort_values("GenHealth")

    fig = go.Figure(go.Bar(
        x=df["GenHealth"], y=df["hd_rate"],
        marker=dict(
            color=df["hd_rate"],
            colorscale="Reds",
            showscale=True,
            colorbar=dict(title="HD Rate%")
        ),
        text=df["hd_rate"].apply(lambda v: f"{v}%"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>HD Rate: %{y:.1f}%<br>Count: %{customdata}<extra></extra>",
        customdata=df["cnt"]
    ))
    _layout(fig, "Heart Disease Rate by Self-Reported General Health")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 7. RACE DISTRIBUTION (Treemap)
# ────────────────────────────────────────────────────────────────────
def chart_race_hd():
    df = run_query("""
        SELECT Race,
               SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END) AS hd_count,
               COUNT(*) AS total
        FROM heart_records GROUP BY Race
    """)
    df["hd_rate"] = (df["hd_count"] / df["total"] * 100).round(1)
    fig = px.treemap(df, path=["Race"], values="total",
                     color="hd_rate",
                     color_continuous_scale="Reds",
                     hover_data={"hd_rate": True, "hd_count": True},
                     labels={"hd_rate": "HD Rate (%)", "total": "Patients"})
    _layout(fig, "Heart Disease Rate by Race (Treemap – size = patient count)")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 8. SLEEP TIME HISTOGRAM
# ────────────────────────────────────────────────────────────────────
def chart_sleep_hd():
    df = run_query("SELECT SleepTime, HeartDisease FROM heart_records")
    fig = px.histogram(df, x="SleepTime", color="HeartDisease", nbins=20,
                       barmode="overlay", opacity=0.7,
                       color_discrete_map={"Yes": COLORS["primary"], "No": COLORS["safe"]},
                       labels={"SleepTime": "Sleep Hours (per night)", "count": "Frequency"})
    fig.update_traces(hovertemplate="Sleep: %{x}h<br>Count: %{y}<extra></extra>")
    _layout(fig, "Sleep Time Distribution by Heart Disease Status")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 9. PHYSICAL vs MENTAL HEALTH SCATTER
# ────────────────────────────────────────────────────────────────────
def chart_phys_mental():
    df = run_query("""
        SELECT PhysicalHealth, MentalHealth, HeartDisease, BMI, Sex
        FROM heart_records
        WHERE PhysicalHealth <= 30 AND MentalHealth <= 30
    """)
    fig = px.scatter(df, x="PhysicalHealth", y="MentalHealth",
                     color="HeartDisease", size="BMI", opacity=0.6,
                     color_discrete_map={"Yes": COLORS["primary"], "No": COLORS["safe"]},
                     symbol="Sex",
                     labels={"PhysicalHealth": "Unhealthy Physical Days (30-day)",
                             "MentalHealth": "Unhealthy Mental Days (30-day)"},
                     hover_data=["BMI", "Sex"])
    _layout(fig, "Physical Health vs Mental Health (sized by BMI)", height=460)
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 10. CORRELATION HEATMAP
# ────────────────────────────────────────────────────────────────────
def chart_correlation():
    df = get_full_df()
    bin_cols = ["HeartDisease","Smoking","AlcoholDrinking","Stroke","DiffWalking",
                "Sex","Diabetic","PhysicalActivity","Asthma","KidneyDisease","SkinCancer"]
    for c in bin_cols:
        if c in df.columns:
            df[c] = (df[c].str.lower().isin(["yes","male"])).astype(int)

    num_df = df[["HeartDisease","BMI","PhysicalHealth","MentalHealth","SleepTime",
                  "Smoking","AlcoholDrinking","Stroke","Diabetic","PhysicalActivity",
                  "DiffWalking","Asthma","KidneyDisease"]].dropna()
    corr = num_df.corr().round(2)
    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale="RdBu_r",
        zmid=0,
        text=corr.values,
        texttemplate="%{text}",
        hovertemplate="<b>%{y} × %{x}</b><br>r = %{z:.2f}<extra></extra>"
    ))
    _layout(fig, "Correlation Heatmap – All Features vs Heart Disease", height=520)
    fig.update_layout(xaxis_tickangle=-35)
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 11. AGE + GENDER BUBBLE (Scenario 1 Dashboard)
# ────────────────────────────────────────────────────────────────────
def chart_age_sex_bubble():
    df = run_query("""
        SELECT AgeCategory, Sex,
               ROUND(100.0*SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END)/COUNT(*),1) AS hd_rate,
               ROUND(AVG(BMI),2) AS avg_bmi,
               COUNT(*) AS cnt
        FROM heart_records GROUP BY AgeCategory, Sex
    """)
    df["AgeCategory"] = pd.Categorical(df["AgeCategory"], categories=AGE_ORDER, ordered=True)
    df = df.sort_values("AgeCategory")
    fig = px.scatter(df, x="AgeCategory", y="hd_rate",
                     size="cnt", color="Sex",
                     symbol="Sex",
                     color_discrete_map={"Male": COLORS["info"], "Female": COLORS["warning"]},
                     hover_data={"avg_bmi": True, "cnt": True, "hd_rate": True},
                     labels={"hd_rate": "HD Rate (%)", "avg_bmi": "Avg BMI", "cnt": "Patients"},
                     size_max=40)
    _layout(fig, "Heart Disease Rate by Age Group & Gender (bubble size = patient count)")
    fig.update_layout(xaxis_tickangle=-35)
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 12. DIABETIC + SMOKING COMBINED (stacked)
# ────────────────────────────────────────────────────────────────────
def chart_comorbidities():
    df = run_query("""
        SELECT
            CASE WHEN Diabetic='Yes' AND Smoking='Yes' THEN 'Diabetic+Smoker'
                 WHEN Diabetic='Yes' AND Smoking='No'  THEN 'Diabetic Only'
                 WHEN Diabetic='No'  AND Smoking='Yes' THEN 'Smoker Only'
                 ELSE 'Neither'
            END AS Group_,
            HeartDisease, COUNT(*) AS cnt
        FROM heart_records GROUP BY Group_, HeartDisease
    """)
    fig = px.bar(df, x="Group_", y="cnt", color="HeartDisease",
                 color_discrete_map={"Yes": COLORS["primary"], "No": COLORS["safe"]},
                 barmode="stack", text_auto=True,
                 labels={"Group_": "Patient Group", "cnt": "Count"})
    _layout(fig, "Comorbidities: Diabetic & Smoking vs Heart Disease")
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# 13. SUNBURST – Hierarchical View
# ────────────────────────────────────────────────────────────────────
def chart_sunburst():
    df = run_query("""
        SELECT Sex, AgeCategory, HeartDisease, COUNT(*) AS cnt
        FROM heart_records GROUP BY Sex, AgeCategory, HeartDisease
    """)
    fig = px.sunburst(df, path=["HeartDisease","Sex","AgeCategory"], values="cnt",
                      color="HeartDisease",
                      color_discrete_map={"Yes": COLORS["primary"], "No": COLORS["safe"]})
    _layout(fig, "Hierarchical View: HD → Gender → Age", height=500)
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# FILTERED CHARTS (for dynamic filtering)
# ────────────────────────────────────────────────────────────────────
def chart_filtered(sex=None, age=None, diabetic=None, smoking=None):
    where_clauses = []
    if sex       and sex      != "All": where_clauses.append(f"Sex='{sex}'")
    if age       and age      != "All": where_clauses.append(f"AgeCategory='{age}'")
    if diabetic  and diabetic != "All": where_clauses.append(f"Diabetic='{diabetic}'")
    if smoking   and smoking  != "All": where_clauses.append(f"Smoking='{smoking}'")
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    df = run_query(f"""
        SELECT GenHealth, HeartDisease, COUNT(*) AS cnt
        FROM heart_records {where}
        GROUP BY GenHealth, HeartDisease
    """)
    if df.empty:
        return _to_json(go.Figure())

    fig = px.bar(df, x="GenHealth", y="cnt", color="HeartDisease",
                 barmode="group",
                 color_discrete_map={"Yes": COLORS["primary"], "No": COLORS["safe"]},
                 category_orders={"GenHealth": HEALTH_ORDER},
                 text_auto=True,
                 labels={"cnt": "Count", "GenHealth": "General Health"})
    title = "Filtered: General Health vs Heart Disease"
    if where_clauses: title += f"  [{', '.join(where_clauses)}]"
    _layout(fig, title)
    return _to_json(fig)

def chart_filtered_age_bmi(sex=None, age=None, diabetic=None, smoking=None):
    where_clauses = []
    if sex       and sex      != "All": where_clauses.append(f"Sex='{sex}'")
    if age       and age      != "All": where_clauses.append(f"AgeCategory='{age}'")
    if diabetic  and diabetic != "All": where_clauses.append(f"Diabetic='{diabetic}'")
    if smoking   and smoking  != "All": where_clauses.append(f"Smoking='{smoking}'")
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    df = run_query(f"""
        SELECT AgeCategory, HeartDisease,
               ROUND(AVG(BMI),2) AS avg_bmi, COUNT(*) AS cnt
        FROM heart_records {where}
        GROUP BY AgeCategory, HeartDisease
    """)
    if df.empty:
        return _to_json(go.Figure())
    df["AgeCategory"] = pd.Categorical(df["AgeCategory"], categories=AGE_ORDER, ordered=True)
    df = df.sort_values("AgeCategory")
    fig = px.line(df, x="AgeCategory", y="avg_bmi", color="HeartDisease",
                  markers=True,
                  color_discrete_map={"Yes": COLORS["primary"], "No": COLORS["safe"]},
                  labels={"avg_bmi": "Average BMI", "AgeCategory": "Age Category"})
    _layout(fig, "Filtered: Average BMI by Age & Heart Disease")
    fig.update_layout(xaxis_tickangle=-35)
    return _to_json(fig)

# ────────────────────────────────────────────────────────────────────
# PERFORMANCE STATS
# ────────────────────────────────────────────────────────────────────
def get_performance_stats():
    total = run_query("SELECT COUNT(*) AS cnt FROM heart_records").iloc[0]["cnt"]
    hd_rate = run_query("""
        SELECT ROUND(100.0*SUM(CASE WHEN HeartDisease='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) AS r
        FROM heart_records
    """).iloc[0]["r"]
    age_groups = run_query("SELECT COUNT(DISTINCT AgeCategory) AS c FROM heart_records").iloc[0]["c"]
    races      = run_query("SELECT COUNT(DISTINCT Race) AS c FROM heart_records").iloc[0]["c"]

    bmi_stats = run_query("""
        SELECT HeartDisease,
               ROUND(MIN(BMI),1) AS min_bmi,
               ROUND(MAX(BMI),1) AS max_bmi,
               ROUND(AVG(BMI),2) AS avg_bmi,
               ROUND(AVG(SleepTime),2) AS avg_sleep
        FROM heart_records GROUP BY HeartDisease
    """)

    return dict(
        total_records=int(total),
        hd_rate=float(hd_rate),
        age_groups=int(age_groups),
        races=int(races),
        num_columns=18,
        num_visualizations=13,
        num_calc_fields=6,
        num_filters=4,
        bmi_stats=bmi_stats.to_dict(orient="records"),
    )
