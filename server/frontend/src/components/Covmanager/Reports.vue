<template>
  <div id="main" class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-file-bar-graph"></i> Aggregated Reports
    </div>
    <div class="panel-body">
      <div class="panel panel-default" style="float: right">
        <div class="panel-heading">
          <i class="bi bi-lightning-charge-fill"></i> Actions
        </div>
        <div class="panel-body">
          <button class="btn btn-default" @click="navigate('diff')">
            View Differences
          </button>
          <button class="btn btn-default" @click="summary_diff()">
            View Summarized Diff
          </button>
          <button class="btn btn-default" @click="toggle_reviewed_only()">
            {{ reviewed_only_btn_text }}
          </button>
          <!--<button @click="navigate('patch')" class="btn btn-default">Patch Analysis</button>-->
        </div>
      </div>

      <div style="font-size: 16px">
        The list below contains all coverage reports that are automatically
        produced. This includes weekly, monthly and quarterly reports.<br /><br />

        You can view each report individually, inspect its summary or select
        multiple reports and view their difference.<br /><br />

        Note that unreviewed reports might be broken or contain faulty data. You
        can filter for reviewed reports or ask the fuzzing team for assistance.
      </div>
    </div>
    <table class="table table-condensed table-bordered table-db">
      <thead>
        <tr>
          <th
            :class="{ active: sortKey == 'description' }"
            style="width: 150px"
            @click="sortBy('description')"
          >
            Description
          </th>
          <th
            :class="{ active: sortKey == 'data_created' }"
            style="width: 80px"
            @click="sortBy('data_created')"
          >
            Created
          </th>
          <th style="width: 100px"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="report in ordered_reports"
          :id="report.id"
          :key="report.id"
          :class="report.css_class"
          @click="report_click_handler(report.id)"
        >
          <td>{{ report.description }}</td>
          <td>{{ formatDate(report.data_created) }}</td>
          <td>
            <button
              class="btn btn-default"
              @click.stop="summary(report.coverage, report.tag)"
            >
              View Report Summary
            </button>
            <button
              class="btn btn-default"
              @click.stop="browse(report.coverage)"
            >
              Browse
            </button>
            <button
              v-if="can_publish"
              class="btn btn-default"
              @click.stop="publish(report)"
            >
              {{ report.publish_text }}
            </button>
            <button
              v-if="can_publish"
              class="btn btn-default"
              @click.stop="promote(report)"
            >
              {{ report.promote_text }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import _ from "lodash";
import swal from "sweetalert";
import { defineComponent } from "vue";
import { getCSRFToken } from "../../cookie_csrf";
import {
  E_SERVER_ERROR,
  formatClientTimestamp,
  formatMonthly,
  formatQuarterly,
} from "../../helpers";
import { HashParamManager } from "../../params";
import "../../public/css/covmanager.css";

let URLS = {
  collections_api: "/covmanager/collections/api/",
  reports_api: "/covmanager/reports/api/",
  diff: "/covmanager/collections/diff/",
  patch: "/covmanager/collections/patch/",
};

const pmanager = new HashParamManager();

export default defineComponent({
  props: {
    canPublish: {
      type: Boolean,
      required: true,
    },
  },
  data() {
    return {
      csrftoken: "",
      reports: null,
      sortKey: "data_created",
      reverse: true,
      block_fetch: true,
      can_publish: this.canPublish,
      show_reviewed_only: false,
      selected_reports: [],
    };
  },
  computed: {
    reviewed_only_btn_text() {
      return this.show_reviewed_only
        ? "Show Unreviewed Reports"
        : "Hide Unreviewed Reports";
    },
    ordered_reports() {
      if (this.reports) {
        for (let report of this.reports) {
          report.css_class = {};
          let selected = this.selected_reports.indexOf(report.id) >= 0;

          report.css_class["report"] = true;

          if (selected) {
            report.css_class["no-hover"] = true;
          }

          // Compute Publish/Unpublish button text
          report.publish_text = report.public ? "Unpublish" : "Publish";

          // We optionally prefix the with the tag of the report
          let tag = "";
          if (report.tag) {
            tag = report.tag + " ";
          }

          // Compute description and css class
          if (report.is_quarterly) {
            report.css_class["report-quarterly"] = true;
            report.description =
              "Quarterly " +
              tag +
              "Report - " +
              formatQuarterly(report.data_created);
            if (selected) report.css_class["report-quarterly-selected"] = true;
            report.promote_text = "Demote to Weekly";
          } else if (report.is_monthly) {
            report.css_class["report-monthly"] = true;
            report.description =
              "Monthly " +
              tag +
              "Report - " +
              formatMonthly(report.data_created);
            report.promote_text = "Promote to Quarterly";
            if (selected) report.css_class["report-monthly-selected"] = true;
          } else {
            report.css_class["report-weekly"] = true;
            report.description = "Weekly " + tag + "Report";
            report.promote_text = "Promote to Monthly";
            if (selected) report.css_class["report-weekly-selected"] = true;
          }
        }
      }
      return _.orderBy(
        this.reports,
        [this.sortKey],
        [this.reverse ? "desc" : "asc"],
      );
    },
  },
  watch: {
    show_reviewed_only() {
      return this.fetch();
    },
  },
  created() {
    this.csrftoken = getCSRFToken();
    this.fetch();

    pmanager.update_state();
    this.show_reviewed_only = pmanager.get_value("reviewed", false);
  },
  mounted() {
    window.addEventListener("hashchange", () => {
      pmanager.update_state();
      const show_reviewed_only = pmanager.get_value("reviewed", false);
      if (this.show_reviewed_only !== show_reviewed_only) {
        this.show_reviewed_only = show_reviewed_only;
      }
    });
  },
  unmounted() {
    window.removeEventListener("hashchange", this.handleHashChange);
  },
  methods: {
    apiurl() {
      let url = URLS.reports_api;
      if (!pmanager.get_value("reviewed", false)) url += "?unpublished=1";

      return url;
    },
    fetch: _.throttle(function () {
      this.loading = true;
      fetch(this.apiurl(), {
        method: "GET",
        credentials: "same-origin",
      })
        .then((response) => {
          if (response.ok) {
            return response.json();
          }
          swal("Oops", E_SERVER_ERROR, "error");
          this.loading = false;
        })
        .then((json) => {
          this.reports = json["results"];
          this.loading = false;
          this.block_fetch = false;
        });
    }, 500),
    navigate(dst) {
      let ids = [];

      if (this.selected_reports.length > 0) {
        for (const report of this.reports) {
          if (this.selected_reports.indexOf(report.id) >= 0) {
            ids.push(report.coverage);
          }
        }
      } else {
        for (const report of this.ordered_reports) {
          ids.push(report.coverage);
        }
      }

      if (ids) {
        let url = URLS[dst] + "#ids=" + ids.join(",");
        if (window.location.hash) {
          url += "&" + window.location.hash.substr(1);
        }

        const win = window.open(url, "_blank");
        win.focus();
      }
    },
    sortBy(sortKey) {
      this.reverse = this.sortKey === sortKey ? !this.reverse : false;
      this.sortKey = sortKey;
    },
    browse(id) {
      window.open(`../collections/${id}/browse/`, "_blank").focus();
    },
    summary(id, tag) {
      if (tag) {
        tag = `#root=${tag}`;
      }
      window.open(`../collections/${id}/summary/${tag}`, "_blank").focus();
    },
    report_click_handler(id) {
      const self = this;
      const idx = self.selected_reports.indexOf(id);

      if (idx < 0) {
        self.selected_reports.push(id);
      } else {
        self.selected_reports.splice(idx, 1);
      }
    },
    toggle_reviewed_only() {
      if (this.show_reviewed_only) {
        pmanager.update_value("reviewed", "");
      } else {
        pmanager.update_value("reviewed", "1");
      }
      pmanager.update_hash();
    },
    publish(report) {
      let url = URLS.reports_api + "update/" + report.id + "/";
      let data = { public: !report.public };
      let desc = "publish this report";

      if (report.public) {
        desc = "unpublish this report";
      }

      this.update(url, data, desc);
    },
    promote(report) {
      let url = URLS.reports_api + "update/" + report.id + "/";
      let data = {};
      let desc = "promote this report";

      if (report.is_quarterly) {
        data["is_quarterly"] = false;
        data["is_monthly"] = false;
        desc = "demote this report";
      } else if (report.is_monthly) {
        data["is_quarterly"] = true;
      } else {
        data["is_monthly"] = true;
      }

      this.update(url, data, desc);
    },
    update(url, data, desc) {
      let self = this;

      swal({
        title: "Confirm Action",
        text: `Would you really like to ${desc}?`,
        icon: "warning",
        buttons: true,
      }).then((confirmed) => {
        if (!confirmed) {
          /* User pressed cancel button */
          return;
        }

        fetch(url, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": self.csrftoken,
          },
          body: JSON.stringify(data),
        })
          .then((response) => {
            this.loading = false;
            if (response.ok) {
              return response.json();
            }
            swal("Oops", E_SERVER_ERROR, "error");
          })
          .then(() => {
            self.fetch();
          });
      });
    },
    summary_diff() {
      if (this.selected_reports.length != 2) {
        swal(
          "Oops",
          "Summarized diff requires exactly 2 reports to be selected",
          "error",
        );
        return;
      }

      let collection_ids = [];

      for (let report of this.reports) {
        if (this.selected_reports.indexOf(report.id) >= 0) {
          collection_ids.push(report.coverage);
        }

        if (collection_ids.length == 2) break;
      }

      // Make sure we always diff forward
      if (collection_ids[0] > collection_ids[1]) {
        let tid = collection_ids[0];
        collection_ids[0] = collection_ids[1];
        collection_ids[1] = tid;
      }

      window
        .open(
          `../collections/${collection_ids[1]}/summary/htmlexport/?diff=${collection_ids[0]}`,
          "_blank",
        )
        .focus();
    },
    formatDate: function (datetime) {
      return formatClientTimestamp(datetime);
    },
  },
});
</script>
