
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCORECARD = pd.read_csv(BASE / 'data' / 'processed' / 'fund_scorecard.csv')

def get_recommendations(risk_level, top_n=3):
    df = SCORECARD[SCORECARD['risk_grade'] == risk_level].copy()
    return df.sort_values('sharpe_ratio', ascending=False).head(top_n)
