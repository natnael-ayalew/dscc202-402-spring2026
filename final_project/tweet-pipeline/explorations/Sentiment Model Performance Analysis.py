# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # Sentiment Model Performance Analysis
# MAGIC
# MAGIC ## Purpose
# MAGIC Evaluate sentiment classification model performance by comparing predictions against ground truth.
# MAGIC Generate classification metrics and log results to MLflow for experiment tracking.
# MAGIC
# MAGIC ## Requirements
# MAGIC - Load tweets_gold table with predictions and ground truth
# MAGIC - Calculate classification metrics (accuracy, precision, recall, F1)
# MAGIC - Generate confusion matrix visualization
# MAGIC - Log metrics, parameters, and artifacts to MLflow
# MAGIC
# MAGIC ## Expected Output
# MAGIC - Classification report with per-class metrics
# MAGIC - Confusion matrix visualization
# MAGIC - MLflow experiment with accuracy metric and confusion matrix artifact
# MAGIC
# MAGIC ## Reference
# MAGIC See Lab 0.5 (MLops) for MLflow experiment tracking patterns

# COMMAND ----------

# TODO: Import necessary libraries
# You will need:
# - pyspark.sql functions
# - pandas
# - mlflow and MlflowClient
# - delta.tables.DeltaTable
# - matplotlib.pyplot
# - sklearn.metrics (confusion_matrix, classification_report, ConfusionMatrixDisplay)

from pyspark.sql import functions as F
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
from delta.tables import DeltaTable
import matplotlib.pyplot as plt
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Task 1: Load Gold Data
# MAGIC
# MAGIC TODO: Read the tweets_gold table to get predicted and actual sentiments
# MAGIC - Load table using spark.read.format("delta").table()
# MAGIC - Table contains sentiment_id (ground truth) and predicted_sentiment_id (model prediction)
# MAGIC - Both are binary: 0=negative, 1=positive/neutral

# COMMAND ----------

# TODO: Load gold table

gold_df = spark.read.format("delta").table("workspace.default.tweets_gold")

print(f"Loaded {gold_df.count():,} rows from tweets_gold")
gold_df.select("sentiment_id", "predicted_sentiment_id", "predicted_sentiment").show(5)


# COMMAND ----------

# MAGIC %md
# MAGIC ## Task 2: Generate Classification Report
# MAGIC
# MAGIC TODO: Convert to pandas and compute classification metrics
# MAGIC 1. Convert gold DataFrame to pandas using .toPandas()
# MAGIC 2. Extract y_true from sentiment_id column
# MAGIC 3. Extract y_pred from predicted_sentiment_id column
# MAGIC 4. Define target_names as ["Negative", "Positive"]
# MAGIC 5. Generate classification_report with output_dict=True
# MAGIC
# MAGIC Reference: sklearn.metrics.classification_report

# COMMAND ----------

# TODO: Generate classification report

# Convert to pandas
gold_pdf = gold_df.select("sentiment_id", "predicted_sentiment_id").toPandas()

# Extract ground truth and predictions
y_true = gold_pdf["sentiment_id"]
y_pred = gold_pdf["predicted_sentiment_id"]

# Per-class metric names
target_names = ["Negative", "Positive"]

# Generate the report as a dict (for MLflow logging) and as text (for printing)
report_dict = classification_report(
    y_true, y_pred,
    target_names=target_names,
    output_dict=True,
    zero_division=0,
)

print(classification_report(
    y_true, y_pred,
    target_names=target_names,
    zero_division=0,
))


# COMMAND ----------

# MAGIC %md
# MAGIC ## Task 3: Create Confusion Matrix
# MAGIC
# MAGIC TODO: Visualize model performance with confusion matrix
# MAGIC 1. Generate confusion matrix using sklearn.metrics.confusion_matrix
# MAGIC 2. Create ConfusionMatrixDisplay with target names
# MAGIC 3. Plot and display the matrix
# MAGIC
# MAGIC Confusion Matrix Layout:
# MAGIC                Predicted
# MAGIC              Neg    Pos
# MAGIC Actual  Neg   TN     FP
# MAGIC        Pos   FN     TP

# COMMAND ----------

# TODO: Create and display confusion matrix

# Layout: rows = actual, cols = predicted
#         [[TN, FP],
#          [FN, TP]]
cm = confusion_matrix(y_true, y_pred)

disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=target_names)
fig, ax = plt.subplots(figsize=(6, 5))
disp.plot(ax=ax, cmap="Blues", values_format="d")
ax.set_title("Sentiment Model — Confusion Matrix")
plt.tight_layout()

# Save for the MLflow artifact step (Task 4)
cm_path = "/tmp/confusion_matrix.png"
plt.savefig(cm_path, dpi=120)
plt.show()


# COMMAND ----------

# MAGIC %md
# MAGIC ## Task 4: Log Results to MLflow
# MAGIC
# MAGIC TODO: Track model performance in MLflow experiment
# MAGIC 1. Set MLflow registry to Unity Catalog: mlflow.set_registry_uri("databricks-uc")
# MAGIC 2. Get Delta table version from tweets_silver (for data lineage)
# MAGIC 3. Start MLflow run
# MAGIC 4. Log metrics:
# MAGIC    - accuracy from classification report
# MAGIC 5. Log parameters:
# MAGIC    - model_name: "workspace.default.tweet_sentiment_model"
# MAGIC    - model_version: 1
# MAGIC    - silver_delta_version: from Delta table history
# MAGIC 6. Log artifact:
# MAGIC    - confusion matrix figure as "confusion_matrix.png"
# MAGIC
# MAGIC Reference: Lab 0.5 for MLflow logging patterns

# COMMAND ----------

# TODO: Log metrics and artifacts to MLflow

# 1. Set MLflow registry to Unity Catalog
mlflow.set_registry_uri("databricks-uc")

# 2. Get Delta table version from tweets_silver (data lineage)
silver_version_row = spark.sql(
    "DESCRIBE HISTORY workspace.default.tweets_silver LIMIT 1"
).collect()[0]
silver_delta_version = silver_version_row["version"]
print(f"Silver Delta version: {silver_delta_version}")

# 3. Start MLflow run
with mlflow.start_run(run_name="sentiment_model_evaluation") as run:
    # 4. Log metrics — accuracy from classification report
    mlflow.log_metric("accuracy", report_dict["accuracy"])
    mlflow.log_metric("precision_negative", report_dict["Negative"]["precision"])
    mlflow.log_metric("recall_negative", report_dict["Negative"]["recall"])
    mlflow.log_metric("f1_negative", report_dict["Negative"]["f1-score"])
    mlflow.log_metric("precision_positive", report_dict["Positive"]["precision"])
    mlflow.log_metric("recall_positive", report_dict["Positive"]["recall"])
    mlflow.log_metric("f1_positive", report_dict["Positive"]["f1-score"])
    mlflow.log_metric("f1_macro", report_dict["macro avg"]["f1-score"])

    # 5. Log parameters
    mlflow.log_param("model_name", "workspace.default.tweet_sentiment_model")
    mlflow.log_param("model_version", 1)
    mlflow.log_param("silver_delta_version", silver_delta_version)

    # 6. Log artifact — confusion matrix figure
    mlflow.log_artifact(cm_path, artifact_path="confusion_matrix.png")

    print(f"\n✅ MLflow run logged: {run.info.run_id}")
    print(f"   Accuracy: {report_dict['accuracy']:.4f}")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation
# MAGIC
# MAGIC After running this notebook, verify in the MLflow UI:
# MAGIC 1. Navigate to "Experiments" tab
# MAGIC 2. Find experiment for this notebook
# MAGIC 3. Check latest run contains:
# MAGIC    - accuracy metric (e.g., 0.85 = 85% correct)
# MAGIC    - model_name, model_version, silver_delta_version parameters
# MAGIC    - confusion_matrix.png artifact
# MAGIC
# MAGIC ## Interpreting Results
# MAGIC
# MAGIC **Accuracy**:
# MAGIC - High (>80%): Model performing well
# MAGIC - Low (<70%): Consider different model or fine-tuning
# MAGIC
# MAGIC **Confusion Matrix**:
# MAGIC - Diagonal (TN, TP): Correct predictions
# MAGIC - Off-diagonal (FP, FN): Misclassifications
# MAGIC - Imbalanced: May indicate class imbalance or bias
# MAGIC
# MAGIC **Next Steps**:
# MAGIC - If accuracy low: Try different model, improve preprocessing
# MAGIC - If confusion matrix shows bias: Investigate class distribution, confidence thresholds
