from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sentence_transformers import SentenceTransformer
import pandas as pd
from pathlib import Path


# Path to this script (ml_ai/longitudinal/baseline.py)
SCRIPT_DIR = Path(__file__).resolve().parent

CSV_PATH = SCRIPT_DIR.parents[1] / "datasets" / "research_data" / "mental_health_unbanlanced.csv"

# Read the CSV file and split into training and testing sets

data = pd.read_csv(CSV_PATH)

X_train, X_test, y_train, y_test = train_test_split(data['text'], data['status'], test_size=0.2, random_state=42)

# Pipeline: Convert text n-grams -> Linear Support Vector Classifier

model = make_pipeline(
    TfidfVectorizer(
        ngram_range=(1, 3),       # (1, 3) rarely beats (1, 2) with TF-IDF
        sublinear_tf=True,        # Dampens outlier frequency counts
        min_df=3,                 # Drops single-occurrence noise
        max_df=0.9                # Drops boilerplate stopwords
    ),
    LinearSVC(class_weight="balanced", random_state=42)
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
