import _isEqual from "lodash/isEqual";
import _orderBy from "lodash/orderBy";
import * as api from "./api";

/**
 * A helper method to try to parse errors into human-readable strings.
 * This also parses anything that is not an Error, since JavaScript allows throwing anything, not just errors.
 *
 * @param {any} error Any error.
 * @returns {string} A string representing the error in a way as human-readable as possible.
 */
export const errorParser = (error) => {
  if (typeof error === "string") return error;

  /*
   * There are two types of strings in JS!
   * We can't call null.toString() or undefined.toString(), but we can call String(null).toString()…
   */
  if (!error) return String(error).toString();

  let message = null;
  if (error.response && error.response.data) {
    if (
      typeof error.response.data === "string" ||
      error.response.data instanceof String ||
      Array.isArray(error.response.data)
    )
      message = error.response.data;
    else if (error.response.data.detail) message = error.response.data.detail;
    else if (error.response.data.message) message = error.response.data.message;
  }

  if (!message && error.message) message = error.message;
  if (!message) return error.toString();

  if (Array.isArray(message)) return message.join(" - ");
  if (typeof message === "string") return message;
  return message.toString();
};

export const E_SERVER_ERROR = "Error while communicating with the server.";

export const formatSizeFriendly = (sz) => {
  if (sz >= 1024 * 1024 * 1024)
    return Math.round(sz / 1024 / 1024 / 1024) + "G";
  if (sz >= 1024 * 1024) return Math.round(sz / 1024 / 1024) + "M";
  if (sz >= 1024) return Math.round(sz / 1024) + "K";
  return sz + "";
};

export const formatClientTimestamp = (datetime) => {
  const date = new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(new Date(datetime));
  return Object.values(date)
    .map(({ value }) => (value === ", " ? " " : value))
    .join("");
};

export const assignExternalBug = (bucketId, bugId, providerId) => {
  const payload = {
    bug: bugId,
    bug_provider: providerId,
  };

  try {
    return Promise.resolve(
      api.updateBucket({
        id: bucketId,
        params: { reassign: false },
        ...payload,
      }),
    );
  } catch (err) {
    return Promise.reject(err);
  }
};

export const formatDateRelative = (datetime, relative_to, suffix) => {
  relative_to = relative_to !== undefined ? new Date(relative_to) : new Date();
  suffix = suffix !== undefined ? suffix : "ago";
  const delta =
    Math.abs(relative_to.getTime() - new Date(datetime).getTime()) / 1000;
  const days = Math.floor(delta / 86400);
  const hours = Math.floor((delta % 86400) / 3600);
  const minutes = Math.floor((delta % 3600) / 60);
  let ret = "";
  if (days > 1) {
    ret += `${days} days `;
  } else if (days > 0) {
    ret += `${days} day `;
  }
  if (hours > 1) {
    ret += `${hours} hours `;
  } else if (hours > 0) {
    ret += `${hours} hour `;
  }
  if (minutes > 1) {
    ret += `${minutes} minutes `;
  } else if (minutes > 0) {
    ret += `${minutes} minute `;
  }
  if (ret.length === 0) {
    ret = "less than a minute ";
  }
  return ret + suffix;
};

export const parseHash = (hash) => {
  return hash
    .substring(1)
    .split("&")
    .map((v) => v.split("="))
    .reduce(
      (pre, [key, value]) => ({ ...pre, [key]: decodeURIComponent(value) }),
      {},
    );
};

export const multiSort = {
  created: function () {
    if (location.hash.startsWith("#")) {
      const hash = parseHash(this.$route.hash);
      if (Object.prototype.hasOwnProperty.call(hash, "sort")) {
        const sortKeys = hash.sort.split(",").filter((key) => {
          const realKey = key.startsWith("-") ? key.substring(1) : key;
          if (this.validSortKeys.includes(realKey)) {
            return true;
          }
          // eslint-disable-next-line no-console
          console.debug(`parsing '#sort=\\s+': unrecognized key '${realKey}'`);
          return false;
        });
        if (sortKeys.length > 0) {
          this.sortKeys = sortKeys;
        }
      }
    }
  },
  methods: {
    addSort: function (sortKey) {
      /*
       * add sort by sortKey to existing sort keys
       * if already sorting, by sortKey,
       *   reverse the sort order without changing the priority of sort keys
       * if not sorting by sortKey yet,
       *   sort first by this sortKey and then by existing sort keys
       */
      const index = this.sortKeys.indexOf(sortKey);
      if (index >= 0) {
        this.sortKeys.splice(index, 1, `-${sortKey}`);
      } else {
        const revIndex = this.sortKeys.indexOf(`-${sortKey}`);
        if (revIndex >= 0) {
          this.sortKeys.splice(revIndex, 1, sortKey);
        } else {
          this.sortKeys.unshift(`-${sortKey}`);
        }
      }
    },
    sortBy: function (sortKey) {
      /*
       * reset sort by sortKey
       * if the display is already sorted by sortKey (alone or in concert),
       *   then reverse the sort order, but always remove other sort keys
       */
      if (this.sortKeys.includes(sortKey)) {
        this.sortKeys = [`-${sortKey}`];
      } else if (this.sortKeys.includes(`-${sortKey}`)) {
        this.sortKeys = [sortKey];
      } else {
        this.sortKeys = [`-${sortKey}`];
      }
    },
    sortData: function (data) {
      return _orderBy(
        data,
        this.sortKeys.map((key) =>
          key.startsWith("-") ? key.substring(1) : key,
        ),
        this.sortKeys.map((key) => (key.startsWith("-") ? "desc" : "asc")),
      );
    },
    updateHashSort: function (hash) {
      if (!_isEqual(this.sortKeys, this.defaultSortKeys)) {
        hash.sort = this.sortKeys.join();
      }
    },
  },
};

export function formatQuarterly(d) {
  const quarters = ["Q1", "Q2", "Q3", "Q4"];

  const date = new Date(d);
  return `${quarters[Math.floor(date.getMonth() / 3)]} ${date.getFullYear()}`;
}

export function formatMonthly(d) {
  const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const date = new Date(d);
  return `${months[date.getMonth()]} ${date.getFullYear()}`;
}
