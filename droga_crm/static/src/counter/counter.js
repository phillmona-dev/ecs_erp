/** @odoo-module */

import {registry} from "@web/core/registry"
import { Component,useState } from "@odoo/owl";
import {BadgeField} from "@web/views/fields/badge/badge_field"

class counter extends BadgeField{
    setup() {
        super.setup();
        //Props is used for updating the user interface components, similar with React
        this.customState = useState({ value: this.props.value || 1 });

        //When browser is minimised, closed or inactive, the counting stops so we can't rely on setInterval, we'll use it to update the props only
        this.startTime = Date.now();
        const startsec=this.props.value;

        //This is for looping every second. Updating the customState will also update the props.value, using state
        this.intervalId = setInterval(() => {
            let currentTime = Date.now();
            let elapsedSeconds = Math.floor((currentTime - this.startTime) / 1000);
            //Stop updating if deadline already passed, great, otherwise small phones memory usage will go crazy, as most CRM phones might be. Clear interval will clear the timer.
            if (this.customState.value > 0) {
              this.customState.value = startsec - elapsedSeconds;
            } else {
              this.customState.value = 0;
              clearInterval(this.intervalId);
            }
        }, 1000);
    }

    //The template file reads the output of this function, t-esc="counterValue", so it updates every second
    get counterValue() {
        return this.secondsToDaysHoursMinutes(this.customState.value);
    }

    secondsToDaysHoursMinutes(seconds) {

      if (typeof parseInt(seconds) !== 'number') {
        seconds=parseInt(seconds);
      }

      if (seconds<=0)
      {
        return 'Deadline passed.';
      }

      const days = Math.floor(seconds / (24 * 60 * 60));
      const remainingSecondsAfterDays = seconds % (24 * 60 * 60);

      const hours = Math.floor(remainingSecondsAfterDays / (60 * 60));
      const remainingSecondsAfterHours = remainingSecondsAfterDays % (60 * 60);

      const minutes = Math.floor(remainingSecondsAfterHours / 60);
      const remainingSeconds = remainingSecondsAfterHours % 60;

      let result = "";

      if (days > 0) {
        result += days + (days>1? " Days, ":" Day,")
      }

      if (hours > 0) {
        result += hours + (hours>1? " Hours, ":" Hour,")
      }

      if (minutes > 0) {
        result += minutes + (minutes>1? " Mins, ":" Min,");
      }

      if (remainingSeconds > 0 || (days === 0 && hours === 0 && minutes === 0)){
        result += remainingSeconds + (remainingSeconds>1? " Secs, ":" Sec");
      }

      // Remove trailing comma and space, if any.
      if (result.endsWith(", ")) {
        result = result.slice(0, -2);
      }

      return result + " left";
    }
}

counter.template="custom.counter"
counter.supportedTypes=["float"]
registry.category("fields").add("counter",counter)
