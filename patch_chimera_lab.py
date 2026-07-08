import os
import re

target_file = "run_chimera.py"

if not os.path.exists(target_file):
    print(f"❌ {target_file} not found. Make sure you are in the Chimera directory.")
else:
    with open(target_file, "r") as f:
        code = f.read()

    # Find the brittle recommendation API call and replace it with robust handling
    brittle_pattern = r"rec = requests\.post\(f\"\{ORACLE_URL\}/recommend_next\".*?\.json\(\)\.get\('recommendation', ''\)"
    
    robust_replacement = """try:
            rec_res = requests.post(f"{ORACLE_URL}/recommend_next", json={'synthesis': synth, 'user_comment': uc})
            rec = rec_res.json().get('recommendation', '') if rec_res.status_code == 200 else "Continue analysis."
        except Exception as e:
            print(f"⚠️ Oracle Recommendation failed: {e}")
            rec = "Continue analysis."
"""
    
    # Apply the patch
    patched_code = re.sub(brittle_pattern, robust_replacement, code)
    
    with open(target_file, "w") as f:
        f.write(patched_code)
        
    print(f"✅ {target_file} successfully refactored. The core JSON bug is patched.")