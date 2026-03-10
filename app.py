"""
app.py - Heart Disease Analysis Dashboard
Main Flask application entry point.
"""

import json
import time
from flask import Flask, render_template, jsonify, request
import db_setup
import analysis

app = Flask(__name__)
app.secret_key = "hd_analysis_2024_secure_key"

# ── Bootstrap DB on startup ────────────────────────────────────────
with app.app_context():
    try:
        db_setup.init_db()
    except Exception as e:
        print(f"[WARN] DB init: {e}")

# ── Helper: timed chart load ───────────────────────────────────────
def _safe_chart(fn, *args, **kwargs):
    t0 = time.time()
    try:
        data = fn(*args, **kwargs)
        elapsed = round((time.time() - t0) * 1000, 1)
        return data, elapsed, None
    except Exception as ex:
        return None, 0, str(ex)


# ══════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Landing / Overview page."""
    kpis = analysis.get_kpis()
    return render_template("index.html", kpis=kpis)


@app.route("/dashboard")
def dashboard():
    """Main interactive dashboard – Scenario 1 & 2."""
    charts = {}
    timings = {}

    chart_fns = {
        "hd_dist":      analysis.chart_hd_distribution,
        "hd_age":       analysis.chart_hd_by_age,
        "bmi_dist":     analysis.chart_bmi_distribution,
        "risk_factors": analysis.chart_risk_factors,
        "hd_sex":       analysis.chart_hd_by_sex,
        "genhealth":    analysis.chart_genhealth_hd,
        "race_hd":      analysis.chart_race_hd,
        "sleep_hd":     analysis.chart_sleep_hd,
        "phys_mental":  analysis.chart_phys_mental,
        "correlation":  analysis.chart_correlation,
        "age_sex":      analysis.chart_age_sex_bubble,
        "comorbid":     analysis.chart_comorbidities,
        "sunburst":     analysis.chart_sunburst,
    }
    for key, fn in chart_fns.items():
        data, ms, err = _safe_chart(fn)
        charts[key] = data
        timings[key] = ms
        if err:
            print(f"[WARN] chart {key}: {err}")

    kpis = analysis.get_kpis()
    age_categories  = ["All"] + analysis.AGE_ORDER
    return render_template("dashboard.html",
                           charts=charts,
                           timings=timings,
                           kpis=kpis,
                           age_categories=age_categories)


@app.route("/story")
def story():
    """Data story – 3 scenario narratives with embedded charts."""
    c1, _, _ = _safe_chart(analysis.chart_age_sex_bubble)
    c2, _, _ = _safe_chart(analysis.chart_risk_factors)
    c3, _, _ = _safe_chart(analysis.chart_genhealth_hd)
    c4, _, _ = _safe_chart(analysis.chart_bmi_distribution)
    c5, _, _ = _safe_chart(analysis.chart_correlation)
    return render_template("story.html",
                           chart_age_sex=c1,
                           chart_risk=c2,
                           chart_genhealth=c3,
                           chart_bmi=c4,
                           chart_corr=c5)


@app.route("/analysis")
def analysis_page():
    """Deep-dive analysis page with all charts."""
    kpis = analysis.get_kpis()
    c_corr, _, _ = _safe_chart(analysis.chart_correlation)
    c_sun,  _, _ = _safe_chart(analysis.chart_sunburst)
    c_comorb, _, _ = _safe_chart(analysis.chart_comorbidities)
    c_phys, _, _ = _safe_chart(analysis.chart_phys_mental)
    c_sleep, _, _ = _safe_chart(analysis.chart_sleep_hd)
    c_race, _, _ = _safe_chart(analysis.chart_race_hd)
    return render_template("analysis.html",
                           kpis=kpis,
                           chart_corr=c_corr,
                           chart_sun=c_sun,
                           chart_comorb=c_comorb,
                           chart_phys=c_phys,
                           chart_sleep=c_sleep,
                           chart_race=c_race)


@app.route("/performance")
def performance():
    """Performance testing page."""
    t0 = time.time()
    stats = analysis.get_performance_stats()
    elapsed = round((time.time() - t0) * 1000, 1)

    render_times = {}
    chart_fns = {
        "HD Distribution":  analysis.chart_hd_distribution,
        "Age Analysis":     analysis.chart_hd_by_age,
        "BMI Violin":       analysis.chart_bmi_distribution,
        "Risk Factors":     analysis.chart_risk_factors,
        "Gender":           analysis.chart_hd_by_sex,
        "General Health":   analysis.chart_genhealth_hd,
        "Race Treemap":     analysis.chart_race_hd,
        "Sleep Histogram":  analysis.chart_sleep_hd,
        "Phys/Mental":      analysis.chart_phys_mental,
        "Correlation":      analysis.chart_correlation,
        "Age+Sex Bubble":   analysis.chart_age_sex_bubble,
        "Comorbidities":    analysis.chart_comorbidities,
        "Sunburst":         analysis.chart_sunburst,
    }
    for name, fn in chart_fns.items():
        _, ms, _ = _safe_chart(fn)
        render_times[name] = ms

    return render_template("performance.html",
                           stats=stats,
                           render_times=render_times,
                           total_elapsed=elapsed)


# ══════════════════════════════════════════════════════════════════
# API ENDPOINTS (for dynamic filtering via JS fetch)
# ══════════════════════════════════════════════════════════════════

@app.route("/api/filter")
def api_filter():
    sex      = request.args.get("sex",      "All")
    age      = request.args.get("age",      "All")
    diabetic = request.args.get("diabetic", "All")
    smoking  = request.args.get("smoking",  "All")
    t0 = time.time()
    genhealth_chart = analysis.chart_filtered(sex, age, diabetic, smoking)
    bmi_chart       = analysis.chart_filtered_age_bmi(sex, age, diabetic, smoking)
    elapsed = round((time.time() - t0) * 1000, 1)
    return jsonify({
        "genhealth": genhealth_chart,
        "bmi":       bmi_chart,
        "elapsed_ms": elapsed,
    })


@app.route("/api/kpis")
def api_kpis():
    return jsonify(analysis.get_kpis())


@app.route("/api/sql", methods=["POST"])
def api_sql():
    """Execute safe read-only SQL queries (SELECT only)."""
    body = request.get_json(silent=True) or {}
    sql  = body.get("sql", "").strip()
    if not sql.upper().startswith("SELECT"):
        return jsonify({"error": "Only SELECT queries are allowed."}), 400
    try:
        df = db_setup.run_query(sql)
        return jsonify({
            "columns": df.columns.tolist(),
            "rows":    df.head(200).values.tolist(),
            "count":   len(df),
        })
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
