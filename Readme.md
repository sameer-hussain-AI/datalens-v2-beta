# Data Lens V2

### Intelligent Data Analysis & Data Quality Assessment Platform

Data Lens V2 is a web-based data analysis platform designed to help users explore, assess, clean, visualize, and understand their datasets through a professional and user-friendly interface.

Built with a modern frontend and a Python-powered backend, Data Lens V2 makes essential data analysis tasks easier without requiring users to write code.

## Features

- **Dataset Overview:** View file information, rows, columns, total entries, missing values, duplicates, column names, and data types.
- **Data Preview:** Explore uploaded datasets directly in the application.
- **Data Quality Assessment:** Identify missing values, duplicate records, and other data quality issues.
- **Data Cleaning:** Clean datasets and download the processed data.
- **Data Visualization:** Generate different charts, including bar charts, line charts, scatter plots, histograms, pie charts, box plots, area charts, horizontal bar charts, and correlation heatmaps.
- **Statistical Analysis:** Explore numerical data through statistical summaries and analysis.
- **CSV and Excel Support:** Upload supported dataset formats for analysis.

## Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- FastAPI
- Pandas
- NumPy

### Data Visualization
- Matplotlib

### Development Tools
- Visual Studio Code
- Git
- GitHub

## Project Structure

```text
Data-Lens-V2/
│
├── backend/
│   ├── main.py
│   ├── data_overview.py
│   ├── data_preview.py
│   ├── data_quality.py
│   ├── data_cleaning.py
│   ├── data_viz.py
│   └── statistical.py
│
├── index.html
├── style.css
├── script.js
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sameer-hussain-AI/Data-Lens-V2.git
```

### 2. Navigate to the Project Folder

```bash
cd Data-Lens-V2
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Backend

Navigate to the backend folder:

```bash
cd backend
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

### 6. Open the Application

Open the frontend using the project's configured local frontend route or development setup.

FastAPI API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Project Goal

The goal of Data Lens V2 is to develop an accessible and practical data analysis platform that combines data exploration, data quality assessment, cleaning, visualization, and statistical analysis in one application.

## Developer

**Sameer Hussain**

Aspiring Data Analyst | Python | SQL | Power BI | Data Analytics

GitHub: [sameer-hussain-AI](https://github.com/sameer-hussain-AI)

LinkedIn: [Sameer Hussain](https://www.linkedin.com/in/sameer-hussain-920722356/)

---

*Data Lens V2 — Making Data Analysis Simpler.*
