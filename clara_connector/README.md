# Clara Connector for Odoo

> [!WARNING]
> **THIS IS A TEMPLATE PROJECT**. 
> This repository is intended to be **FORKED** and customized for your specific Odoo environment. **Do not use this repository directly** in production without first forking it to your own organization or account to maintain control over your own configuration, certificates, and updates.

The **Clara Odoo Connector** provides a seamless, secure, and robust integration between Odoo (v17+) and the Clara Spend Management ecosystem. It is designed to bridge the gap between corporate spend and accounting, ensuring all card data and transactions are synchronized in real-time.

---

## 🚀 Key Features

### 🔹 Unified Card Management
- **Smart Sync**: Automatically fetches all active, inactive, and virtual Clara cards.
- **Dynamic Limits**: Tracks **Periodicity** (Daily, Monthly, etc.) and individual **Thresholds** directly from the Clara API v3.
- **Employee Mapping**: Automatically links Clara cards to Odoo `hr.employee` records based on cardholder names.

### 🔹 Fiscal Invoice Recovery (Mexico)
- **SAT Synchronization**: Recovers official fiscal documents (CFDI) directly from Clara's integration with the SAT.
- **Automatic Linking**: Automatically associates recovered XML/PDF metadata with the corresponding Clara transactions in Odoo.
- **Fiscal Metadata**: Captures SAT UUID, Issuer RFC, and total amounts for easier reconciliation.

### 🔹 Transaction Synchronization
- **Real-Time Data**: Syncs all corporate spend transactions, including merchant details, amounts, and currencies.
- **Automated Logging**: Tracks every sync session with detailed success/failure logs.
- **Multi-Currency Support**: Handles international transactions with automatic Odoo currency matching.

### 🔹 Enterprise-Grade Security
- **mTLS Integration**: Securely communicates with Clara using Mutual TLS without requiring certificates to be stored on the local file system.
- **Encrypted Storage**: Credentials and certificates are stored securely within the Odoo database.

---

## 🛠 Installation & Setup

### 1. Module Deployment (Forked Workflow)
1. **Fork the repository**: Click the **Fork** button on the top right of this GitHub repository to create your own private or organization-level copy.
2. **Clone your fork**: Clone **your forked version** into your Odoo `addons` directory:
   ```bash
   git clone https://github.com/YOUR_ORG/odoo-connector.git
   ```
3. **Update Addons Path**: Ensure the directory is included in your `odoo.conf` file:
   ```ini
   addons_path = /path/to/odoo/addons,/path/to/clara-connector
   ```
4. **Restart Odoo**: Restart your Odoo server to detect the new module.
5. **Enable Developer Mode**: In Odoo, go to **Settings** and click **Activate the developer mode**.
6. **Update Apps List**: Navigate to the **Apps** menu and click **Update Apps List** in the top bar.
7. **Install**: Search for "Clara" and click **Install**.

### 2. Requirements
- Odoo 17.0+ (Community or Enterprise).
- Modules: `account`, `hr_expense`.

### 3. Basic Configuration
1. Navigate to **Settings** > **Accounting** > **Clara Connector**.
2. Select your **Region** (MX, CO, BR, etc.).
3. Enter your **Client ID** and **Client Secret** provided by Clara.

### 4. mTLS Certificate Setup
> [!IMPORTANT]
> To ensure a secure connection, you must upload your Clara-issued certificates in the **Certificates** tab of the configuration page.
- **CA Certificate**: Your root/intermediate certificate.
- **Client Certificate**: Your individual service certificate.
- **Client Key**: The private key associated with your certificate.

### 5. Verification
- Press the **Test Connection** button.
- A **Success** notification indicates Odoo is now communicating with Clara's Public API v3.

---

## 📁 User Guide

### Manual Synchronization
You can trigger a manual sync at any time:
1. Go to **Clara** > **Sync** > **Manual Sync**.
2. Choose your scope: **Transactions Only**, **Cards Only**, **Recovered Invoices Only**, or **Full Sync**.
3. Press **Run Sync Now**.

### Automated Sync (Cron)
The module includes a scheduled action that runs automatically (default: every 4 hours). You can adjust this in Odoo's **Scheduled Actions** menu.

### Invoice Management
Browse your recovered fiscal documents by navigating to **Clara** > **Invoices**. 
- Each record displays the official **SAT UUID** and **Issuer RFC**.
- Linked transactions can be accessed directly from the invoice form view.

### Card Details View
Each card record contains:
- **Limits**: Shows the `Credit Limit` and the effective `Threshold`.
- **Status**: Visual indicators (Active, Locked, Cancelled) matching Clara's system.
- **Technical Tab**: For administrators, it includes the `Raw Payload` from the last API response.

---

## 🆘 Support & Maintenance

- **Issues**: Report bugs or request features via the [GitHub Issues](https://github.com/clara-com/odoo-connector/issues) page.
- **API Status**: Check the [Clara Status Page](https://status.clara.com) if you experience connection timeouts.

---
*Designed with ❤️ by the Clara Integration Team.*
