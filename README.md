# 🧠 Enhanced SQL Intelligent Tutoring System with Ontology Integration

**Author:** Cruz Bello
**Project Type:** Intelligent Tutoring System / Semantic Web / SQL Education

---

## 📌 Overview

The **Enhanced SQL Intelligent Tutoring System (ITS)** is a desktop-based educational application designed to help learners **understand, write, debug, and optimize SQL queries** using a **rule-based ontology-driven approach**.

Unlike traditional SQL checkers, this system integrates **Semantic Web technologies (OWL + RDF + SPARQL)** with **programmatic SQL analysis**, enabling:

* Intelligent error detection
* Ontology-based explanations
* Personalized learning paths
* Concept prerequisite tracking

The application is implemented in **Python** using **Tkinter** for the GUI and **SQLite** as an execution sandbox.

---

## ✨ Key Features

### 🧩 Ontology-Driven Intelligence

* Uses an **OWL ontology** to represent:

  * SQL concepts (SELECT, WHERE, GROUP BY, JOIN, etc.)
  * Error types and explanations
  * Learning prerequisites
* SPARQL queries dynamically extract knowledge

### 🔍 Advanced SQL Analysis

* Syntax validation (clause order, missing keywords)
* Semantic validation:

  * Aggregates in WHERE
  * Missing GROUP BY
  * HAVING without GROUP BY
  * Ambiguous columns
* Schema-aware validation against ontology-defined tables

### 🎓 Personalized Learning Path

* Automatically recommends SQL topics based on detected errors
* Orders concepts by difficulty
* Displays prerequisite relationships

### 📊 Safe Query Execution

* Executes **SELECT-only** queries in a sandboxed SQLite database
* Prevents destructive SQL commands (DROP, DELETE, UPDATE, etc.)
* Displays results and row counts

### 🖥️ Rich Desktop GUI

* Tkinter-based interface
* Multiple tabs:

  * Analysis & Feedback
  * Query Results
  * Learning Path
* Color-coded feedback (errors, suggestions, ontology hints)

---

## 🏗️ System Architecture

```
+-------------------+
|   Tkinter GUI     |
+-------------------+
          |
          v
+-------------------+
| SQLTutorEngine    |
| - Syntax checks   |
| - Semantic rules  |
| - Execution       |
+-------------------+
          |
          v
+-------------------+
| OntologyManager   |
| - OWL / RDF       |
| - SPARQL Queries  |
| - Learning paths  |
+-------------------+
```

---

## 🧠 Ontology Components

The ontology (`sql_tutor_ontology.owl`) defines:

* **Classes**:

  * `SQLQuery`
  * `SQLConcept`
  * `Error`
  * `Suggestion`
  * `Table`, `Column`

* **Relationships**:

  * Concept prerequisites
  * Column-to-table mappings
  * Error explanations

If the ontology file is missing, the system **auto-generates a minimal ontology** to remain functional.

---

## 📚 Sample Database Schema

Loaded dynamically from the ontology:

* **employees**

  * emp_id (PK)
  * first_name
  * last_name
  * department
  * salary
  * hire_date
  * manager_id

* **departments**

  * dept_id (PK)
  * dept_name
  * location
  * budget

* **projects**

  * project_id (PK)
  * project_name
  * department
  * start_date
  * end_date
  * budget

---

## 🚀 Getting Started

### ✅ Prerequisites

```bash
pip install sqlparse rdflib
```

(Standard libraries used: `tkinter`, `sqlite3`, `datetime`, `re`)

---

### ▶️ Running the Application

```bash
python sql_tutor.py
```

The GUI window will open automatically.

---

## 🧪 Example Queries

```sql
SELECT department, AVG(salary) AS avg_salary
FROM employees
GROUP BY department
ORDER BY avg_salary DESC;
```

```sql
SELECT e.first_name, e.last_name, d.dept_name
FROM employees e
JOIN departments d ON e.department = d.dept_name
WHERE e.salary > 60000;
```

---

## 🎯 Educational Use Cases

* Undergraduate & postgraduate SQL courses
* Intelligent tutoring systems research
* Semantic Web + Education projects
* MSc / PhD coursework and dissertations

---

## 🔐 Safety & Limitations

* Only **SELECT** queries are allowed
* No external database connections
* SQLite used purely for learning

---

## 📈 Future Enhancements

* Web-based version (Flask / FastAPI)
* User progress persistence
* Adaptive difficulty scaling
* LLM-assisted explanations (hybrid symbolic + AI)
* Integration with PostgreSQL / Oracle

---

## 👤 Author

**Cruz Bello**
SQL • Data Systems • Semantic Web • Intelligent Tutoring Systems

---

## 📜 License

This project is provided for **educational and research purposes**.
You are free to modify and extend it with attribution.

---

⭐ *If you find this project useful, consider starring the repository!*
