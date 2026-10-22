import pandas as pd
import os
import random

output_dir = 'data/processed'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def load_csv_with_encoding(file_path):
    """ Tries multiple encodings to handle Arabic characters and Excel formats. """
    encodings = ['utf-8-sig', 'utf-16', 'utf-8', 'cp1252', 'windows-1256']
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc, low_memory=False)
            print(f"Successfully loaded {file_path} using {enc} encoding.")
            return df
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise Exception(f"Could not decode {file_path}. Ensure it is a valid CSV.")

print("--- Starting Advanced Grade & Status Cleaning ---")

try:
    df_enrollments = load_csv_with_encoding('data/raw/student_course table.csv')
    df_profiles = load_csv_with_encoding('data/raw/students.csv')
    df_course_names = load_csv_with_encoding('data/raw/course table.csv')
except Exception as e:
    print(f"Error: {e}")
    exit()

df_enrollments = df_enrollments.rename(columns={
    'Masked_ID': 'Student_ID', 
    'course_code': 'Course_Code', 
    'grade': 'Course_grade', 
    'result': 'Total_Score'
})
df_profiles = df_profiles.rename(columns={'Masked_ID': 'Student_ID', 'GPA': 'Cumulative_GPA'})
df_course_names = df_course_names.rename(columns={'code': 'Course_Code'})


df_enrollments['Course_grade'] = df_enrollments['Course_grade'].fillna('Abs').astype(str).str.strip()

grades_to_remove = ['I', 'I*', 'V']
initial_row_count = len(df_enrollments)
df_enrollments = df_enrollments[~df_enrollments['Course_grade'].isin(grades_to_remove)]
removed_grades_count = initial_row_count - len(df_enrollments)
print(f"Removed {removed_grades_count} rows containing grades: {grades_to_remove}")

df_enrollments = df_enrollments[~df_enrollments['status_id'].isin([1, 9])].copy()

def determine_final_status(row):
    grade = row['Course_grade']
    if grade == 'Abs':
        return 'Absent'
    if grade == 'F':
        return 'Failed'
    return 'Completed'

df_enrollments['status_id'] = df_enrollments.apply(determine_final_status, axis=1)

merged_step1 = pd.merge(df_enrollments, df_course_names, on='Course_Code', how='left')
final_merged_data = pd.merge(merged_step1, df_profiles, on='Student_ID', how='left')
final_merged_data = final_merged_data.drop_duplicates()

requested_columns = [
    'Student_ID', 'Course_Code', 'term_work', 'exam_work', 
    'Total_Score', 'Cumulative_GPA', 'succededhours', 
    'level_id_x', 'Course_grade', 'status_id'
]
available_cols = [c for c in requested_columns if c in final_merged_data.columns]

try:
    output_full_ref = os.path.join(output_dir, 'merged_student_data_refined.csv')
    final_merged_data[available_cols].to_csv(output_full_ref, index=False, encoding='utf-8-sig')
    
    output_full_all = os.path.join(output_dir, 'merged_student_data_full.csv')
    final_merged_data.to_csv(output_full_all, index=False, encoding='utf-8-sig')

    unique_ids = final_merged_data['Student_ID'].unique()
    if len(unique_ids) >= 100:
        random.seed(42)
        sampled_ids = random.sample(list(unique_ids), 100)
        sample_df = final_merged_data[final_merged_data['Student_ID'].isin(sampled_ids)]
        
        output_samp_ref = os.path.join(output_dir, 'merged_student_cluster_sample_refined.csv')
        sample_df[available_cols].to_csv(output_samp_ref, index=False, encoding='utf-8-sig')
        
        output_samp_all = os.path.join(output_dir, 'merged_student_cluster_sample_full.csv')
        sample_df.to_csv(output_samp_all, index=False, encoding='utf-8-sig')

    print("\n--- Files Generated Successfully ---")
    print(f"Refined File: {output_full_ref}")

except PermissionError:
    print("\nERROR: Please close the Excel files and run the script again.")