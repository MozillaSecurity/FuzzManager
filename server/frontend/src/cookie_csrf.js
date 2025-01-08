export function getCSRFToken() {
  const needle = "csrftoken=";
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const trimmedCookie = cookie.trim();
      if (trimmedCookie.startsWith(needle)) {
        return decodeURIComponent(trimmedCookie.substring(needle.length));
      }
    }
  }
}
