import pandas as pd

def run_final_audit(file_path):
    print("⚖️ CLASS ACTION: OHIO - FINAL DATA AUDIT")
    print("------------------------------------------")
    
    try:
        # Load data with leading zeros for districts
        df = pd.read_csv(file_path, dtype={'zip_code': str, 'rep_district': str})
        
        # 1. Check for total district coverage (1-99)
        all_districts = set([str(i).zfill(2) for i in range(1, 100)])
        found_districts = set(df['rep_district'].unique())
        missing_districts = sorted(list(all_districts - found_districts))
        
        if not missing_districts:
            print("✅ SUCCESS: All 99 House Districts are represented.")
        else:
            print(f"❌ ERROR: Missing {len(missing_districts)} districts: {missing_districts}")
            
        # 2. Check for Zip Code Integrity
        duplicate_zips = df[df.duplicated('zip_code')]['zip_code'].tolist()
        # Filter out 00000 which is expected to have duplicates (Gov, Lt Gov, etc)
        duplicate_zips = [z for z in duplicate_zips if z != "00000"]
        
        if not duplicate_zips:
            print("✅ SUCCESS: No duplicate Zip Codes found (excluding statewide entries).")
        else:
            print(f"⚠️ WARNING: Duplicate Zip Codes found: {set(duplicate_zips)}")
            print("   (Ensure these zips split across districts intentionally.)")
            
        # 3. Check for Null Values in Critical Advocacy Columns
        critical_cols = ['rep_name', 'rep_email', 'school_district', 'avg_teacher_ex', 'poverty_rate']
        null_counts = df[critical_cols].isnull().sum()
        
        if null_counts.sum() == 0:
            print("✅ SUCCESS: All advocacy data hooks are populated.")
        else:
            print("❌ ERROR: Missing data in the following columns:")
            print(null_counts[null_counts > 0])
            
        # 4. Total Enrollment/Fiscal Snapshot
        total_enrollment = pd.to_numeric(df['enrollment'], errors='coerce').sum()
        print(f"📊 DATA SNAPSHOT: Representing approximately {int(total_enrollment):,} Ohio Students.")
        
    except FileNotFoundError:
        print("❌ ERROR: 'ohio_districts.csv' not found in the current directory.")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")

# Run the audit
if __name__ == "__main__":
    run_final_audit("ohio_districts.csv")
