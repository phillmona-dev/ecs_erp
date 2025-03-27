/** @odoo-module **/
import { registry } from '@web/core/registry';
import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';
import { FormRenderer } from '@web/views/form/form_renderer';
import { useService } from "@web/core/utils/hooks";

const { onMounted, onWillUpdateProps, useState } = owl;
const core = require('web.core');
const _t = core._t;
const rpc = require('web.rpc');

export class CheckinController extends FormController {
    setup() {
        super.setup();
        this.uiService = useService("ui");
        this.state = useState({
            isDisabled: false,
            fieldIsDirty: false,
        });
    }


    async willStart() {
        await super.willStart();
        this.state.isDisabled = this.model.root.data.is_disabled || false;
        this.state.fieldIsDirty = this.model.root.data.field_is_dirty || false;
    }

    async handleLocationUpdate(method) {
        this.uiService.block();

        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
        };

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;
                    const res_id = this.model.root.data.id;

                    try {
                        await rpc.query({
                            model: 'crm.lead',
                            method: method,
                            args: [0, res_id, latitude, longitude],
                        });
                        alert(_t(`${method === 'update_check_in_locations' ? 'Check-in' : 'Check-out'} successful.`));
                    } catch (rpcError) {
                        console.error("RPC Error:", rpcError);
                        alert(_t('Failed to update location. Please try again.'));
                    } finally {
                        this.uiService.unblock();
                        window.location.reload();
                    }
                },
                (error) => {
                    console.error("Geolocation Error:", error);
                    alert(_t('Could not get location. Please enable GPS.'));
                    this.uiService.unblock();
                },
                options
            );
        } else {
            alert(_t('Geolocation is not supported by your browser.'));
            this.uiService.unblock();
        }
    }

    checkIn() {
        this.handleLocationUpdate('update_check_in_locations');
    }

    checkOut() {
        this.handleLocationUpdate('update_check_out_locations');
    }
}

CheckinController.template = "check_in.JsFormView";

export class CheckinRenderer extends FormRenderer {
    setup() {
        super.setup();
        onMounted(() => {});
        onWillUpdateProps(async (nextProps) => {});
    }

    get context() {
        return {
            ...super.context,
            isDisabled: this.props.isDisabled,
            fieldIsDirty: this.state.fieldIsDirty,
        };
    }
}

registry.category('views').add('check_in_form_view', {
    ...formView,
    Controller: CheckinController,
    Renderer: CheckinRenderer,
});