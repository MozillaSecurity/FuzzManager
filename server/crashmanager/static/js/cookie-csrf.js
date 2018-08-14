function getCSRFToken() {
  let needle = "csrftoken="
  if (document.cookie && document.cookie !== '') {
    let cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      let cookie = jQuery.trim(cookies[i]);
      if (cookie.startsWith(needle)) {
        return decodeURIComponent(cookie.substring(needle.length));
      }
    }
  }
}
