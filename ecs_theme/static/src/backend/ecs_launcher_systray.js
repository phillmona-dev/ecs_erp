/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";


class EcsLauncherSystray extends Component {
    static template = xml`
        <a href="/ecs/home"
           class="ecs-back-launcher-btn"
           title="Open ECS Company Home"
           role="menuitem">
            <span class="ecs-back-launcher-icon">E</span>
            <span class="ecs-back-launcher-label">ECS Home</span>
        </a>
    `;
    static props = {};
}

registry.category("systray").add(
    "ecs_theme.launcher_systray",
    { Component: EcsLauncherSystray },
    { sequence: 2 }
);
