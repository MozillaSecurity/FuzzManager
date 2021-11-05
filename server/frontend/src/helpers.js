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
      })
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
      {}
    );
};
