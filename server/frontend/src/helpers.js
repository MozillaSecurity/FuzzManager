/**
 * A helper method to try to parse errors into human-readable strings.
 * This also parses anything that is not an Error, since JavaScript allows throwing anything, not just errors.
 *
 * @param {any} error Any error.
 * @returns {string} A string representing the error in a way as human-readable as possible.
 */
export const errorParser = error => {
    if (typeof error === 'string') return error

    /*
     * There are two types of strings in JS!
     * We can't call null.toString() or undefined.toString(), but we can call String(null).toString()…
     */
    if (!error) return String(error).toString()

    let message = null
    if (error.response && error.response.data) {
        if (
            typeof error.response.data === 'string' ||
            error.response.data instanceof String ||
            Array.isArray(error.response.data)
        ) message = error.response.data
        else if (error.response.data.detail) message = error.response.data.detail
    }

    if (!message && error.message) message = error.message
    if (!message) return error.toString()

    if (Array.isArray(message)) return message.join(' - ')
    if (typeof message === 'string') return message
    return message.toString()
}
