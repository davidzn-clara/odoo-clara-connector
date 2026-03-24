/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";

export class ClaraDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            kpi: {
                totalSpend: 0.0,
                approvedCount: 0,
                pendingExpensesCount: 0,
                unpostedEntriesCount: 0,
            },
            lastSync: {
                status: 'unknown',
                timestamp: 'Never',
                color: 'bg-secondary'
            },
            chartData: []
        });

        onWillStart(async () => {
            await this.fetchData();
        });

        const fetchInterval = setInterval(() => this.fetchData(), 300000);
        onWillUnmount(() => {
            clearInterval(fetchInterval);
        });
    }

    async fetchData() {
        const today = new Date();
        const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];

        const txDomain = [['transaction_date', '>=', startOfMonth]];
        const transactions = await this.orm.searchRead('clara.transaction', txDomain, ['amount', 'status', 'expense_id', 'account_move_id', 'merchant_category']);

        let totalSpend = 0;
        let approvedCount = 0;
        let pendingExt = 0;
        let unposted = 0;
        let categories = {};

        transactions.forEach(tx => {
            const isSpend = ['approved', 'authorized'].includes(tx.status);
            if (isSpend) {
                totalSpend += tx.amount;
                approvedCount++;
                if (!tx.expense_id) pendingExt++;
                if (!tx.account_move_id) unposted++;

                let cat = tx.merchant_category || 'Other';
                categories[cat] = (categories[cat] || 0) + tx.amount;
            }
        });

        this.state.kpi.totalSpend = totalSpend;
        this.state.kpi.approvedCount = approvedCount;
        this.state.kpi.pendingExpensesCount = pendingExt;
        this.state.kpi.unpostedEntriesCount = unposted;

        let sortedCats = Object.keys(categories).map(k => ({ name: k, value: categories[k] })).sort((a, b) => b.value - a.value).slice(0, 5);
        this.state.chartData = sortedCats;

        const logs = await this.orm.searchRead('clara.sync.log', [], ['state', 'finished_at'], { limit: 1, order: 'finished_at desc' });
        if (logs.length > 0) {
            const log = logs[0];
            this.state.lastSync.status = log.state;
            this.state.lastSync.timestamp = log.finished_at || 'Never';
            if (log.state === 'success') this.state.lastSync.color = 'text-bg-success';
            else if (log.state === 'failed') this.state.lastSync.color = 'text-bg-danger';
            else this.state.lastSync.color = 'text-bg-warning';
        }
    }

    openTransactions() {
        this.action.doAction('clara_connector.action_clara_transactions');
    }

    openCards() {
        this.action.doAction('clara_connector.action_clara_cards');
    }

    async syncNow() {
        this.action.doAction('clara_connector.action_clara_sync_wizard');
    }
}

ClaraDashboard.template = "clara_connector.DashboardView";

registry.category("actions").add("clara_dashboard_client_action", ClaraDashboard);
