/** @odoo-module **/
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { browser } from "@web/core/browser/browser";

const {
  Component,
  EventBus,
  onMounted,
  onWillStart,
  onWillUnmount,
  useState,
  onWillUpdateProps,
} = owl;

const core = require("web.core");
const ajax = require("web.ajax");
const Dialog = require("web.Dialog");

var rpc = require("web.rpc");
var _t = core._t;

var headers = { ApiKey: "b904ea3c8a3446a0894aeec285e774b7" };

export class CustomFormController extends FormController {
  setup() {
    super.setup();
  }

  OnClickPrint() {
    //get data from the from
    var report = this.model.root.data.report;
    var date_from = this.model.root.data.date_from;
    var date_to = this.model.root.data.date_to;
    var z_no_start = this.model.root.data.z_no_start;
    var z_no_end = this.model.root.data.z_no_end;

    if (report == "printzdailysales") {
      this.printzdailysales();
    } else if (report == "printdailyclosing") {
      this.printdailyclosing();
    } else if (report == "printclerkreport") {
      this.printclerkreport();
    } else if (report == "printxdailysales") {
      this.printxdailysales();
    } else if (report == "printzaccumulatedreport") {
      this.printzaccumulatedreport();
    } else if (report == "printxaccumulatedreport") {
      this.printxaccumulatedreport();
    } else if (report == "printfullfiscalreportbyz") {
      this.printfullfiscalreportbyz();
    } else if (report == "printfullfiscalreportbydate") {
      this.printfullfiscalreportbydate();
    } else if (report == "printsummaryfiscalreportbyz") {
      this.printsummaryfiscalreportbyz();
    } else if (report == "printsummaryfiscalreportbydate") {
      this.printsummaryfiscalreportbydate();
    }
  }

  //Prints a fiscal daily sales report (Z-Report).
  printzdailysales() {
    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: "",
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints a fiscal daily closing report and clears the fiscal printer memory.
  printdailyclosing() {
    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: "",
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints a fiscal clerk report.
  printclerkreport() {
    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: "",
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints non fiscal x-daily sales report.
  printxdailysales() {
    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: "",
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints accumulated Z-Report.
  printzaccumulatedreport() {
    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: "",
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints accumulated X-Report.
  printxaccumulatedreport() {
    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: "",
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints a full fiscal report for the specified Z range.
  printfullfiscalreportbyz() {
    var parameter = {
      fromZ: this.model.root.data.z_no_start,
      toZ: this.model.root.data.z_no_end,
    };

    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: JSON.stringify(parameter),
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints a full fiscal report for the specified date range.
  printfullfiscalreportbydate() {
    var parameter = {
      dateFrom: this.model.root.data.date_from,
      dateTo: this.model.root.data.date_to,
    };

    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: JSON.stringify(parameter),
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints a summary of fiscal report for the specified Z range.
  printsummaryfiscalreportbyz() {
    var parameter = {
      fromZ: this.model.root.data.z_no_start,
      toZ: this.model.root.data.z_no_end,
    };

    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: JSON.stringify(parameter),
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }

  //Prints a summary of fiscal report for the specified date range.
  printsummaryfiscalreportbydate() {
    var parameter = {
      dateFrom: this.model.root.data.date_from,
      dateTo: this.model.root.data.date_to,
    };

    $.ajax({
      url: "https://reqres.in/api/users",
      method: "GET",
      data: JSON.stringify(parameter),
      contentType: "application/json",
      headers: headers,
      timeout: 5000,
    })
      .then((data) => {
        console.log(data);
        Dialog.alert(this, _t(data.PrintMessage));
      })
      .catch((error) => {});
  }
}

CustomFormController.template = "droga_sales.PosReportFormView";

export class CustomFormRenderer extends FormRenderer {
  setup() {
    super.setup();
  }
}

registry.category("views").add("pos_report_form_view", {
  ...formView,
  Controller: CustomFormController,
  Renderer: CustomFormRenderer,
});
