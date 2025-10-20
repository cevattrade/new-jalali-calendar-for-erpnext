/*
 * Jalali calendar integration for ERPNext Desk.
 *
 * This script injects a Jalali-aware date picker while keeping the
 * underlying database values in Gregorian format. The conversion
 * routines are implemented in plain JavaScript and mirror the
 * server-side helpers in ``jalali_calendar.api.converter``.
 */
/* global frappe */
(function () {
  if (typeof frappe === "undefined" || !frappe.ui || !frappe.ui.form) {
    return;
  }

  frappe.provide("frappe.jalali");

  const GREGORIAN_MONTH_LENGTHS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const JALALI_MONTH_LENGTHS = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29];
  const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
  const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
  const VALID_CALENDARS = ["jalali", "gregorian"];
  const DEFAULT_CALENDAR = "jalali";
  let ORIGINAL_CONTROL_DATE = null;
  let ORIGINAL_CONTROL_DATETIME = null;
  let currentCalendar = null;

  function div(a, b) {
    return Math.floor(a / b);
  }

  function pad(number) {
    return String(number).padStart(2, "0");
  }

  function normalizeDigits(value) {
    if (!value) {
      return value;
    }
    let result = "";
    for (const char of value) {
      const persianIndex = PERSIAN_DIGITS.indexOf(char);
      if (persianIndex > -1) {
        result += String(persianIndex);
        continue;
      }
      const arabicIndex = ARABIC_DIGITS.indexOf(char);
      if (arabicIndex > -1) {
        result += String(arabicIndex);
        continue;
      }
      result += char;
    }
    return result;
  }

  function parseDateInput(value) {
    if (!value) {
      return null;
    }
    const normalized = normalizeDigits(value).replace(/\//g, "-").trim();
    const tokens = normalized.split("-").filter(Boolean);
    if (tokens.length < 3) {
      return null;
    }
    const year = parseInt(tokens[0], 10);
    const month = parseInt(tokens[1], 10);
    const day = parseInt(tokens[2], 10);
    if (Number.isNaN(year) || Number.isNaN(month) || Number.isNaN(day)) {
      return null;
    }
    return { year, month, day };
  }

  function gregorianToJalali(gy, gm, gd) {
    let gy2 = gy - 1600;
    let gm2 = gm - 1;
    const gd2 = gd - 1;

    let gDayNo = 365 * gy2 + div(gy2 + 3, 4) - div(gy2 + 99, 100) + div(gy2 + 399, 400);
    for (let i = 0; i < gm2; i += 1) {
      gDayNo += GREGORIAN_MONTH_LENGTHS[i];
    }
    if (gm2 > 1 && isGregorianLeap(gy)) {
      gDayNo += 1;
    }
    gDayNo += gd2;

    let jDayNo = gDayNo - 79;

    const jNp = div(jDayNo, 12053);
    jDayNo %= 12053;

    let jy = 979 + 33 * jNp + 4 * div(jDayNo, 1461);
    jDayNo %= 1461;

    if (jDayNo >= 366) {
      jy += div(jDayNo - 366, 365);
      jDayNo = (jDayNo - 366) % 365;
    }

    let jm = 0;
    let jd = 0;
    for (let i = 0; i < 12; i += 1) {
      const monthLength = JALALI_MONTH_LENGTHS[i];
      if (jDayNo < monthLength) {
        jm = i + 1;
        jd = jDayNo + 1;
        break;
      }
      jDayNo -= monthLength;
    }

    return [jy, jm, jd];
  }

  function jalaliToGregorian(jy, jm, jd) {
    const jy2 = jy - 979;
    const jm2 = jm - 1;
    const jd2 = jd - 1;

    let jDayNo = 365 * jy2 + div(jy2, 33) * 8 + div((jy2 % 33) + 3, 4);
    for (let i = 0; i < jm2; i += 1) {
      jDayNo += JALALI_MONTH_LENGTHS[i];
    }
    jDayNo += jd2;

    let gDayNo = jDayNo + 79;

    let gy = 1600 + 400 * div(gDayNo, 146097);
    gDayNo %= 146097;

    let leap = true;
    if (gDayNo >= 36525) {
      gDayNo -= 1;
      gy += 100 * div(gDayNo, 36524);
      gDayNo %= 36524;

      if (gDayNo >= 365) {
        gDayNo += 1;
      } else {
        leap = false;
      }
    }

    gy += 4 * div(gDayNo, 1461);
    gDayNo %= 1461;

    if (gDayNo >= 366) {
      leap = false;
      gDayNo -= 1;
      gy += div(gDayNo, 365);
      gDayNo %= 365;
    }

    let gm = 0;
    let gd = 0;
    for (let i = 0; i < 12; i += 1) {
      const monthLength = GREGORIAN_MONTH_LENGTHS[i] + (i === 1 && leap ? 1 : 0);
      if (gDayNo < monthLength) {
        gm = i + 1;
        gd = gDayNo + 1;
        break;
      }
      gDayNo -= monthLength;
    }

    return [gy, gm, gd];
  }

  function isGregorianLeap(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  }

  function formatIso(gy, gm, gd) {
    return `${gy.toString().padStart(4, "0")}-${pad(gm)}-${pad(gd)}`;
  }

  function toJalaliDisplay(value) {
    const parsed = parseDateInput(value);
    if (!parsed) {
      return value;
    }
    const [jy, jm, jd] = gregorianToJalali(parsed.year, parsed.month, parsed.day);
    return `${jy}-${pad(jm)}-${pad(jd)}`;
  }

  function fromJalaliInput(value) {
    const parsed = parseDateInput(value);
    if (!parsed) {
      return null;
    }
    // Heuristic: years >= 1700 are already Gregorian
    if (parsed.year >= 1700) {
      return formatIso(parsed.year, parsed.month, parsed.day);
    }
    const [gy, gm, gd] = jalaliToGregorian(parsed.year, parsed.month, parsed.day);
    return formatIso(gy, gm, gd);
  }

  function splitDateTime(value) {
    if (!value) {
      return { date: "", time: "" };
    }
    const trimmed = normalizeDigits(value).trim();
    const [datePart, ...rest] = trimmed.split(" ");
    return { date: datePart, time: rest.join(" ") };
  }

  function toJalaliDatetimeDisplay(value) {
    if (!value) {
      return value;
    }
    const { date: datePart, time } = splitDateTime(value);
    if (!datePart) {
      return value;
    }
    const displayDate = toJalaliDisplay(datePart);
    return time ? `${displayDate} ${time}` : displayDate;
  }

  function fromJalaliDatetime(value) {
    if (!value) {
      return value;
    }
    const { date: datePart, time } = splitDateTime(value);
    if (!datePart) {
      return value;
    }
    const isoDate = fromJalaliInput(datePart);
    if (!isoDate) {
      return value;
    }
    return time ? `${isoDate} ${time}` : isoDate;
  }

  function normalizeCalendarChoice(calendar) {
    if (!calendar) {
      throw new Error("Calendar value is required");
    }
    const normalized = String(calendar).trim().toLowerCase();
    if (!VALID_CALENDARS.includes(normalized)) {
      throw new Error(`Unsupported calendar: ${calendar}`);
    }
    return normalized;
  }

  function getCalendarContext() {
    const boot = (frappe.boot && frappe.boot.jalali_calendar) || {};
    let active;
    try {
      active = normalizeCalendarChoice(boot.active_calendar || DEFAULT_CALENDAR);
    } catch (error) {
      active = DEFAULT_CALENDAR;
    }
    const context = {
      active_calendar: active,
      source: boot.source || (boot.active_calendar ? "system" : "default"),
      is_jalali_enabled: active === "jalali",
    };
    if (boot.system_calendar && VALID_CALENDARS.includes(boot.system_calendar)) {
      context.system_calendar = boot.system_calendar;
    }
    if (boot.user_calendar && VALID_CALENDARS.includes(boot.user_calendar)) {
      context.user_calendar = boot.user_calendar;
    }
    return context;
  }

  function updateBootContext(context) {
    if (!context) {
      return;
    }
    if (!frappe.boot) {
      frappe.boot = {};
    }
    frappe.boot.jalali_calendar = context;
  }

  function invokePreferenceMethod(method, args) {
    if (frappe.xcall) {
      return frappe.xcall(method, args);
    }
    if (frappe.call) {
      return new Promise((resolve, reject) => {
        frappe.call({
          method,
          args,
          callback: (response) => {
            if (response && Object.prototype.hasOwnProperty.call(response, "message")) {
              resolve(response.message);
            } else {
              resolve(response);
            }
          },
          error: (error) => reject(error),
        });
      });
    }
    return Promise.reject(new Error("Frappe RPC helpers are not available"));
  }

  function setCalendarPreference(calendar, scope = "user") {
    const normalizedCalendar = normalizeCalendarChoice(calendar);
    const normalizedScope = scope === "system" ? "system" : "user";
    return invokePreferenceMethod("jalali_calendar.api.preferences.set_calendar_preference", {
      scope: normalizedScope,
      calendar: normalizedCalendar,
    }).then((context) => {
      updateBootContext(context);
      return applyCalendarPreference(true);
    });
  }

  function fetchCalendarPreference() {
    return invokePreferenceMethod("jalali_calendar.api.preferences.get_calendar_preference", {}).then(
      (context) => {
        updateBootContext(context);
        return applyCalendarPreference(true);
      }
    );
  }

  function getCalendarPreference() {
    const context = getCalendarContext();
    return { ...context };
  }

  frappe.jalali.normalizeDigits = normalizeDigits;
  frappe.jalali.gregorianToJalali = gregorianToJalali;
  frappe.jalali.jalaliToGregorian = jalaliToGregorian;
  frappe.jalali.fromJalaliInput = fromJalaliInput;
  frappe.jalali.toJalaliDisplay = toJalaliDisplay;
  frappe.jalali.getCalendarPreference = getCalendarPreference;
  frappe.jalali.fetchCalendarPreference = fetchCalendarPreference;
  frappe.jalali.setCalendarPreference = setCalendarPreference;

  function ensureOriginalControls() {
    if (!ORIGINAL_CONTROL_DATE && frappe.ui && frappe.ui.form) {
      ORIGINAL_CONTROL_DATE = frappe.ui.form.ControlDate || null;
    }
    if (!ORIGINAL_CONTROL_DATETIME && frappe.ui && frappe.ui.form) {
      ORIGINAL_CONTROL_DATETIME = frappe.ui.form.ControlDatetime || null;
    }
  }

  function patchControlDate() {
    ensureOriginalControls();
    const ControlDate = frappe.ui.form.ControlDate;
    if (!ControlDate || ControlDate.__jalali_patched) {
      return;
    }

    const Extended = ControlDate.extend({
      set_formatted_input(value) {
        if (!value) {
          return this._super(value);
        }
        const displayValue = toJalaliDisplay(value);
        return this._super(displayValue);
      },
      get_input_value() {
        const raw = this.$input ? this.$input.val() : "";
        if (!raw) {
          return raw;
        }
        const iso = fromJalaliInput(raw);
        return iso || raw;
      },
      parse(value) {
        if (!value) {
          return this._super(value);
        }
        const iso = fromJalaliInput(value);
        return this._super(iso || value);
      },
      refresh_input() {
        this._super();
        if (this.$input && this.value) {
          this.$input.val(toJalaliDisplay(this.value));
        }
      },
    });

    Extended.__jalali_patched = true;
    Extended.__jalali_original = ORIGINAL_CONTROL_DATE;
    frappe.ui.form.ControlDate = Extended;
  }

  function unpatchControlDate() {
    ensureOriginalControls();
    const ControlDate = frappe.ui.form.ControlDate;
    if (ControlDate && ControlDate.__jalali_patched && ORIGINAL_CONTROL_DATE) {
      frappe.ui.form.ControlDate = ORIGINAL_CONTROL_DATE;
    }
  }

  function patchControlDatetime() {
    ensureOriginalControls();
    const ControlDatetime = frappe.ui.form.ControlDatetime;
    if (!ControlDatetime || ControlDatetime.__jalali_patched) {
      return;
    }

    const Extended = ControlDatetime.extend({
      set_formatted_input(value) {
        if (!value) {
          return this._super(value);
        }
        const displayValue = toJalaliDatetimeDisplay(value);
        return this._super(displayValue);
      },
      get_input_value() {
        const raw = this.$input ? this.$input.val() : "";
        if (!raw) {
          return raw;
        }
        const iso = fromJalaliDatetime(raw);
        return iso || raw;
      },
      parse(value) {
        if (!value) {
          return this._super(value);
        }
        const iso = fromJalaliDatetime(value);
        return this._super(iso || value);
      },
      refresh_input() {
        this._super();
        if (this.$input && this.value) {
          this.$input.val(toJalaliDatetimeDisplay(this.value));
        }
      },
    });

    Extended.__jalali_patched = true;
    Extended.__jalali_original = ORIGINAL_CONTROL_DATETIME;
    frappe.ui.form.ControlDatetime = Extended;
  }

  function unpatchControlDatetime() {
    ensureOriginalControls();
    const ControlDatetime = frappe.ui.form.ControlDatetime;
    if (ControlDatetime && ControlDatetime.__jalali_patched && ORIGINAL_CONTROL_DATETIME) {
      frappe.ui.form.ControlDatetime = ORIGINAL_CONTROL_DATETIME;
    }
  }

  function applyCalendarPreference(force = false) {
    const context = getCalendarContext();
    if (!force && currentCalendar === context.active_calendar) {
      return context;
    }
    currentCalendar = context.active_calendar;
    if (context.is_jalali_enabled) {
      patchControlDate();
      patchControlDatetime();
    } else {
      unpatchControlDate();
      unpatchControlDatetime();
    }
    if (typeof document !== "undefined" && document.documentElement) {
      document.documentElement.dataset.calendar = context.active_calendar;
    }
    frappe.jalali.currentCalendar = context.active_calendar;
    frappe.jalali.isActive = context.is_jalali_enabled;
    return context;
  }

  frappe.jalali.applyCalendarPreference = applyCalendarPreference;
  frappe.jalali.DEFAULT_CALENDAR = DEFAULT_CALENDAR;
  frappe.jalali.VALID_CALENDARS = [...VALID_CALENDARS];

  if (frappe.after_ajax) {
    frappe.after_ajax(() => applyCalendarPreference());
  } else {
    $(document).ready(() => applyCalendarPreference());
  }
})();
