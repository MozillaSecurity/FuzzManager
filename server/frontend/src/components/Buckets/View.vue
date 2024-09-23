<template>
  <div class="panel panel-default">
    <div class="panel-heading"><i class="bi bi-tag-fill"></i> Bucket</div>
    <div class="panel-body">
      <table class="table">
        <tbody>
          <tr>
            <td>Description</td>
            <td>{{ bucket.description }}</td>
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
              <br v-if="canEdit" /><br v-if="canEdit" />
              <div v-if="canEdit" class="btn-group">
                <a v-on:click="unlink" class="btn btn-danger">Unlink</a>
              </div>
            </td>
            <td v-else>
              No bug associated.
              <br v-if="canEdit" /><br v-if="canEdit" />
              <div v-if="canEdit" class="btn-group">
                <assignbutton :bucket="bucket.id" :providers="providers" />
                <a :href="createBugUrl" class="btn btn-danger">File a bug</a>
              </div>
            </td>
          </tr>
          <tr>
            <td>Reports in this bucket</td>
            <td>
              {{ bucket.size }}
              <activitygraph
                :data="bucket.report_history"
                :range="activityRange"
              />
              <div class="btn-group">
                <a :href="reportsUrl" class="btn btn-default">View Reports</a>
                <a
                  title="Add/Update"
                  class="btn btn-danger"
                  v-on:click="submitWatchForm"
                  >Notify on New Reports</a
                >
              </div>
              <form :action="watchUrl" ref="bucketWatchForm" method="post">
                <input type="hidden" name="bucket" :value="bucket.id" />
                <input
                  type="hidden"
                  name="report"
                  :value="bucket.latest_entry_id"
                />
              </form>
            </td>
          </tr>
          <tr>
            <td>Latest Report</td>
            <td>{{ bucket.latest_report | date }}</td>
          </tr>
          <tr>
            <td>Priority</td>
            <td>{{ bucket.priority }}</td>
          </tr>
        </tbody>
      </table>

      <strong>Signature</strong><br />
      <pre><code>{{ prettySignature }}</code></pre>

      <div v-if="canEdit" class="btn-group">
        <!--a :href="optUrl" class="btn btn-default">Optimize</a-->
        <a :href="editUrl" class="btn btn-default">Edit</a>
        <a :href="delUrl" class="btn btn-danger">Delete</a>
      </div>
    </div>
  </div>
</template>

<script>
import {
  assignExternalBug,
  date,
  errorParser,
  jsonPretty,
} from "../../helpers";
import ActivityGraph from "../ActivityGraph.vue";
import AssignBtn from "./AssignBtn.vue";
import swal from "sweetalert";

export default {
  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
  },
  computed: {
    prettySignature() {
      return jsonPretty(this.bucket.signature);
    },
  },
  data: () => ({
    description: "",
  }),
  filters: {
    date: date,
  },
  props: {
    activityRange: {
      type: Number,
      required: true,
    },
    bucket: {
      type: Object,
      required: true,
    },
    reportsUrl: {
      type: String,
      required: true,
    },
    canEdit: {
      type: Boolean,
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
    watchUrl: {
      type: String,
      required: true,
    },
  },
  mounted() {
    const el = document.getElementsByName("csrfmiddlewaretoken")[0];
    this.$refs.bucketWatchForm.appendChild(el);
  },
  methods: {
    submitWatchForm() {
      this.$refs.bucketWatchForm.submit();
    },
    unlink() {
      swal({
        title: "Unlink bug",
        text: "Are you sure that you want to unlink this signature from its assigned external bug?",
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
