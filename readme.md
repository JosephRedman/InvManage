# InvManage
## An Invantory Management System

A simple inventory management system with:

 - A Flask web interface for viewing and editing stock.

 - A console UI (via rich) that auto-updates when data changes.

 - Product code auto-generation with configurable format.

## Installation

1. Clone the Repository
```
git clone https://github.com/JosephRedman/InvManage.git
cd InvManage
```

2. Set Up a Python Virtual Environment (optional but recommended)
```
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install Dependencies
```
pip install -r requirements.txt
```

## Running

```
python InvManage.py
```
 - The web interface will be available at: http://localhost:8080

 - The console view will auto-refresh with stock changes.

## Configuration

You can set the desired format for product codes by editing the `PRODUCT_CODE_FORMAT` value in `InvManage.py`:

```
PRODUCT_CODE_FORMAT = "EUK111111"  # Format: letters + digits, like "JOS111" or "111111"
```

## Database

The app uses a local SQLite database named `inventory.db` and creates the table automatically if it doesn't exist.

To reset the inventory, simply delete the `inventory.db` file:
```
rm inventory.db
```

## Copyright

© Elec UK
This software is proprietary. Redistribution, commercial or non-commercial, is not allowed, except by Joseph Redman.