import subprocess
import sys

def create_conda_env():
    # Create a new Conda environment with Python 3.10
    subprocess.run(["conda", "create", "--name", "gg337", "python=3.10", "-y"], check=True)

def activate_conda_env():
    # Activate the Conda environment
    if sys.platform == "win32":
        activate_command = "activate gg337"
    else:
        activate_command = "source activate gg337"
    subprocess.run(activate_command, shell=True, check=True)

def install_requirements():
    # Install required packages from requirements.txt
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

def download_spacy_model():
    # Download SpaCy language model
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)

if __name__ == "__main__":
    create_conda_env()
    activate_conda_env()
    install_requirements()
    download_spacy_model()
    print("Conda environment setup is complete!")
