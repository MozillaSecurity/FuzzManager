<template>
  <Popper trigger="hover" :options="{ placement: 'right' }">
    <div class="popper">
      <div class="pop-header">Signatures</div>
      <div class="pop-body">
        <h4>Signature structure</h4>
        <div class="pop-list mt-1">
          <p>
            Queries are JSON objects representing a series of
            &ldquo;symptoms&rdquo; which will be checked against WebCompat
            reports. Each symptom object can have these key/values:
          </p>
          <ul>
            <li>
              <code>type</code> (required), the type of this symptom object.
              Value must be one of: <code>app_channel</code>,
              <code>app_name</code>, <code>app_version</code>,
              <code>breakage_category</code>, <code>comments</code>,
              <code>details</code>, <code>os</code>, <code>reported_at</code>,
              <code>url</code>, or <code>uuid</code>.
            </li>
            <li>
              <code>value</code> (any <code>type</code> except
              <code>reported_at</code>, precludes <code>pattern</code>), value
              to match (exactly). This can be a string, boolean, or
              <code>null</code>.
            </li>
            <li>
              <code>pattern</code> (any <code>type</code> except
              <code>reported_at</code>, precludes <code>value</code>), regular
              expression to match (exactly). This must be a string.
            </li>
            <li>
              <code>part</code> (only with <code>type: url</code>), the part of
              the URL to match. Value must be one of: <code>scheme</code>,
              <code>netloc</code>, <code>path</code>, <code>query</code>,
              <code>fragment</code>, <code>username</code>,
              <code>password</code>, <code>hostname</code>, or
              <code>port</code>. If <code>part</code> is not given,
              <code>url</code> matches against the entire URL.
            </li>
            <li>
              <code>path</code> (only with <code>type: details</code>), the
              <a
                href="https://www.rfc-editor.org/rfc/rfc9535.html"
                target="_blank"
                >JSONPath</a
              >
              within <code>details</code> to select for <code>value</code> or
              <code>pattern</code> matching.
            </li>
            <li>
              <code>time</code>, <code>before</code>, and
              <code>after</code> (only with <code>type: reported_at</code>)
              compare by date/time. <code>time</code> matches exactly, the
              others compare as their name implies. Dates are strings which
              conform to
              <a
                href="https://www.rfc-editor.org/rfc/rfc3339.html#section-5.6"
                target="_blank"
                >RFC 3339 &sect; 5.6</a
              >. <code>time</code> precludes <code>before</code>/<code
                >after</code
              >
              and vice versa.
            </li>
          </ul>
        </div>
      </div>
    </div>
    <!-- eslint-disable-next-line -->
    <span slot="reference">
      <i class="bi bi-question-circle-fill"></i>
    </span>
  </Popper>
</template>

<script>
import Popper from "vue-popperjs";

export default {
  components: {
    Popper,
  },
};
</script>

<style scoped>
.ml-8 {
  margin-left: 8rem;
}
.mt-1 {
  margin-top: 1rem;
}
.pop-header {
  padding: 1rem;
  margin-bottom: 0;
  background-color: #f7f7f7;
  border-bottom: 1px solid #ebebeb;
  font-size: 1.5rem;
  font-weight: bold;
}
.pop-body {
  padding: 1rem;
  color: #212529;
}
.pop-body a {
  margin-bottom: 1rem;
}
.pop-list p {
  margin-bottom: 0.25rem;
}
.popper {
  text-align: left;
}
</style>
