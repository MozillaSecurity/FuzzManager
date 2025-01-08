<template>
  <div id="main" class="panel panel-default">
    <!-- Panel Header -->
    <div class="panel-heading">
      <i class="bi bi-funnel-fill"></i> Report Configurations
    </div>
    <!-- Panel Body -->
    <div class="panel-body">
      <!-- Button: Create -->
      <button class="btn btn-default" @click="rc_dialog()">
        Create new Report Configuration
      </button>
      <!-- Input: Search -->
      <div v-show="search">
        <input ref="search" v-model="search" type="text" class="form-control" />
      </div>
      <!--- Modal Component -->
      <div
        v-if="modal.show"
        class="modal modal-mask"
        role="document"
        style="display: block"
      >
        <div class="modal-dialog modal-dialog-centered" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">{{ modal.title }}</h5>
              <!-- Todo: This must be naturally on the same line. -->
              <div class="pull-right" style="transform: translateY(-100%)">
                <button
                  type="button"
                  class="close"
                  data-dismiss="modal"
                  @click="rc_close()"
                >
                  <span aria-hidden="true">&times;</span>
                </button>
              </div>
            </div>
            <div class="modal-body">
              <form>
                <div class="form-group">
                  <label class="col-form-label">Logical Parent:</label>
                  <input
                    v-model="modal.rc.logical_parent"
                    type="text"
                    class="form-control"
                  />
                </div>
                <div class="form-group">
                  <label class="col-form-label">Description:</label>
                  <input
                    v-model="modal.rc.description"
                    type="text"
                    class="form-control"
                  />
                </div>
                <div class="form-group">
                  <label class="col-form-label">Repository:</label>
                  <input
                    v-model="modal.rc.repository"
                    type="text"
                    class="form-control"
                  />
                </div>
                <div class="form-group">
                  <label class="col-form-label">Directives:</label>
                  <textarea
                    v-model="modal.rc.directives"
                    rows="10"
                    class="form-control"
                  ></textarea>
                </div>
                <div class="form-group">
                  <label class="col-form-label">Public</label>
                  <input
                    v-model="modal.rc.public"
                    type="checkbox"
                    class="form-control"
                  />
                </div>
              </form>
            </div>
            <div class="modal-footer">
              <button class="btn btn-primary" @click="modal_ok">Ok</button>
              <button type="button" class="btn btn-danger" @click="rc_close()">
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
      <!-- End of Modal Component -->
    </div>
    <!-- End of Panel Body -->
    <!-- Report Configuration Table -->
    <table class="table table-condensed table-hover table-bordered table-db">
      <thead>
        <tr>
          <th
            :class="{ active: sortKey == 'id' }"
            style="width: 25px"
            @click="sortBy('id')"
          >
            ID
          </th>
          <th
            :class="{ active: sortKey == 'description' }"
            style="width: 100px"
            @click="sortBy('description')"
          >
            Description
          </th>
          <th
            :class="{ active: sortKey == 'logical_parent' }"
            style="width: 25px"
            @click="sortBy('logical_parent')"
          >
            Logical Parent
          </th>
          <th
            :class="{ active: sortKey == 'repository' }"
            style="width: 50px"
            @click="sortBy('repository')"
          >
            Repository
          </th>
          <th style="width: 100px">Directives</th>
          <th
            :class="{ active: sortKey == 'public' }"
            style="width: 25px"
            @click="sortBy('public')"
          >
            Public
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="rc in ordered_rc_list"
          :id="rc.id"
          :key="rc.id"
          @click="rc_dialog(rc)"
        >
          <td>{{ rc.id }}</td>
          <td>{{ rc.description }}</td>
          <td>{{ rc.logical_parent }}</td>
          <td>{{ rc.repository }}</td>
          <td>
            <pre>{{ rc.directives }}</pre>
          </td>
          <td>{{ rc.public }}</td>
        </tr>
      </tbody>
    </table>
    <!-- End of Report Configuration Table -->
  </div>
</template>
<script>
import _ from "lodash";
import swal from "sweetalert";
import { defineComponent } from "vue";
import { reportConfiguration } from "../../api";
import { getCSRFToken } from "../../cookie_csrf";
import { E_SERVER_ERROR } from "../../helpers";
import { HashParamManager } from "../../params";
import "../../public/css/covmanager.css";

