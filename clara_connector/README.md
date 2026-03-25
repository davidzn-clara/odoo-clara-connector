# Clara Connector for Odoo

The **Clara Odoo Connector** provides a seamless, secure, and robust integration between Odoo (v17+) and the Clara Spend Management ecosystem. It is designed to bridge the gap between corporate spend and accounting, ensuring all card data and transactions are synchronized in real-time.

---

## 🚀 Key Features

### 🔹 Unified Card Management
- **Smart Sync**: Automatically fetches all active, inactive, and virtual Clara cards.
- **Dynamic Limits**: Tracks **Periodicity** (Daily, Monthly, etc.) and individual **Thresholds** directly from the Clara API v3.
- **Employee Mapping**: Automatically links Clara cards to Odoo `hr.employee` records based on cardholder names.

### 🔹 Transaction Synchronization
- **Real-Time Data**: Syncs all corporate spend transactions, including merchant details, amounts, and currencies.
- **Automated Logging**: Tracks every sync session with detailed success/failure logs.
- **Multi-Currency Support**: Handles international transactions with automatic Odoo currency matching.

### 🔹 Enterprise-Grade Security
- **mTLS Integration**: Securely communicates with Clara using Mutual TLS without requiring certificates to be stored on the local file system.
- **Encrypted Storage**: Credentials and certificates are stored securely within the Odoo database.

---

## 🛠 Installation & Setup

### 1. Requirements
- Odoo 17.0+ (Community or Enterprise).
- Modules: `account`, `hr_expense`.

### 2. Basic Configuration
1. Navigate to **Settings** > **Accounting** > **Clara Connector**.
2. Select your **Region** (MX, CO, BR, etc.).
3. Enter your **Client ID** and **Client Secret** provided by Clara.

### 3. mTLS Certificate Setup
> [!IMPORTANT]
> To ensure a secure connection, you must upload your Clara-issued certificates in the **Certificates** tab of the configuration page.
- **CA Certificate**: Your root/intermediate certificate.
- **Client Certificate**: Your individual service certificate.
- **Client Key**: The private key associated with your certificate.

### 4. Verification
- Press the **Test Connection** button.
- A **Success** notification indicates Odoo is now communicating with Clara's Public API v3.

---

## 📁 User Guide

### Manual Synchronization
You can trigger a manual sync at any time:
1. Go to **Clara** > **Sync** > **Manual Sync**.
2. Choose your scope: **Transactions Only**, **Cards Only**, or **Full Sync**.
3. Press **Run Sync Now**.

### Automated Sync (Cron)
The module includes a scheduled action that runs automatically (default: every 4 hours). You can adjust this in Odoo's **Scheduled Actions** menu.

### Card Details View
Each card record contains:
- **Limits**: Shows the `Credit Limit` and the effective `Threshold`.
- **Status**: Visual indicators (Active, Locked, Cancelled) matching Clara's system.
- **Technical Tab**: For administrators, it includes the `Raw Payload` from the last API response for easier debugging.

---

## 🆘 Support & Maintenance

- **Issues**: Report bugs or request features via the [GitHub Issues](https://github.com/clara-com/odoo-connector/issues) page.
- **API Status**: Check the [Clara Status Page](https://status.clara.com) if you experience connection timeouts.

---
*Designed with ❤️ by the Clara Integration Team.*
