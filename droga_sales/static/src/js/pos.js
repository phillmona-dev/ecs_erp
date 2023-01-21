/** @odoo-module **/
import {registry} from "@web/core/registry";
import {formView} from "@web/views/form/form_view";
import {FormController} from "@web/views/form/form_controller";
import {FormRenderer} from "@web/views/form/form_renderer";
import {browser} from "@web/core/browser/browser";

const core = require("web.core");
const ajax = require("web.ajax");
const Dialog = require("web.Dialog");
const framework = require('web.framework');

const rpc = require("web.rpc");
const _t = core._t;

const headers = {
    ApiKey: "b904ea3c8a3446a0894aeec285e774b7",
};

let posUrl = "";

export class PosFormController extends FormController {
    setup() {
        super.setup();
    }

    PrintToPos() {

        console.log(this.model.root.data.pos_device_ip_address);
        if (this.model.root.data.is_invoice_printed_pos === true) {
            Dialog.alert(this, _t("The current invoice has already been printed!"));
            return;
        } else if (this.model.root.data.pos_device_ip_address === "") {
            Dialog.alert(this, _t("The POS device IP address is not set for the current user, please contact the system administrator to set it."));
            return;
        }

        //set posurl
        posUrl = "http://" + this.model.root.data.pos_device_ip_address;

        //block UI
        framework.blockUI();

        //Get Payment Type
        const payment_type = this.model.root.data.sales_type;
        const m = new Date();

        const dateString = m.getUTCFullYear() + "-" + ("0" + (m.getUTCMonth() + 1)).slice(-2) + "-" + ("0" + m.getUTCDate()).slice(-2) + " " + ("0" + m.getUTCHours()).slice(-2) + ":" + ("0" + m.getUTCMinutes()).slice(-2) + ":" + ("0" + m.getUTCSeconds()).slice(-2);

        //build json file
        const header = {
            ThirdPartyID: "Odoo",
            TenantId: "TenantId",
            TransactionID: this.model.root.data.id,
            ReferenceNumber: this.model.root.data.name,
            PaymentType: payment_type,
            PaymentReferenceNumber: this.model.root.data.name,
            BuyerName: this.model.root.data.commercial_partner_id[1],
            BuyerTaxIdNumber: this.model.root.data.tin_no,
            AddOnType: "percentage",
            AddOnValue: "0",
            DiscountType: "fixed",
            DiscountValue: "0",
            UserName: this.model.root.data.user_id[1],
            HeaderMemo: "Free Text",
            FooterMemo: "Welcome Message",
            TimeStamp: dateString,
            Remark: "",
            ApprovedBy: this.model.root.data.user_id[1],
        };

        let lineItems = [];
        header.LineItem = lineItems;

        //get invoice line items
        let line_items = this.model.root.data.invoice_line_ids.records;

        line_items.forEach((currentElement, index, array) => {

            let tax_percent = 0;
            let line_no = 0;

            let lineItem = {
                LineIndex: line_no++,
                ItemTransactionId: currentElement.data.id,
                ItemID: currentElement.data.item_code,
                ItemShortName: currentElement.data.product_id[1],
                ItemDescription: currentElement.data.product_id[1],
                UnitName: currentElement.data.product_uom_id[1],
                Quantity: currentElement.data.quantity,
                UnitPrice: currentElement.data.price_unit,
                TaxRate: tax_percent,
                AddOnType: "percentage",
                AddOnValue: "0",
                DiscountType: "fixed",
                DiscountValue: "0",
            };

            header.LineItem.push(lineItem);
        });

        let invoice = JSON.stringify(header);


        $.ajax({
            url: posUrl + "/pedsfpsrv/api/SalesInvoice/PrintInvoice?printCopy=false",
            method: "POST",
            dataType: "json",
            crossDomain: true,
            headers: {
                'Access-Control-Allow-Origin': '*', ApiKey: "b904ea3c8a3446a0894aeec285e774b7",
            },
            data: invoice,
            contentType: "application/json",

            timeout: 5000,
        })
            .then((data) => {
                //unblock UI
                framework.unblockUI();
                //check print status
                if (data.Success === "True" && data.Status === "Finished") {
                    //update data on odoo

                    let ts = new Date(data.Content.TimeStamp);
                    let timeStamp = ts.getUTCFullYear() + "-" + ("0" + (ts.getUTCMonth() + 1)).slice(-2) + "-" + ("0" + ts.getUTCDate()).slice(-2) + " " + ("0" + ts.getUTCHours()).slice(-2) + ":" + ("0" + ts.getUTCMinutes()).slice(-2) + ":" + ("0" + ts.getUTCSeconds()).slice(-2);

                    rpc
                        .query({
                            model: "account.move", method: "write", args: [[this.model.root.data.id], {
                                FPMachineID: data.Content.FPMachineID,
                                FSInvoiceNumber: data.Content.FSInvoiceNumber,
                                EJNumber: data.Content.EJNumber,
                                FTimeStamp: timeStamp,
                                is_invoice_printed_pos: "true",
                            },],
                        })
                        .then(function (data) {
                            Dialog.alert(this, _t("Invoice has been successfully printed!"));
                            browser.location.reload();
                        }, function (data) {
                            Dialog.alert(this, _t("Invoice has not been successfully printed!"));
                        });
                } else {
                    Dialog.alert(this, _t(data.ShortMessage));
                }
            })
            .catch((error) => {
                //unblock UI
                framework.unblockUI();
                Dialog.alert(this, _t("The connection to the POS service is not established, please check the connection. "));
            });
    }

    //cancel command when the pos machine stack due to different  reasons
    CancelPosTransaction() {
        //block UI
        if (this.model.root.data.pos_device_ip_address === "") {
            Dialog.alert(this, _t("The POS device IP address is not set for the current user, please contact the system administrator to set it."));
            return;
        }
        //set posurl
        posUrl = "http://" + this.model.root.data.pos_device_ip_address;

        framework.blockUI();
        $.ajax({
            url: posUrl + "/pedsfpsrv/api/SalesInvoice/CancelFSTransaction?fpMachineId=''",
            method: "GET",
            data: "",
            contentType: "application/json",
            headers: headers,
            timeout: 5000,
        }).then((data) => {
            //unblock UI
            framework.unblockUI();
            Dialog.alert(this, _t(data));
        })
            .catch((error) => {
                //unblock UI
                framework.unblockUI();
                Dialog.alert(this, _t("The connection to the POS service is not established, please check the connection. "));
            });
    }


}

PosFormController.template = "droga_sales.PosFormView";

export class PosFormRenderer extends FormRenderer {
    setup() {
        super.setup();
    }
}

registry.category("views").add("pos_form_view", {
    ...formView, Controller: PosFormController, Renderer: PosFormRenderer,
});
