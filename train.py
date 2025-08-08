"""
train.py - Trains an XGBoost classifier on the Penguins dataset.
"""

import seaborn as sns
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score
from xgboost import XGBClassifier

# 1. Load the dataset
df = sns.load_dataset("penguins")
df.dropna(inplace=True)

# 2. One-hot encode categorical features
df = pd.get_dummies(df, columns=["sex", "island"])

# 3. Label encode the target
le = LabelEncoder()
df["species"] = le.fit_transform(df["species"])

# 4. Split into features and target
X = df.drop(columns=["species"])
y = df["species"]

# 5. Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 6. Train XGBoost classifier
model = XGBClassifier(max_depth=3, n_estimators=100, use_label_encoder=False, eval_metric='mlogloss')
model.fit(X_train, y_train)

# 7. Evaluate the model
train_pred = model.predict(X_train)
test_pred = model.predict(X_test)

train_f1 = f1_score(y_train, train_pred, average='weighted')
test_f1 = f1_score(y_test, test_pred, average='weighted')

print(f"Train F1 Score: {train_f1:.4f}")
print(f"Test F1 Score: {test_f1:.4f}")

# 8. Save the model
model.save_model("app/data/model.json")

# 9. Save label encoding map
label_map = dict(zip(le.classes_, le.transform(le.classes_)))
pd.Series(label_map).to_json("app/data/label_map.json")

print("Model and label map saved.")
