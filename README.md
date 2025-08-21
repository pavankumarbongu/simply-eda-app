# simply-eda-app Setup Guide

This project uses Poetry and Conda for Python environment and dependency management. Follow these steps to set up and run the app:

## 1. Clone the repository
```sh
cd simply-eda-app
```

## 2. Create env
```sh
conda create -p /home/oneai/env-eda-app python=3.9 --yes
```

## 3. Activate env
```sh
conda activate /home/oneai/env-eda-app
```

## 4. Install Poetry and Dependencies
```sh
make install
```

## 4. Run the application
```sh
make run
```
This will run `app.py` using the Poetry environment.

