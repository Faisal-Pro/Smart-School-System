import pandas as pd
import xgboost as xgb
import joblib
from sklearn.model_selection import train_test_split

def train_advanced_risk_model():
    df = pd.read_csv('merged_student_data_refined.csv')

    # Honest Labeling
    def define_risk(row):
        status = str(row['status_id']).lower()
        grade = str(row['Course_grade']).upper()
        return 1 if status in ['failed', 'absent'] or grade.startswith(('F', 'D', 'ABS')) else 0

    df['is_at_risk'] = df.apply(define_risk, axis=1)
    
    # Feature Engineering (Standardized)
    df['term_work_norm'] = df.apply(lambda x: x['term_work']/80 if x['term_work'] > 40 else x['term_work']/40, axis=1)
    df['succededhours'] = df['succededhours'].fillna(0)
    df['Cumulative_GPA'] = df['Cumulative_GPA'].fillna(0)
    df['level_id_x'] = df['level_id_x'].fillna(1)
    
    X = df[['term_work_norm', 'Cumulative_GPA', 'succededhours', 'level_id_x']]
    y = df['is_at_risk']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    # Balanced Model: Using scale_pos_weight to manage sensitivity
    model = xgb.XGBClassifier(
        n_estimators=300, 
        max_depth=4, 
        learning_rate=0.1,
        scale_pos_weight=1, # No aggressive weighting
        objective='binary:logistic',
        eval_metric='logloss'
    )

    model.fit(X_train, y_train)
    joblib.dump(model, 'xgboost_risk_model.joblib')
    print("--- [SUCCESS] Clean Model Re-Trained ---")

if __name__ == "__main__":
    train_advanced_risk_model()