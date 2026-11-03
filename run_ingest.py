import sys
sys.path.insert(0, 'src')
from airaware.ingest_advance_search import run_pipeline
df_primary, all_dfs = run_pipeline()

