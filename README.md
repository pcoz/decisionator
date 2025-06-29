# Decisionator: Transactional Analysis Multiple Decision-Making Models Integrator

**Author:** Edward Chalk (edward@fleetingswallow.com)

---

## Overview

**Decisionator** is a Python tool that analyzes complex real-world decision problems using three advanced, Transactional Analysis-based psychological decision-making models. It leverages OpenAI's API to provide multi-model reasoning, full traceability of all considerations, and generates a structured Word report (`.docx`) summarizing the findings.

This tool is ideal for business analysts, technical leaders, organizational psychologists, and anyone who needs a rigorous, multi-perspective breakdown of important choices. A PDF is included in this repo, which explains the psychological decision-making models implemented by the code.

---

## Features

- **Three TA Decision Models:**  
  - *Democratic Ego State Council*  
  - *Second-Order Ego State Negotiations*  
  - *Maslow-TA Matrix*

- **Generates:**  
  - Comprehensive Word document reports with tables and color-coded considerations
  - Everyday language and technical summaries
  - Detailed appendices with all model output

- **Fully open-source, MIT license.**  
  - Free for commercial and non-commercial use, with attribution.

---

## Requirements

- Python 3.8+
- [OpenAI Python SDK](https://pypi.org/project/openai/)
- [python-docx](https://pypi.org/project/python-docx/)
- [numpy](https://pypi.org/project/numpy/)

### Install dependencies

You can install all required dependencies with:

```sh
pip install openai python-docx numpy markdown
````

---

## Platform Support

* **Works on:**

  * Windows (tested on 10/11)
  * MacOS
  * Linux

* **Output:**

  * Generates `.docx` reports readable in Microsoft Word, LibreOffice, Google Docs, etc.

---

## Setup

### 1. Clone the Repository

```sh
git clone https://github.com/yourusername/decisionator.git
cd decisionator
```

### 2. Obtain an OpenAI API Key

* Sign up at [OpenAI](https://platform.openai.com/)
* Create an API key

### 3. Set Your API Key as an Environment Variable

**Linux/Mac:**

```sh
export OPENAI_API_KEY=sk-xxxxxx
```

**Windows (CMD):**

```cmd
set OPENAI_API_KEY=sk-xxxxxx
```

**Windows (PowerShell):**

```powershell
$env:OPENAI_API_KEY="sk-xxxxxx"
```

---

### 4. (Optional) Set the OpenAI Model Used

By default, the tool uses the GPT-4.1 Turbo model (`gpt-4-1106-preview`).

**To change the model (e.g., to `gpt-4o` or `gpt-3.5-turbo`):**

1. Open `decisionator.py` in a text editor.

2. Locate the following lines in the `_call_openai_api` method (search for `# === MODEL OPTIONS (uncomment ONE) ===`):

   ```python
   # === MODEL OPTIONS (uncomment ONE) ===

   # GPT-4.1 Turbo (high quality, efficient)
   model="gpt-4-1106-preview",

   # model="gpt-4o",
   # model="gpt-3.5-turbo",
   ```

3. Uncomment the model you wish to use, and comment out the others.
   Only **one** `model=` line should be active at a time.

   For example, to use `gpt-4o`, change the block to:

   ```python
   # === MODEL OPTIONS (uncomment ONE) ===

   # model="gpt-4-1106-preview",
   model="gpt-4o",
   # model="gpt-3.5-turbo",
   ```

4. Save the file.

> For a list of available model names, see [OpenAI’s Model Documentation](https://platform.openai.com/docs/models).

---

## Usage

From your terminal in the project directory:

```sh
python decisionator.py
```

* You will be prompted to **enter your decision problem** (multi-line, Markdown accepted).

  * End input by pressing Enter twice on an empty line.

* The tool will:

  * **Detect decision options** from your text (shows you a list)
  * **Run all three TA models** using the OpenAI API
  * **Aggregate and deduplicate all considerations**
  * **Generate a color-coded, structured Word report** (`TA_Decision_Report_[TIMESTAMP].docx`)

### **Input Notes:**

* Input can be multi-line, and can include Markdown (headings, lists, etc.)
* The clearer you state the decision and the available options, the better the results.

### **Output:**

* Report file in `.docx` format with:

  * All considerations, grouped by option, positive/negative, and scored
  * Summaries and recommendations in both plain English and technical terms
  * Full model output as an appendix

---

## License

MIT License (see the top of `decisionator.py`).

Commercial and non-commercial use permitted with attribution to Edward Chalk ([edward@fleetingswallow.com](mailto:edward@fleetingswallow.com)).

---

## Attribution

If you use this project, please star the repo and cite Edward Chalk as the original author.
Feel free to fork, adapt, and extend for your use case!

---

## Contact

Questions, ideas, or contributions?
Email: [edward@fleetingswallow.com](mailto:edward@fleetingswallow.com)

```
