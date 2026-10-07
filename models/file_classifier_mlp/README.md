# Evidence File-Type Classifier

This directory contains the file-fragment classification example in CrimeGraph AI.

## Objective and design

The classifier demonstrates predicting a file category from a hexadecimal byte fragment. A `TfidfVectorizer` extracts weighted unigram and bigram tokens (up to 500 features). The project evaluates two classifiers:

- **Random Forest baseline:** 100 trees, maximum depth 20. A tree ensemble is not trained in epochs.
- **TF-IDF + MLP:** hidden layers `[128, 64]`, ReLU activation, Adam optimizer, learning rate `0.001`, batch size 64. The default training run uses 50 epochs via `partial_fit`.

The training utilities calculate SHAP values for the Random Forest baseline. The deployed app instead reports recognized file-header signatures as diagnostic context; those markers are not SHAP explanations and do not prove a file's origin.

## Data and evaluation

The default loader generates Govdocs1-style synthetic byte fragments in six categories: `PDF_DOCUMENT`, `OFFICE_DOCX`, `JPEG_IMAGE`, `EXECUTABLE_PAYLOAD`, `TEXT_LOG`, and `ARCHIVE_ZIP`. It does **not** currently train and evaluate on the original Govdocs1 corpus. Data are split into training, validation, and test sets; TF-IDF is fit only on training text. Scores from generated examples demonstrate the pipeline but are not real-world accuracy claims.

After training, each model's held-out test metrics are saved separately:

| CSV file | Model |
|---|---|
| `saved_models/mlp_metrics.csv` | TF-IDF + MLP |
| `saved_models/random_forest_metrics.csv` | Random Forest baseline |

The files report accuracy, weighted precision/recall/F1, macro F1, training duration, data source, and epoch/training-method information. Run the training script before quoting numbers.

## Artifacts

| File | Purpose |
|---|---|
| `dataset.py` | Generates benchmark fragments; contains an optional local-file reader. |
| `model.py` | TF-IDF, Random Forest, and MLP pipeline definitions. |
| `train.py` | Training, validation, test metrics, CSV export, and SHAP plot generation. |
| `saved_models/mlp_classifier.joblib` | Trained MLP used by the API. |
| `saved_models/rf_baseline.joblib` | Trained baseline. |
| `saved_models/tfidf_vectorizer.joblib` | Fitted TF-IDF transformer used by inference. |
| `saved_models/mlp_metrics.csv` | MLP held-out test metrics. |
| `saved_models/random_forest_metrics.csv` | Random Forest held-out test metrics. |
| `saved_models/model_comparison.json` | Comparison metrics and MLP epoch history. |
| `saved_models/shap_summary.png` | Random Forest SHAP summary from the training utility. |

## Run training (Windows PowerShell)

From the repository root with its Python environment active:

```powershell
$env:PYTHONPATH = "."
python models\file_classifier_mlp\train.py
```

The script explicitly uses 50 epochs. The API loads the serialized MLP and fitted TF-IDF artifact from this directory.
