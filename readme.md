# InvManage
## An Invantory Management System

A simple inventory management system with:

 - A Flask web interface for viewing and editing stock.

 - A console UI (via rich) that auto-updates when data changes.

 - Product code auto-generation with configurable format.

## Installation

1. Clone the Repository
```bash
git clone https://github.com/JosephRedman/InvManage.git
cd InvManage
```

2. Set Up a Python Virtual Environment (optional but recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install Dependencies
```bash
pip install -r requirements.txt
```
## Optional: Run automatically on pi's boot
 
 1. Make the program an executable:
 ```bash
 chmod +x /home/pi/InvManage/InvManage.py
 ```
 > [!NOTE]
 > Replace `/home/pi/InvManage/InvManage.py` with the actual full path if it's different.

 2. Create a systemd service
 ```bash
 sudo nano /etc/systemd/system/invmanage.service
 ```
 Paste the following:
 ```ini
 [Unit]
 Description=InvManage Inventory Web App
 After=network.target

 [Service]
 ExecStart=/usr/bin/python3 /home/pi/InvManage/InvManage.py
 WorkingDirectory=/home/pi/InvManage
 StandardOutput=inherit
 StandardError=inherit
 Restart=always
 User=pi 

 [Install]
 WantedBy=multi-user.target
 ```
 > [!NOTE]
 > Make sure `ExecStart` points to the full path of your Python interpreter and script.

 3. Enable and start the service
 ```bash
 sudo systemctl daemon-reexec
 sudo systemctl daemon-reload
 sudo systemctl enable invmanage.service
 sudo systemctl start invmanage.service
 ```
 4. Check it’s running
 ```bash
 sudo systemctl status invmanage.service
 ```
You should see green text saying it's active. InvManage should now:
- Start automatically at boot

- Restart if it crashes

## Running
> [!WARNING]
> The default login credentials:
>
> ```python
> VALID_USERNAME = "admin"
> VALID_PASSWORD = "password123"
> ```
>
> are insecure and should **never** be used in production.  
> Update these values to protect your system from unauthorized access.

```bash
python InvManage.py
```
 - The web interface will be available at: http://localhost:8080

 - The console view will auto-refresh with stock changes.

## Configuration

You can set the desired format for product codes by editing the `PRODUCT_CODE_FORMAT` value in `InvManage.py`:

```python
PRODUCT_CODE_FORMAT = "EUK111111"  # Format: letters + digits, like "JOS111" or "111111"
```

## Database

The app uses a local SQLite database named `inventory.db` and creates the table automatically if it doesn't exist.

To reset the inventory, simply delete the `inventory.db` file:
```bash
rm inventory.db
```

## Copyright

© Elec UK
This software is proprietary. Redistribution, commercial or non-commercial, is not allowed, except by Joseph Redman.
