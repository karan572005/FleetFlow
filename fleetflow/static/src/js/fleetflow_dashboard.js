/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

class FleetFlowDashboard extends Component {
    static template = "fleetflow.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            activeFleet: 0,
            maintenanceAlert: 0,
            utilizationRate: 0,
            pendingCargo: 0,
            totalVehicles: 0,
            recentTrips: [],
            loading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        // Active Fleet (On Trip)
        const onTrip = await this.orm.searchCount("fleetflow.vehicle", [
            ["state", "=", "on_trip"],
        ]);
        // In Shop
        const inShop = await this.orm.searchCount("fleetflow.vehicle", [
            ["state", "=", "in_shop"],
        ]);
        // Total vehicles
        const total = await this.orm.searchCount("fleetflow.vehicle", [
            ["state", "!=", "retired"],
        ]);
        // Pending Cargo (draft trips)
        const pending = await this.orm.searchCount("fleetflow.trip", [
            ["state", "=", "draft"],
        ]);

        // Recent trips
        const trips = await this.orm.searchRead(
            "fleetflow.trip",
            [["state", "in", ["draft", "dispatched", "completed"]]],
            ["name", "vehicle_id", "driver_id", "origin", "destination",
             "cargo_weight", "state", "date_planned"],
            { limit: 8, order: "date_planned desc" }
        );

        this.state.activeFleet = onTrip;
        this.state.maintenanceAlert = inShop;
        this.state.totalVehicles = total;
        this.state.pendingCargo = pending;
        this.state.utilizationRate = total > 0
            ? Math.round((onTrip / total) * 100)
            : 0;
        this.state.recentTrips = trips;
        this.state.loading = false;
    }

    // ── NAVIGATION ──────────────────────────────────────────────
    openNewTrip() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fleetflow.trip",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNewVehicle() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fleetflow.vehicle",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openVehicleList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Vehicle Registry",
            res_model: "fleetflow.vehicle",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openTripList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Trips",
            res_model: "fleetflow.trip",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openMaintenance() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Maintenance Logs",
            res_model: "fleetflow.maintenance",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openTrip(tripId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fleetflow.trip",
            res_id: tripId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    getStateClass(state) {
        const map = {
            draft:      "ff-pill-draft",
            dispatched: "ff-pill-dispatched",
            completed:  "ff-pill-completed",
            cancelled:  "ff-pill-cancelled",
        };
        return map[state] || "ff-pill-draft";
    }

    getStateLabel(state) {
        const map = {
            draft:      "Draft",
            dispatched: "On Trip",
            completed:  "Completed",
            cancelled:  "Cancelled",
        };
        return map[state] || state;
    }
}

registry.category("actions").add("fleetflow_dashboard", FleetFlowDashboard);
