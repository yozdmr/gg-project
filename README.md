# gg-project
 
CS337 Project 1 -- Tweet Mining & The Golden Globes 

This project uses a variety of natural language processing (NLP) and text-processing libraries for handling various text-related tasks. The following libraries are included in the project:

## Libraries Overview

1. **SpaCy**: A powerful NLP library for advanced text processing such as tokenization, lemmatization, named entity recognition, etc.
    - Model: `en_core_web_sm` (Small English model for NLP tasks).
   
2. **NLTK**: The Natural Language Toolkit (NLTK) is a comprehensive library for working with human language data (text) in Python, including text classification, tokenization, stemming, tagging, parsing, and more.

3. **JupyterLab**: A web-based interactive development environment for Jupyter notebooks, code, and data.

4. **FTFY**: Fixes text encoding issues, like repairing mojibake (encoding errors), and ensures proper display of text.

5. **Unidecode**: Converts Unicode text (e.g., accented characters) into ASCII text, useful for simplifying text handling.

6. ***langdetect**: A simple and lightweight language detection library for Python, based on Google's language-detection library, that identifies the language of a given text input.

7. **Inflection**: Provides methods to singularize or pluralize English nouns, and other useful inflection tasks for English grammar.

## Setup Instructions

The setup process automates the creation of a Conda environment, installs the required libraries from a `environment.yml` file. Create the environment, activate it, then download the SpaCy language model.

### Prerequisites

Make sure you have the following installed on your machine:

- **Conda**: For environment management.
- **Python 3.10**: Required Python version.
- **Pip**: Package manager for Python packages.

### How to Run the Setup Script

1. Clone the project repository or download the project files.
2. Open a terminal in the project directory.
3. Run the following command to create a conda environment called `gg337` with `Python 3.10`. It will also install all required packages from `environment.yml`:

   ```bash
   conda env create -f environment.yml
   ```
4. Once the process completes, activate the environment using:

   ```bash
   conda activate gg337
   ```
5. After activation, download the SpaCy language model `en_core_web_sm`:

    ```bash
    python -m spacy download en_core_web_sm
    ```
6. You are ready to start using the environment for your text processing tasks.

### Additional Information

- **SpaCy Model**: The `en_core_web_sm` model is used for English language processing. You can download other models as needed from the SpaCy documentation.
- **JupyterLab**: You can run Jupyter notebooks with the installed environment by simply running `jupyter lab` in the terminal after activating the environment.

### Troubleshooting

- If the setup script fails to create the Conda environment or install dependencies, ensure that you have the correct versions of Conda and Python installed.
- For any specific library issues, consult the respective library documentation:
    - [SpaCy Documentation](https://spacy.io/usage)
    - [NLTK Documentation](https://www.nltk.org/)
    - [JupyterLab Documentation](https://jupyter.org/)
    - [FTFY Documentation](https://ftfy.readthedocs.io/en/latest/)
    - [Unidecode Documentation](https://pypi.org/project/Unidecode/)
    - [langdetect Documentation](https://pypi.org/project/langdetect/)
    - [Inflection Documentation](https://pypi.org/project/inflection/)

### License

This project is licensed under the MIT License.



