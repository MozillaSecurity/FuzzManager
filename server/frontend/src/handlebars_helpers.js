/**
 * Determine if value is a string.
 * @param {string} value - Value to test.
 */
export function isString(value) {
  return typeof value === "string";
}

/**
 * Split a string using the specified delimeter.
 * @param {string} str - String to split.
 * @param {string} delim - Delimiter to split on.
 */
export function split(str, delim) {
  if (!isString(str) || !isString(delim)) {
    return "";
  }

  return str.split(delim);
}

/**
 * Retrieve the element at "index" from an array.
 * @param {Array} arr - Target array
 * @param {number} index - Element index
 */
export function index(arr, index) {
  if (!Array.isArray(arr) && arr.length < index) {
    return "";
  }

  return arr[index];
}

/**
 * Determine if string includes the supplied pattern.
 * @param {string} str - The string to search.
 * @param {string} pattern - The pattern to match.
 */
export function includes(str, pattern) {
  if (!(isString(str) && isString(pattern) && pattern.length)) {
    return false;
  }

  return str.includes(pattern);
}
