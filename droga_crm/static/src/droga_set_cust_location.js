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

export class cusLocController extends FormController {
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

    async cust_loc_func() {
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
                            model: 'res.partner',
                            method: 'update_current_locations',
                            args: [0, res_id, latitude, longitude],
                        });

                        alert(_t('Location updated successfully.'));

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
                    alert(_t('Could not get location. Please check your internet connection or enable GPS.'));
                    this.uiService.unblock();
                },
                options
            );
        } else {
            alert(_t('Geolocation is not supported by your browser.'));
            this.uiService.unblock();
        }
    }

    get rendererProps() {
        const props = super.rendererProps;
        return {
            ...props,
            isDisabled: this.state.isDisabled,
            fieldIsDirty: this.state.fieldIsDirty,
        };
    }
}

cusLocController.template = "droga_pharma.JsFormView";

export class cusLocRenderer extends FormRenderer {
    setup() {
        super.setup();
        onMounted(() => {});
        onWillUpdateProps(async (nextProps) => {});
    }

    get context() {
        return {
            ...super.context,
            isDisabled: this.props.isDisabled,
            fieldIsDirty: this.props.fieldIsDirty,
        };
    }
}

registry.category('views').add('js_form_view', {
    ...formView,
    Controller: cusLocController,
    Renderer: cusLocRenderer,
});