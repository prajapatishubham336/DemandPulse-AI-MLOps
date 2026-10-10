# DemandPulse-AI-MLOps
End-to-end demand forecasting and MLOps platform built with Python and FastAPI, featuring data uploads, ML forecasting, product comparison, and a web dashboard.


# 📊 DemandPulse AI MLOps

### End-to-End Demand Forecasting & MLOps Platform

<p align="center">
  <strong>Forecast demand. Compare products. Make data-driven decisions.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Machine%20Learning-Forecasting-orange" alt="Machine Learning">
  <img src="https://img.shields.io/badge/MLOps-Pipeline-purple" alt="MLOps">
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

---

## 🚀 Overview

**DemandPulse AI MLOps** is an end-to-end demand forecasting platform designed to help users analyze historical demand data, generate forecasts, and compare demand across products and stores.

The project combines a FastAPI backend, a browser-based dashboard, and modular machine learning pipeline components to support the demand forecasting workflow.

The application includes data upload and validation, preprocessing, feature engineering, forecasting, model tuning, demand segmentation, and inventory-related functionality through dedicated modules.

The goal is to turn historical demand data into useful insights that can support inventory planning, product analysis, and business decision-making.

---

🌐 **Live Demo:** [DemandPulse AI MLOps](https://demandpulse-ai-mlops.onrender.com/)

📘 **API Documentation:** [Swagger UI](https://demandpulse-ai-mlops.onrender.com/docs)

---

## ✨ Features

* **📈 Demand Data Upload:** Upload demand datasets for analysis through the application.
* **🧹 Data Validation:** Validate incoming data before processing.
* **🤖 Data Preprocessing:** Prepare historical demand data for forecasting.
* **📊 Feature Engineering:** Create model-ready features from available demand history.
* **🔄 Demand Forecasting:** Generate forecasts for a selected product, store, and forecast horizon where supported.
* **⚖️ Product Comparison:** Compare demand patterns across products where implemented.
* **🎛️ Model Tuning:** Provide pipeline components for model configuration and tuning.
* **🧩 Demand Segmentation:** Organize demand using the available segmentation functionality.
* **📦 Inventory Management Module:** Include inventory-related processing components.
* **🖥️ Interactive Dashboard:** Access application functionality through an HTML, CSS, and JavaScript frontend.
* **🔌 REST API:** Expose backend functionality through FastAPI endpoints.
* **💾 Session and Upload Storage:** Maintain application session and uploaded-data files.
* **🩺 Health Check and Testing:** Include a health-check test and support for application testing.
* **🐳 Docker Support:** Package the application for containerized execution.


## 🛠️ Tech Stack

| Technology                 | Purpose                                            |
| -------------------------- | -------------------------------------------------- |
| Python 3.11                | Backend development and machine learning workflows |
| FastAPI                    | Backend API and application server                 |
| Machine Learning Libraries | Data processing and forecasting                    |
| HTML5                      | Dashboard structure                                |
| CSS3                       | Dashboard styling                                  |
| JavaScript                 | Frontend interactions                              |
| pytest                     | Automated testing                                  |
| Docker                     | Application containerization                       |
| Git and GitHub             | Version control and project management             |

Refer to `requirements.txt` for the actual Python dependencies used by the project.

## 🏗️ System Architecture

```text
                    User
                     |
                     v
             Web Dashboard
          HTML / CSS / JavaScript
                     |
                     v
              FastAPI Backend
                app/main.py
                     |
          +----------+-----------+
          |          |           |
          v          v           v
     Data Upload  Validation  Session Store
          |          |
          +----------+
                     |
                     v
              Data Pipeline
                     |
          +----------+-----------+
          |          |           |
          v          v           v
     Preprocessing  Feature    Segmentation
                    Engineering
          |          |           |
          +----------+-----------+
                     |
                     v
             Forecasting Pipeline
                     |
          +----------+-----------+
          |                      |
          v                      v
      Forecasts             Comparisons
          |                      |
          +----------+-----------+
                     |
                     v
              Dashboard Results
```

## 📂Project Structure

```text
DemandPulse-AI-MLOps/
│
├── app/
│   ├── pipeline/
│   │   ├── data_adapter.py
│   │   ├── feature_engineering.py
│   │   ├── forecasting.py
│   │   ├── inventory.py
│   │   ├── models.py
│   │   ├── preprocessing.py
│   │   ├── pretrain.py
│   │   ├── segmentation.py
│   │   ├── tuning.py
│   │   ├── upload_loader.py
│   │   └── validation.py
│   │
│   ├── services/
│   │   └── session_store.py
│   │
│   ├── static/
│   │   ├── script.js
│   │   └── style.css
│   │
│   ├── templates/
│   │   └── index.html
│   │
│   └── main.py
│
├── data/
│   ├── sessions/
│   └── uploads/
│
├── tests/
│   └── test_health.py
│
├── .dockerignore
├── .gitignore
├── Dockerfile
├── requirements.txt
├── run.py
└── README.md
```


## ⚙️ Getting Started

### Prerequisites

* Python 3.11
* Git
* Docker Desktop (optional)

### 1. Clone the repository

```bash
git clone https://github.com/prajapatishubham336/DemandPulse-AI-MLOps.git
cd DemandPulse-AI-MLOps
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.▶️ Run the application

Start the application using the repository's entry point:

```bash
python run.py
```

If the application starts successfully on the default FastAPI port, open:

* Dashboard: http://127.0.0.1:8000
* API documentation: http://127.0.0.1:8000/docs

The actual address depends on the host and port configured in the application.

## 📖 How to Use

1. Open the application dashboard.
2. Upload a supported demand dataset.
3. Select the available product and store options.
4. Configure the forecast horizon if the interface supports it.
5. Generate a demand forecast.
6. Review the forecast results.
7. Compare product demand where the comparison functionality is available.

Refer to the validation and upload modules for supported file formats, required columns, and dataset constraints.

## 🔌 API Documentation

DemandPulse AI MLOps uses FastAPI to expose backend functionality.

Once the application is running, the interactive API documentation is generally available at:

**Swagger UI:** http://127.0.0.1:8000/docs

**ReDoc:** http://127.0.0.1:8000/redoc

These endpoints are available only if the application enables the corresponding documentation routes.

Use the API documentation to inspect available endpoints, request parameters, and response schemas.

## 🔄 MLOps Workflow

The project's modular pipeline supports the following general workflow:

1. **Data Ingestion:** Load historical demand data and uploaded datasets.
2. **Data Validation:** Check data quality and required fields.
3. **Preprocessing:** Prepare the data for downstream processing.
4. **Feature Engineering:** Generate features from available demand history.
5. **Model Preparation and Tuning:** Configure forecasting models and tuning components.
6. **Demand Segmentation:** Apply the available demand segmentation functionality.
7. **Forecast Generation:** Produce demand predictions using the configured forecasting pipeline.
8. **Result Delivery:** Make available forecasts and comparisons accessible through the backend and dashboard.

Specific model algorithms, evaluation metrics, retraining schedules, and production monitoring should be documented according to their actual implementation.

## 🧪 Running Tests

The project includes a health-check test under `tests/`.

Install pytest if it is not already installed:

```bash
pip install pytest
```

Run the test suite from the repository root:

```bash
pytest
```

## 🐳 Docker Deployment

The repository includes a Dockerfile for containerized execution.

Build the Docker image:

```bash
docker build -t demandpulse-ai-mlops .
```

Run the container:

```bash
docker run --rm -p 8000:8000 demandpulse-ai-mlops
```

Open http://127.0.0.1:8000 after confirming that the application starts successfully.

Ensure the Dockerfile uses the correct application startup command and that the configured port matches the port mapping. If uploaded data or session files must persist between container runs, configure an appropriate volume.

The project can run using a CPU-based environment; a GPU is not required for the standard setup.

## ⚙️ Configuration and Data Storage

The application includes directories for uploaded datasets and session-related data.

Before running the project in a production environment:

* Confirm the required dataset format and schema.
* Configure storage paths and access permissions.
* Decide whether uploaded files and session data should persist.
* Validate file uploads and handle invalid datasets safely.
* Avoid committing private datasets, credentials, or generated sensitive files to version control.

## 🚀 Deployment Checklist

* [ ] Verify that the application starts locally.
* [ ] Confirm that the dashboard loads correctly.
* [ ] Test dataset upload and validation.
* [ ] Verify forecasting and product comparison.
* [ ] Run the automated test suite.
* [ ] Configure the correct host and port for the deployment platform.
* [ ] Configure persistent storage if required.
* [ ] Review logs and error handling.
* [ ] Check hosting limits, free-tier restrictions, and billing requirements before deployment.

## 🗺️ Roadmap

* [ ] Document supported datasets and required columns.
* [ ] Add comprehensive tests for data validation and forecasting.
* [ ] Document forecasting models and evaluation metrics.
* [ ] Improve handling of products with insufficient historical data.
* [ ] Add structured logging and request timing.
* [ ] Document model caching and retraining behavior.
* [ ] Add forecasting performance and model comparison reports.
* [ ] Publish deployment instructions for a selected hosting platform.
* [ ] Provide a safe sample dataset for demonstration purposes.

## 🤝Contributing

Contributions, suggestions, and improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement your changes.
4. Add or update tests where appropriate.
5. Submit a pull request describing your changes.

## 🔒 Security

* Keep API keys and credentials out of source control.
* Use environment variables or a secrets manager for sensitive configuration.
* Validate uploaded files before processing.
* Avoid exposing internal stack traces to public users.
* Exclude virtual environments, caches, and private data from Git.
* Configure suitable access controls for uploaded datasets and session storage.

## 📄 License

No license has been specified yet. Add a `LICENSE` file to define the terms under which others may use, modify, and distribute this project.

## 👨‍💻 Author

**Shubham Prajapati**

AI/ML Engineer | Machine Learning | Generative AI

GitHub: [@prajapatishubham336](https://github.com/prajapatishubham336)

---

<p align="center">
  <strong>DemandPulse AI MLOps</strong><br>
  <em>From demand data to actionable forecasts.</em>
</p>
