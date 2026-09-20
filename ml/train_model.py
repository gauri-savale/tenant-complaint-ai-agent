"""
ml/train_model.py
------------------
Trains a classical ML pipeline (TF-IDF -> Logistic Regression) to predict
a complaint's CATEGORY from its free-text description.

Run standalone:
    python ml/train_model.py

Outputs:
    ml/model/category_vectorizer.joblib
    ml/model/category_model.joblib
    ml/model/metrics.json
    ml/model/confusion_matrix.png

This demonstrates: text preprocessing, TF-IDF feature extraction,
train/test split, model training, and standard evaluation metrics
(accuracy, precision, recall, F1, confusion matrix) — required
academic ML content distinct from the LLM/agent layer.

NOTE: data/training_data.csv is a small DEMONSTRATION dataset built for
this course project. A production deployment would train on thousands
of real, anonymized historical complaints for meaningfully higher
accuracy and better generalization across property-specific vocabulary.
"""

import json
import os
import sys

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

TRAINING_DATA_PATH = os.path.join(BASE_DIR, "data", "training_data.csv")
MODEL_DIR = os.path.join(BASE_DIR, "ml", "model")


def train_and_evaluate():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = pd.read_csv(TRAINING_DATA_PATH)
    df = df.dropna(subset=["text", "category"])

    print(f"Loaded {len(df)} labeled examples across {df['category'].nunique()} categories.")

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["category"], test_size=0.2, random_state=42, stratify=df["category"]
    )

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, max_features=3000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0
    )
    report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)

    print(f"\nAccuracy:  {accuracy:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1-score:  {f1:.3f}\n")
    print(classification_report(y_test, y_pred, zero_division=0))

    labels = sorted(df["category"].unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Predicted category")
    ax.set_ylabel("True category")
    ax.set_title("Confusion Matrix — Complaint Category Classifier")
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=7)
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(os.path.join(MODEL_DIR, "confusion_matrix.png"), dpi=150)
    plt.close(fig)

    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "category_vectorizer.joblib"))
    joblib.dump(model, os.path.join(MODEL_DIR, "category_model.joblib"))

    metrics = {
        "accuracy": round(accuracy, 4),
        "precision_weighted": round(precision, 4),
        "recall_weighted": round(recall, 4),
        "f1_weighted": round(f1, 4),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "labels": labels,
        "per_class_report": report,
        "note": (
            "Small demonstration dataset built for a college project. "
            "A real deployment should train on thousands of anonymized "
            "historical complaints for stronger generalization."
        ),
    }
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nSaved model, vectorizer, metrics.json and confusion_matrix.png to {MODEL_DIR}")
    return metrics


if __name__ == "__main__":
    train_and_evaluate()
