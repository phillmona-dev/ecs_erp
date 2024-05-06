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
var session = require('web.session');


const rpc = require("web.rpc");
const _t = core._t;

const headers = {
    ApiKey: "9a2a2f2680f04b43873f02ad7716afdb",
};

let posUrl = "";

//$('#btnPosPrint').hide();

export class PosFormController extends FormController {
    setup() {


        super.setup();


    }

    PrintToPos() {

        //get sales order id
         var invoice_origin=this.model.root.data.invoice_origin;

        console.log(this.model.root.data);
        if (this.model.root.data.pos_device_ip_address === "") {
            Dialog.alert(this, _t("The POS device IP address is not set for the current user, please contact the system administrator to set it."));
            return;
        } else if (this.model.root.data.is_invoice_printed_pos === true) {
            Dialog.alert(this, _t("The current invoice has already been printed!"));
            return;
        } else if (this.model.root.data.state !== "posted") {
            Dialog.alert(this, _t("Please confirm the invoice before you send it to the POS printer."));
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

        let tin_no = this.model.root.data.tin_no;
        let customer_name = this.model.root.data.commercial_partner_id[1];


        if (this.model.root.data.tin_no === "0000000000") {
            tin_no = "";
        }

        if (this.model.root.data.customer_name1 !== "") {
            customer_name = this.model.root.data.customer_name1;
        }


        //build json file
        const header = {
            ThirdPartyID: "Odoo",
            TenantId: "TenantId",
            TransactionID: this.model.root.data.id,
            ReferenceNumber: this.model.root.data.name,
            PaymentType: payment_type,
            PaymentReferenceNumber: this.model.root.data.name,
            BuyerName: customer_name,
            BuyerTaxIdNumber: tin_no,
            AddOnType: "percentage",
            AddOnValue: "0",
            DiscountType: "fixed",
            DiscountValue: "0",
            UserName: this.model.root.data.current_user_id[1],
            HeaderMemo: "Free Text",
            FooterMemo: "Welcome Message",
            TimeStamp: dateString,
            Remark: "",
            ApprovedBy: this.model.root.data.current_user_id[1],
        };

        let lineItems = [];
        header.LineItem = lineItems;

        //get invoice line items
        let line_items = this.model.root.data.invoice_line_ids.records;

        line_items.forEach((currentElement, index, array) => {

            let tax_percent = 0;
            let line_no = 0;


            let tax_ids=currentElement.data.tax_ids.records;

            console.log(tax_ids);


            tax_ids.forEach((taxItem)=>{
                tax_percent=15.00;
                }
            )



            if (currentElement.data.price_unit !== 0) {

                let lineItem = {
                    LineIndex: line_no++,
                    ItemTransactionId: currentElement.data.id,
                    ItemID: currentElement.data.item_code, //ItemShortName: currentElement.data.product_id[1],
                    ItemShortName: currentElement.data.name.trim(),
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
            }


        });

        let invoice = JSON.stringify(header);
        console.log(invoice);

        $.ajax({
            url: posUrl + "/pedsfpsrv/api/SalesInvoice/PrintInvoice?printCopy=false",
            method: "POST",
            dataType: "json",
            crossDomain: true,
            headers: headers,
            data: invoice,
            contentType: "application/json",
            timeout: 60000,
        })
            .then((data) => {
                console.log(data);
                //unblock UI
                framework.unblockUI();
                //check print status
                if (data.Success === "True" && data.Status === "Finished") {
                    //update data on odoo

                    let ts = new Date();
                    let timeStamp = ts.getUTCFullYear() + "-" + ("0" + (ts.getUTCMonth() + 1)).slice(-2) + "-" + ("0" + ts.getUTCDate()).slice(-2) + " " + ("0" + ts.getUTCHours()).slice(-2) + ":" + ("0" + ts.getUTCMinutes()).slice(-2) + ":" + ("0" + ts.getUTCSeconds()).slice(-2);

                    rpc
                        .query({
                            model: "account.move", method: "write", args: [[this.model.root.data.id], {
                                FPMachineID: data.Content.FPMachineID,
                                FSInvoiceNumber: data.Content.FSInvoiceNumber,
                                EJNumber: data.Content.EJNumber,
                                FTimeStamp: timeStamp,
                                is_invoice_printed_pos: "true",
                            }],
                        }, {timeout: 60000})
                        .then(function (data) {


                                //update sales order status
                                var domain = [['name', '=', invoice_origin]];

                                rpc.query({
                                    model: 'sale.order',
                                    method: 'search',
                                    args: [domain],
                                }, {timeout: 60000})
                                .then(function (data){
                                    var sales_order_id=data[0];

                                                   rpc.query({
                                                        model: 'sale.order',
                                                        method: 'write',
                                                        args: [[sales_order_id],{
                                                            invoice_printed:"Yes"
                                                        }],
                                                       }, {timeout: 60000})
                                                    .then(function (data){

                                                    });
                                });

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
                console.log(error);
                framework.unblockUI();
                Dialog.alert(this, _t("Error"));
            });
    }

    PrintToPosMaraki(){


        //Get Payment Type
        const payment_type1 = this.model.root.data.sales_type;
        const m = new Date();

        const dateString = m.getUTCFullYear() + "-" + ("0" + (m.getUTCMonth() + 1)).slice(-2) + "-" + ("0" + m.getUTCDate()).slice(-2) + " " + ("0" + m.getUTCHours()).slice(-2) + ":" + ("0" + m.getUTCMinutes()).slice(-2) + ":" + ("0" + m.getUTCSeconds()).slice(-2);

        let tin_no = this.model.root.data.tin_no;
        let customer_name1 = this.model.root.data.commercial_partner_id[1];
        let customer_code1= this.model.root.data.commercial_partner_id[0];

        if (this.model.root.data.tin_no === "0000000000") {
            tin_no = "";
        }

        if (this.model.root.data.customer_name1 !== "") {
            customer_name1 = this.model.root.data.customer_name1;
        }


        var doc = document.implementation.createDocument("", "", null);

        var invoice = doc.createElement("Invoice");

        var plant_code=doc.createElement("Plant_Code");
        var plant_name=doc.createElement("Plant_Name");
        var invoice_type=doc.createElement("Invoice_Type");
        var reference_no=doc.createElement("Reference_Number");
        var invoice_Date=doc.createElement("Invoice_Date");
        var customer_code=doc.createElement("Customer_Code");
        var customer_name=doc.createElement("Customer_Name");
        var customer_tin=doc.createElement("Customer_TIN");
        var payment_type=doc.createElement("Payment_Type");
        var invoice_disc=doc.createElement("Invoice_DiscOrAdd_Amount");

        plant_code.textContent  ="1";
        plant_name.textContent  ="Ema Head Office";
        invoice_type.textContent  ="Invoice";
        reference_no.textContent  =this.model.root.data.name;
        invoice_Date.textContent  =dateString;
        customer_code.textContent  =customer_code1;
        customer_name.textContent  =customer_name1;
        customer_tin.textContent  =tin_no;
        payment_type.textContent  =payment_type1;
        invoice_disc.textContent  ="0";

        invoice.appendChild(plant_code);
        invoice.appendChild(plant_name);
        invoice.appendChild(invoice_type);
        invoice.appendChild(reference_no);
        invoice.appendChild(invoice_Date);
        invoice.appendChild(customer_code);
        invoice.appendChild(customer_name);
        invoice.appendChild(customer_tin);
        invoice.appendChild(payment_type);
        invoice.appendChild(invoice_disc);


        //get invoice line items
        let line_items = this.model.root.data.invoice_line_ids.records;

        line_items.forEach((currentElement, index, array) => {

            let tax_percent = 0;
            let line_no = 0;

            let tax_ids=currentElement.data.tax_ids.records;

            tax_ids.forEach((currentElement1, index1, array1) =>
            {
                         //console.log(currentElement1.data);

                         // Use an empty array to search for all the records
                 var domain =[ ];

                  var args = [domain];

                         rpc.query({
                model: 'account.tax',
                method: 'search_read',
                args: args,
                    }).then(function (data) {
                        console.log(data);
                    });

                         //get tax id
             })





            if (currentElement.data.price_unit !== 0) {
                //
                var line_items = doc.createElement("Line_Items");
                var item_id=doc.createElement("Item_ID");
                var item_description=doc.createElement("Item_Description");
                var item_quantity=doc.createElement("Item_Quantity");
                var item_uom=doc.createElement("Item_UOM");
                var item_unit_price=doc.createElement("Item_Unit_Price");
                var item_tax_percent=doc.createElement("Item_Tax_Percent");
                var invoice_disc1=doc.createElement("Invoice_DiscOrAdd_Amount");

                item_id.textContent=currentElement.data.item_code;
                item_description.textContent=currentElement.data.product_id[1];
                item_quantity.textContent=currentElement.data.quantity;
                item_uom.textContent=currentElement.data.product_uom_id[1];
                item_unit_price.textContent=currentElement.data.price_unit;
                item_tax_percent.textContent=tax_percent;
                invoice_disc1.textContent="0";

                line_items.appendChild(item_id);
                line_items.appendChild(item_description);
                line_items.appendChild(item_quantity);
                line_items.appendChild(item_uom);
                line_items.appendChild(item_unit_price);
                line_items.appendChild(item_tax_percent);
                line_items.appendChild(invoice_disc1);



                invoice.appendChild(line_items);


            }


        });



        doc.appendChild(invoice);

        console.log(doc);

        console.log((new XMLSerializer()).serializeToString(doc));

       if (window.XMLHttpRequest) {
           xhttp = new XMLHttpRequest();
       }
       else // code for IE5 and IE6
       {
           xhttp = new ActiveXObject("Microsoft.XMLHTTP");
       }

       xhttp.open("GET", "books.xml",false);
       xhttp.setRequestHeader("Accept", "text/xml");
       xhttp.send();
       xmlDoc = xhttp.responseXML;
       x = xmlDoc.getElementsByTagName("title")[0].childNodes[0];

       x.nodeValue = "Easy Cooking";
       xmlDoc.Save("books.xml");





    }

    btnUpdateFs() {
            if (this.model.root.data.pos_device_ip_address === "") {
                Dialog.alert(this, _t("The POS device IP address is not set for the current user, please contact the system administrator to set it."));
                return;
            }
            //set posurl
            posUrl = "http://" + this.model.root.data.pos_device_ip_address;

            //block UI
            framework.blockUI();

            const header = {
                ThirdPartyID: "Odoo",
                TenantId: "TenantId",
                TransactionID: this.model.root.data.id,
            };

            let invoice = JSON.stringify(header);
            console.log(posUrl + "/pedsfpsrv/api/SalesInvoice/GetInvoicePrintStatus")
            console.log(invoice)
            $.ajax({
                url: posUrl + "/pedsfpsrv/api/SalesInvoice/GetInvoicePrintStatus",
                method: "POST",
                dataType: "JSON",
                crossDomain: true,
                headers: headers,
                data: invoice,
                contentType: "application/json",
                timeout: 60000,
            }).then((data) => {

                framework.unblockUI();
                console.log('Receive part')
                console.log(data)
                //check print status
                if (data.Success === "True" && data.Status === "Finished") {
                    //update data on odoo

                    rpc.query({
                        model: "account.move",
                        method: "update_fs_info",
                        args: [this.model.root.data.id, data.Content.FPMachineID, data.Content.FSInvoiceNumber, data.Content.EJNumber,data.Content.TimeStamp],
                    }, { timeout: 60000 });

                    browser.location.reload();
                }
                else {
                    Dialog.alert(this, _t(data.ShortMessage));
                }
            })
                .catch((error) => {
                    //unblock UI
                    console.log(error);
                    framework.unblockUI();
                    Dialog.alert(this, _t("Error"));
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
