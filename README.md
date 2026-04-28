

# Domain-agnostic-framework-for-analyzing-social-discourse

A comprehensive end-to-end pipeline for analyzing social discourse. This framework scrapes raw data from Reddit, filters noise, optimizes it for Large Language Models (LLMs), builds a Knowledge Graph, performs multi-lens analysis, and visualizes the results via a local-first dashboard.

---

## 🚀 Installation & Setup

### 1. System Prerequisites
*   **Python 3.8+**
*   **Local LLM Model**: Download a `.gguf` model (e.g., Llama 3, Qwen, Mistral) to run locally.
*   **Reddit Account**: Required to scrape data.

### 2. Install Python Dependencies

```bash
# Create a virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## 🗄️ Neo4j Installation & Setup

This project relies on **Neo4j** to store and visualize the Knowledge Graph. You must have a local instance running on port `7687`.

### Option A: Neo4j Desktop (Recommended - GUI)
1.  **Download**: Go to [Neo4j Download Page](https://neo4j.com/download/) and install **Neo4j Desktop**.
2.  **Create a Project**: Open the app, click "New Project", and give it a name.
3.  **Add a Database**: Inside the project, click "Add Database" -> "Create Local Database".
4.  **Set Password**:
    *   In the setup form, set the **Password**.
    *   **Important:** The Python scripts are hardcoded to use the password `12345`.
    *   *Suggestion:* Set the password to `12345` to avoid having to edit the code. If you choose a different password, you **must** update `NEO4J_PASSWORD` in `dashboard.py`, `step4_extract_graph.py`, `step5_final_graph_synthesis.py`, and `step6_scenario_generator.py`.
5.  **Start**: Click "Start" on the database card. Wait for the status to turn Active.

### Option B: Docker (Fast Setup)
If you have Docker installed, run this single command to start a Neo4j instance:

```bash
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/12345 \
    -d neo4j:latest
```
*(Note: This sets the user to `neo4j` and password to `12345` automatically).*

---

## 🔐 Configuration (Reddit & Paths)

### A. Setup `.env` File (For Reddit Scraper)
1.  Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
2.  Click **"create app"** (or **"create another app"**).
3.  Fill the form:
    *   **Name**: Any name (e.g., `SocialDiscourseBot`).
    *   **App Type**: Select **"script"** (Crucial!).
    *   **Description**: (Optional).
    *   **About url**: `http://localhost:8080`.
    *   **Redirect uri**: `http://localhost:8080`.
4.  Click **"create app"**.
5.  Copy the **Client ID** (top string) and **Client Secret** (bottom string).

Create a file named `.env` in the project root:

```text
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
```

### B. Configure Local LLM Path
Update the `MODEL_PATH` variable in the following files to point to your downloaded `.gguf` file:
*   `step4_extract_graph.py`
*   `step5_final_graph_synthesis.py`
*   `step6_scenario_generator.py`

---

## 📊 Understanding Data Scraping

The data collection is handled by `reddit.py`.

*   **Mechanism**: It uses the `praw` library to search Reddit globally based on specific topics defined in the script.
*   **Search Strategy**: It cycles through multiple Reddit sort orders (Relevance, New, Top, Comments, Hot) to ensure it gathers the maximum number of unique posts with actual content (selftext).
*   **Data Depth**: For every post found, it fetches:
    *   Post metadata (author karma, score, created time).
    *   **Top N Comments**: Fetches the highest-voted comments.
    *   **Replies**: Fetches replies to those comments to capture conversation depth.
*   **Output**: Saves rich JSON files into a `reddit_outputs/` directory.

---

## 🛠️ Execution Guide (Manual Pipeline)

The pipeline consists of **8 sequential steps**. You must run them in order.

### Step 1: Scrape Data from Reddit
This creates the raw input dataset.

```bash
python reddit.py
```
*   *Result:* A new folder `reddit_outputs` will appear containing JSON files.

### Step 2: Prepare Input for Pipeline
*(Note: The filtering script is currently hardcoded to look for a specific file name.)*

1.  Go to the `reddit_outputs` folder.
2.  Find the JSON file for the topic you want to analyze.
3.  **Rename** that file to `raw_reddit.json`.
4.  **Move** `raw_reddit.json` into the root directory of the project.

### Step 3: Filter and Clean Data
Removes spam, low-quality posts, and empty comments.

```bash
python step1_filter.py
```

### Step 4: Batching
Optimizes data into 16k token batches to fit the LLM context window efficiently.

```bash
python step2_batching.py
```

### Step 5: Compression
Converts JSON data to structured text to save tokens during processing.

```bash
python step3_compress.py
```

### Step 6: Graph Construction
Extracts entities and relationships using the local LLM and builds a Knowledge Graph in Neo4j.

```bash
python step4_extract_graph.py
```

### Step 7: Multi-Lens Analysis
Analyzes the graph through 7 different expert perspectives (Psychology, Economics, Power, etc.).

```bash
python step5_final_graph_synthesis.py
```

### Step 8: Scenario Generation
Generates final strategic scenarios based on the analysis.

```bash
python step6_scenario_generator.py
```

### Step 9: Launch Dashboard
Visualize the final report and the interactive Knowledge Graph.

```bash
streamlit run dashboard.py
```

---

## 🐛 Troubleshooting

1.  **`MissingEnvFile` or `EnvironmentError`**: Ensure you created the `.env` file with your Reddit credentials in the root directory.
2.  **403 Forbidden (Reddit)**: In your Reddit App preferences, ensure the **App Type** is set to **"script"** and the **Redirect URI** is `http://localhost:8080`.
3.  **Neo4j Connection Failed**: Ensure the Neo4j service is running (Desktop "Start" button or Docker command) and the password in the python files matches your database password (`12345`).
4.  **File Not Found (Step 2)**: Remember to rename/move the file from `reddit_outputs` to `raw_reddit.json` in the root folder.
