function getCSRFToken() {
  const needle = "csrftoken="
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(needle)) {
        return decodeURIComponent(cookie.substring(needle.length));
      }
    }
  }
}
