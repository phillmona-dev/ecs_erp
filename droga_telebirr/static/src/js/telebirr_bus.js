/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export const telebirrBusService = {
    dependencies: ["bus_service", "notification", "action"],

    start(env, { bus_service, notification, action }) {

        // Start the bus service (It automatically listens to the user's partner channel)
        bus_service.start();
        bus_service.addEventListener("notification", onNotification);

        function onNotification({ detail }) {
            for (const notif of detail) {
                const { type, payload } = notif;

                if (type === "telebirr.payment.update" || type === "payment_status") {
                    const { invoice_id, invoice_name, status, message } = payload;

                    // --- EXISTING LOGIC (UNCHANGED) ---

                    const hash = browser.location.hash.substring(1);
                    const params = new URLSearchParams(hash);

                    const currentId = parseInt(params.get("id"));
                    const currentModel = params.get("model");

                    if (currentModel !== "account.move" || currentId !== invoice_id) {
                        return;
                    }

                    // --- NOTIFICATION ---

                    notification.add(
                        message || `Payment update for ${invoice_name}`,
                        {
                            title: status === "success" ? "Payment Success" : "Payment Update",
                            type: status === "success" ? "success" : "warning",
                            sticky: true,
                        }
                    );

                    // --- VIEW RELOAD (FIXED) ---

//                    if (status === "success") {
//                        setTimeout(() => {
//                            const currentController = action.currentController;
//
//                            if (currentController && currentController.component && typeof currentController.component.reload === 'function') {
//
//                                currentController.component.reload();
//
//                                console.log(`Telebirr: Successfully reloaded view data for Invoice ${invoice_name}`);
//                            } else {
//                                console.warn("Telebirr: Could not find view component reload method. Forcing page refresh.");
//                                browser.location.reload();
//                            }
//                        }, 500);
//                    }
                }
            }
        }
    },
};

registry.category("services").add("telebirrBusService", telebirrBusService);
