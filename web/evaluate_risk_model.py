"""
evaluate_risk_model.py  -  measures how good the risk model really is.

Run from the folder that contains merged_student_data_refined.csv:
    python evaluate_risk_model.py

It does NOT change xgboost_risk_model.joblib and prints/saves only numbers
(no student data), so model_evaluation.txt is safe to put on GitHub.
"""
import sys
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix)

CSV = sys.argv[1] if len(sys.argv) > 1 else "merged_student_data_refined.csv"
REPORT = "model_evaluation.txt"
lines = []


def say(text=""):
    print(text)
    lines.append(text)


df = pd.read_csv(CSV)


# ---- same labeling and features as train_model.py -------------------------
def define_risk(row):
    status = str(row["status_id"]).lower()
    grade = str(row["Course_grade"]).upper()
    return 1 if status in ["failed", "absent"] or grade.startswith(("F", "D", "ABS")) else 0


df["is_at_risk"] = df.apply(define_risk, axis=1)
df["term_work_norm"] = df.apply(
    lambda x: x["term_work"] / 80 if x["term_work"] > 40 else x["term_work"] / 40, axis=1)
df["succededhours"] = df["succededhours"].fillna(0)
df["Cumulative_GPA"] = df["Cumulative_GPA"].fillna(0)
df["level_id_x"] = df["level_id_x"].fillna(1)

ALL = ["term_work_norm", "Cumulative_GPA", "succededhours", "level_id_x"]
NO_GPA = ["term_work_norm", "succededhours", "level_id_x"]
TERM_ONLY = ["term_work_norm"]
y = df["is_at_risk"]
groups = df["Student_ID"]


def new_model():
    return xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.1,
                             objective="binary:logistic", eval_metric="logloss")


def score(name, features, train_idx, test_idx):
    m = new_model()
    m.fit(df.loc[train_idx, features], y.loc[train_idx])
    proba = m.predict_proba(df.loc[test_idx, features])[:, 1]
    pred = (proba >= 0.5).astype(int)
    yt = y.loc[test_idx]
    tn, fp, fn, tp = confusion_matrix(yt, pred, labels=[0, 1]).ravel()
    say(f"{name:<46} acc={accuracy_score(yt, pred):.3f} "
        f"prec={precision_score(yt, pred, zero_division=0):.3f} "
        f"recall={recall_score(yt, pred, zero_division=0):.3f} "
        f"f1={f1_score(yt, pred, zero_division=0):.3f} "
        f"auc={roc_auc_score(yt, proba):.3f}  (TP={tp} FP={fp} FN={fn} TN={tn})")


say("=== DATA ===")
say(f"rows: {len(df)}   students: {groups.nunique()}   at-risk share: {y.mean():.1%}")
say(f"baseline accuracy (always predict 'not at risk'): {1 - y.mean():.3f}")
say()

# 1) the split used in train_model.py (random rows)
idx = df.index
tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=42)
say("=== 1) RANDOM ROW SPLIT (what train_model.py does) ===")
score("all 4 features", ALL, tr, te)
shared = len(set(groups.loc[tr]) & set(groups.loc[te]))
say(f"students that appear in BOTH train and test: {shared} "
    f"({shared / groups.loc[te].nunique():.0%} of test students)  <- this inflates the score")
say()

# 2) honest split: whole students are either train or test
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
gtr, gte = next(gss.split(df, y, groups))
gtr, gte = idx[gtr], idx[gte]
say("=== 2) SPLIT BY STUDENT (honest: test students were never seen) ===")
score("all 4 features", ALL, gtr, gte)
score("without Cumulative_GPA", NO_GPA, gtr, gte)
score("term_work_norm only", TERM_ONLY, gtr, gte)
say()
say("How to read it:")
say("- If (1) is much higher than (2), the model partly memorised students.")
say("- If 'without Cumulative_GPA' is close to 'all 4 features', GPA adds little.")
say("- If 'term_work_norm only' is already high, the label mostly follows term work.")
say("- Use the numbers from section 2 in your README.")

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nSaved: {REPORT}")
