# simply-eda-app Setup Guide

This project uses Poetry and Conda for Python environment and dependency management. Follow these steps to set up and run the app:

## 1. Clone the repository
```sh
cd simply-eda-app
```

## 2. Install Poetry and all dependencies
```sh
make install
```
This will:
- Install Poetry
- Lock and install dependencies
- Set the Python version for Poetry

## 3. Activate the Poetry environment
```sh
make activate
```
Copy and run the command printed to activate the Poetry virtual environment.

## 4. Run the application
```sh
make run
```
This will run `app.py` using the Poetry environment.


---

**Notes:**
- If you encounter SSL errors during Poetry or Conda installation, the Makefile disables SSL verification for those steps.
- Always activate the correct environment before running the app.
- For troubleshooting, check the Makefile for all available commands.
