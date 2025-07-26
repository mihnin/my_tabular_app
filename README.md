# 📊 Predictive Analytics & Classification Platform

### Executive Summary
This universal application is a deployable tool for solving core business challenges using machine learning on tabular data. It empowers companies to answer critical questions like: "Will this customer churn?", "What is the probability of this component failing?", or "Which segment does this product belong to?". The platform automates the complex process of building classification and regression models, making predictive analytics accessible to business experts, not just data scientists.

---

### 📈 Business Impact & Core Features

* **Increased Profitability:** Reduce customer churn, optimize marketing campaigns, and prevent fraud based on accurate, data-driven predictions.
* **Risk Mitigation:** Forecast the probability of undesirable events—from equipment failure to flight delays—and take preemptive action.
* **Operational Efficiency:** Automate routine analytical tasks, allowing your team to focus on interpreting results and making strategic decisions.
* **Ease of Use:** The intuitive web interface allows any manager to upload data, select a target variable (e.g., "churn status"), and train a powerful predictive model without writing a single line of code.

---

### 🏆 Proven Results: Customer Churn Reduction Case Study

This platform was successfully deployed at a major retail bank to build a customer churn prediction model. By analyzing transactional activity and customer profiles, the model identified clients with a high probability of leaving.

**Implementation Results:**
* **A 25% reduction in customer churn** achieved through targeted retention offers.
* **A 40% increase in marketing campaign efficiency** by focusing the budget solely on at-risk groups.

---

### ✈️ Relevance for the Airline Industry

This application directly addresses the goals of **enhancing operational efficiency and improving customer experiences**. It enables the creation of powerful predictive models for numerous airline-specific scenarios:

* **Frequent Flyer Churn Prediction:** Identify loyal customers who are likely to switch to a competitor, enabling proactive retention campaigns.
* **Predictive Maintenance (MRO):** Classify the health of aircraft components ("will fail" / "will not fail") based on telemetry data to optimize maintenance schedules and increase safety.
* **Flight Delay Prediction:** Determine the probability of a flight being delayed based on route, weather, and aircraft type to improve operational planning and customer communication.
* **Fraud Detection:** Analyze ticket purchases and loyalty program transactions to identify and prevent fraudulent activity in real-time.
* **Customer Segmentation:** Group passengers based on their behavior and preferences to deliver personalized marketing offers and enhance service quality.

---

## 🚀 Live Demo & Technical Guide

This section provides all the necessary information to run the application locally and test its functionality.

### Technical Stack
* **Backend:** Python, FastAPI, AutoGluon (for automated machine learning)
* **Core Libraries:** Pandas, NumPy, Scikit-learn
* **Frontend:** Vue.js
* **Deployment:** Docker, Docker Compose

### Quick Start with Docker (Recommended)

1.  Clone the repository and navigate to the project folder:
    ```sh
    git clone <your_repository_url>
    cd my_tabular_app
    ```

2.  Run all services with a single command:
    ```sh
    docker-compose up --build
    ```

* After building and launching:
    * **Frontend** will be available at: `http://localhost:4173`
    * **Backend (API)** will be available at: `http://localhost:8000`

> **Note:** After opening the application for the first time, set up a secret word. This will be used for configuring the database connection later. To do this, select advanced user settings, go to DB connection settings, and enter the secret word.

### Data Format Requirements (Excel)

* **First Sheet Only:** Training data must be on the first sheet of the Excel file.
* **Header Row:** The first row must contain all column names (features and the target variable).
* **Data from Second Row:** Data entries must start from the second row.
* **Consistent Data Types:** Each column must contain values of a single data type (e.g., numbers, text, dates).
* **No Merged Cells:** The file must not contain merged cells, hidden rows/columns, or formulas.
* **Recommended Formats:** Use `.xlsx` or `.xls`.

### Application Usage (User Guide)

1.  **Connect to Database (Optional)**
    * To load/save data from/to a database, connect to your PostgreSQL instance via the UI (database icon in the top-right corner).

2.  **Load Training and Prediction Data**
    * **From a file:** Use the "Choose File" buttons for both training and prediction datasets, then click "Load Data from File".
    * **From a database:** After connecting, the option to "Load Data from DB" will become available. Select your schema and table.

3.  **Select Target Column and Problem Type**
    * You **must select the target column** for training.
    * Choose the problem type:
        * `auto` - Automatic detection (recommended)
        * `binary` - Binary classification
        * `multiclass` - Multiclass classification
        * `regression` - Regression

4.  **Advanced Settings (Optional)**
    * **Missing Value Imputation:** Default is "mean".
    * **Evaluation Metric:** Select a metric for training (e.g., accuracy, f1, r2).
    * **Models:** Choose specific models for training.
    * **AutoGluon Presets:** Select a training strategy (e.g., `medium_quality`, `high_quality`, `best_quality`).
    * **Time Limit:** Set a time limit for the training process.

5.  **Start Training and Prediction**
    * Click **"Start Training"**. If the "Train, Save, and Predict" option is selected, a prediction will be automatically generated after training is complete. You can then download the results or save them to the database.

---

### Manual Start (Alternative)

1.  **Prerequisites:** Install Python 3.10+ and Node.js 18+.
2.  **Install Dependencies:**
    * **Backend:** `pip install -r backend/requirements.txt`
    * **Frontend:** `cd frontend && npm install && npm run build-only`
3.  **Start the Backend:**
    ```sh
    cd backend/app
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
4.  **Start the Frontend:**
    ```sh
    cd frontend
    npm run preview -- --host --port 4173
    ```

