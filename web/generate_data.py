"""
ADVANCED SYNTHETIC DATA ENGINE v2.1 [STRICT CALIBRATION]
Designed for: Graduation Project Research - 2026
Objective: Generate high-precision risk indicators with tightened 'Mid-Range' sensitivity.
"""
import pandas as pd
import numpy as np
import scipy.stats as stats

def generate_student_data(n=8000): # Increased N for higher model granularity
    np.random.seed(42)
    print("--- [SYS] Initializing Stricter Synthetic Data Generation Pipeline ---")
    
    data = []
    for i in range(n):
        # 1. LATENT TRAIT GENERATION (Hidden Student Potential)
        # Higher alpha/beta values create a more concentrated distribution
        conscientiousness = np.random.beta(4, 2.5) 
        
        # 2. FEATURE SYNTHESIS
        attendance = np.clip(np.random.normal(conscientiousness, 0.12), 0.3, 1.0)
        quiz = np.clip(np.random.normal(conscientiousness, 0.18), 0.0, 1.0)
        hw = np.clip(np.random.normal(conscientiousness * 0.85, 0.1), 0.0, 1.0)
        
        # --- ENHANCED RISK HEURISTICS (STRICTER) ---
        
        # A: Engagement Factor (Strict Penalty: Risk starts rising if below 85%)
        att_risk = 1.0 - attendance if attendance < 0.85 else (1.0 - attendance) * 0.4
        
        # B: Performance Factor (Weighted towards Homework Consistency)
        # We amplify the risk if grades are in the 'C' range (below 0.7)
        base_grade_risk = (1.0 - quiz) * 0.40 + (1.0 - hw) * 0.60
        if (quiz < 0.72 or hw < 0.72):
            perf_risk = base_grade_risk * 1.45 # "Struggle Multiplier"
        else:
            perf_risk = base_grade_risk
        
        # C: Behavioral Anomaly (High Quiz / Low HW suggests lack of effort)
        discrepancy = max(0, (quiz - hw) * 1.8)
        
        # AGGREGATE NEURAL SCORE
        # We increase the weight of the Performance risk for 2026 standards
        raw_score = (att_risk * 0.35) + (perf_risk * 0.55) + (discrepancy * 0.10)
        
        # D: RANDOMIZED ENVIRONMENTAL NOISE
        env_noise = np.random.normal(0, 0.05)
        final_probability = np.clip(raw_score + env_noise, 0, 1)

        # 3. UPDATED NON-LINEAR CLASSIFICATION THRESHOLDS (Lowered for Mid-Sensitivity)
        # By lowering these, 'Mid' students are more likely to be labeled '1' (At Risk)
        if final_probability > 0.50: 
            is_at_risk = 1
        elif final_probability > 0.28: 
            # Fuzzy Logic Zone: 65% chance of being labeled at risk in the mid-range
            is_at_risk = 1 if np.random.random() < 0.65 else 0
        else:
            is_at_risk = 0
            
        data.append([attendance, quiz, hw, is_at_risk])
    
    # 4. EXPORT & DIAGNOSTICS
    columns = ['attendance', 'quiz', 'hw', 'is_at_risk']
    df = pd.DataFrame(data, columns=columns)
    
    # Feature Engineering for complexity
    df['study_hours_est'] = np.clip(df['hw'] * 12 + np.random.normal(0, 1.5), 0, 24)
    
    df.to_csv('student_data.csv', index=False)
    print(f"--- [SUCCESS] Dataset Serialized: {n} observations ---")
    print(f"--- [INFO] New Class Distribution: {df['is_at_risk'].value_counts(normalize=True).to_dict()} ---")

if __name__ == "__main__":
    generate_student_data()