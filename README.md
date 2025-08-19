# simply-eda-app Setup Guide

This project uses Poetry and Conda for Python environment and dependency management. Follow these steps to set up and run the app:

## 1. Clone the repository
```sh
cd simply-eda-app
```

## 2. (Optional) Create and activate a Conda environment
```sh
make conda-create
make conda-activate
# Or manually:
conda activate $(CURDIR)/.simply-eda-app-env
```

## 3. Install Poetry and all dependencies
```sh
make install
```
This will:
- Install Poetry
- Add the Poetry export plugin
- Lock and install dependencies
- Set the Python version for Poetry

## 4. Activate the Poetry environment
```sh
make activate
```
Copy and run the command printed to activate the Poetry virtual environment.

## 5. Run the application
```sh
make run
```
This will run `app.py` using the Poetry environment.

## 6. Export requirements (for pip or deployment)
```sh
make requirements
```
This will generate `requirements.txt` from Poetry dependencies.

---

**Notes:**
- If you encounter SSL errors during Poetry or Conda installation, the Makefile disables SSL verification for those steps.
- Always activate the correct environment before running the app.
- For troubleshooting, check the Makefile for all available commands.
