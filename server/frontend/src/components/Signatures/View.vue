<template>
  <div class="panel panel-default">
    <div class="panel-heading"><i class="bi bi-tag-fill"></i> Signature</div>
    <div class="panel-body">
      <table class="table">
        <tbody>
          <tr>
            <td>Description</td>
            <td>{{ bucket.shortDescription }}</td>
          </tr>
          <tr v-if="bucket.frequent">
            <td>Frequent bucket</td>
            <td></td>
          </tr>
          <tr v-if="bucket.permanent">
            <td>Permanent bucket</td>
            <td></td>
          </tr>
          <tr>
            <td>External Bug Status</td>
            <td v-if="bucket.bug">
              <span v-if="bucket.bug_urltemplate">
                Reported as
                <a
                  :class="{
                    fixedbug: bucket.bug_closed,
                  }"
                  :href="bucket.bug_urltemplate"
                  target="_blank"
                  >bug {{ bucket.bug }}</a
                >.
              </span>
              <span v-else>
                Reported as bug {{ bucket.bug }} on {{ bucket.bug_hostname }}
              </span>
              <br /><br />
              <div class="btn-group">
                <a v-on:click="unlink" class="btn btn-danger">Unlink</a>
              </div>
            </td>
            <td v-else>
              Unreported.
              <br /><br />
              <div class="btn-group">
                <assignbutton :bucket="bucket.id" :providers="providers" />
                <a
                  v-if="bucket.best_entry"
                  :href="createBugUrl"
                  class="btn btn-danger"
                  >File a bug with best crash entry</a
                >
              </div>
            </td>
          </tr>
          <tr>
            <td>Crashes covered by this signature</td>
            <td>
              {{ bucket.size }}
              <activitygraph
                :data="bucket.crash_history"
                :range="activityRange"
              />
              <form :action="sigWatchUrl" ref="sigWatchForm" method="post">
                <input type="hidden" name="bucket" :value="bucket.id" />
                <input
                  type="hidden"
                  name="crash"
                  :value="bucket.latest_entry"
                />
                <input
                  type="submit"
                  name="submit"
                  value="Watch for New Crashes"
                  title="Add/Update"
                  class="btn btn-default"
                />
              </form>
            </td>
          </tr>
          <tr v-if="bucket.best_entry">
            <td>Best Crash Entry</td>
            <td>
              <a :href="bestViewUrl">{{ bucket.best_entry }}</a> (Size:
              {{ bestEntrySize }})
            </td>
          </tr>
        </tbody>
      </table>

      <strong>Signature</strong><br />
      <pre><code>{{ bucket.signature }}</code></pre>

      <div class="btn-group">
        <a :href="crashesUrl" class="btn btn-default">Associated Crashes</a>
        <a :href="optUrl" class="btn btn-default">Optimize</a>
        <a
          v-if="bucket.has_optimization"
          :href="bucket.opt_pre_url"
          class="btn btn-default"
          >Optimize (Precomputed)</a
        >
        <a :href="editUrl" class="btn btn-default">Edit</a>
        <a :href="delUrl" class="btn btn-danger">Delete</a>
      </div>
    </div>
  </div>
</template>

<script>
import { assignExternalBug, errorParser } from "../../helpers";
import ActivityGraph from "../ActivityGraph.vue";
import AssignBtn from "./AssignBtn.vue";
import swal from "sweetalert";

export default {
  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
  },
  data: () => ({
    frequent: false,
    permanent: false,
    shortDescription: "",
  }),
  props: {
    activityRange: {
      type: Number,
      required: true,
    },
    bestEntrySize: {
      type: Number,
      required: true,
    },
    bestViewUrl: {
      type: String,
      default: null,
    },
    bucket: {
      type: Object,
      required: true,
    },
    crashesUrl: {
      type: String,
      required: true,
    },
    createBugUrl: {
      type: String,
      default: null,
    },
    delUrl: {
      type: String,
      required: true,
    },
    editUrl: {
      type: String,
      required: true,
    },
    optUrl: {
      type: String,
      required: true,
    },
    providers: {
      type: Array,
      required: true,
    },
    sigWatchUrl: {
      type: String,
      required: true,
    },
  },
  mounted() {
    const el = document.getElementsByName("csrfmiddlewaretoken")[0];
    this.$refs.sigWatchForm.appendChild(el);
  },
  methods: {
    unlink() {
      swal({
        title: "Unlink bug",
        text:
          "Are you sure that you want to unlink this signature from its assigned external bug?",
        buttons: true,
      }).then((value) => {
        if (value) {
          assignExternalBug(this.bucket.id, null, null)
            .then((data) => {
              window.location.href = data.url;
            })
            .catch((err) => {
              swal("Oops", errorParser(err), "error");
            });
        }
      });
    },
  },
};
</script>

<style scoped>
form {
  display: inline;
}
</style>