const URLS = {
  repository_search: "/covmanager/repositories/search/api/",
  rc_list: "/covmanager/reportconfigurations/api/",
  rc_create: "/covmanager/reportconfigurations/api/create/",
};

let pmanager = new HashParamManager();

export default defineComponent({
  data() {
    return {
      csrftoken: "",
      rc_list: null,
      sortKey: "",
      reverse: false,
      search: "",
      showModal: false,
      modal: {
        show: false,
        title: "",
        rc: null,
      },
    };
  },
  computed: {
    ordered_rc_list() {
      return _.orderBy(
        this.rc_list,
        [this.sortKey],
        [this.reverse ? "desc" : "asc"],
      );
    },
  },
  watch: {
    search() {
      return this.fetch();
    },
  },
  mounted() {
    window.addEventListener("keydown", this.keydown);
    window.addEventListener("keyup", this.keyup);
    window.addEventListener("hashchange", this.onHashChange);

    this.csrftoken = getCSRFToken();
    this.fetch();
  },
  methods: {
    fetch: _.throttle(function () {
      this.loading = true;
      reportConfiguration({ q: this.search })
        .then((json) => {
          this.rc_list = json["results"];
          this.loading = false;
        })
        .catch(() => {
          swal("Oops", E_SERVER_ERROR, "error");
          this.loading = false;
        });
    }, 500),
    sortBy: function (sortKey) {
      this.reverse = this.sortKey === sortKey ? !this.reverse : false;
      this.sortKey = sortKey;
    },
    rc_dialog: function (rc) {
      const title = " Report Configuration";

      if (rc) {
        this.modal.title = `Edit ${title}`;
        this.modal.rc = rc;
      } else {
        this.modal.title = `Create ${title}`;
        this.modal.rc = {};
      }

      this.modal.show = true;
    },
    rc_close: function () {
      this.modal.show = false;
    },
    rc_click_handler: function (rc) {
      return this.rc_dialog(rc);
    },
    keydown: function (e) {
      if (this.modal.show) {
        return;
      }

      if (!e) {
        e = window.event;
      }

      // Ignore the keypress if any of these modifiers are active
      if (
        e.getModifierState("Fn") ||
        e.getModifierState("OS") ||
        e.getModifierState("Win") ||
        e.getModifierState("Control") ||
        e.getModifierState("Alt") ||
        e.getModifierState("Meta")
      ) {
        return;
      }

      if (!e.metaKey) {
        if (
          (e.keyCode >= 65 && e.keyCode <= 90) ||
          (e.keyCode >= 48 && e.keyCode <= 57)
        ) {
          if (!this.search) {
            let str = String.fromCharCode(e.keyCode);
            if (!e.shiftKey) {
              str = str.toLowerCase();
            }
            this.search = str;
          } else {
            this.$refs.search.focus();
          }
        } else if (e.keyCode === 13) {
          // ENTER was pressed, edit
          let target = Object.keys(this.ordered_rc_list)[0];
          if (target) {
            this.rc_click_handle(this.ordered_rc_list[target]);
          }
        }
      }
    },
    keyup: function (e) {
      if (this.modal.show) {
        return;
      }

      // We use the |keyup| event instead of |keydown| here in order to not collide with Vue's internal updating of
      // the search model on input events.
      if (!e) {
        e = window.event;
      }
      if (!e.metaKey) {
        if (this.search && e.keyCode === 27) {
          // ESC was pressed, clear search.
          this.search = "";
        }
      }
    },
    modal_ok: function () {
      let url = URLS.rc_create;
      if (this.modal.rc["id"]) {
        url = `${URLS.rc_list}update/${this.modal.rc["id"]}/`;
      }

      this.modal_submit(url, this.modal.rc).then(() => {
        this.modal.show = false;
      });
    },
    modal_submit: function (url, data) {
      let self = this;

      return fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": this.csrftoken,
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
    },
    onHashChange() {
      pmanager.update_state();
      const new_search = pmanager.get_value("q", "");
      if (this.search != new_search) {
        this.search = new_search;
      }
    },
  },
});
</script>
