<template>
  <div id="main" class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-clipboard-data"></i> Coverage Collections
    </div>
    <div class="panel-body">
      <div class="panel panel-default" style="float: left">
        <div class="panel-heading">
          <i class="bi bi-archive-fill"></i> Repository Filters
        </div>
        <div class="panel-body">
          <div>
            <label>Repository:</label
            ><input
              v-model="search.repository.value"
              type="text"
              class="form-control"
              @focus="suggestions.repository.enabled = true"
              @blur="suggestions.repository.enabled = false"
            />
            <div v-show="suggestions.repository.enabled">
              <div
                v-for="name in suggestions.repository.value"
                :key="name"
                @mousedown="take_suggestion('repository', name)"
              >
                {{ name }}
              </div>
            </div>
          </div>
          <div>
            <label>Revision:</label
            ><input
              v-model="search.revision.value"
              type="text"
              class="form-control"
            />
          </div>
          <div>
            <label>Branch:</label
            ><input
              v-model="search.branch.value"
              type="text"
              class="form-control"
            />
          </div>
        </div>
      </div>

      <div class="panel panel-default" style="float: left">
        <div class="panel-heading">
          <i class="bi bi-funnel-fill"></i> Misc Filters
        </div>
        <div class="panel-body">
          <div>
            <label>Tool:</label>
            <input
              v-model="search.tools.value"
              type="text"
              class="form-control"
              @focus="suggestions.tools.enabled = true"
              @blur="suggestions.tools.enabled = false"
            />
            <div v-show="suggestions.tools.enabled">
              <div
                v-for="name in suggestions.tools.value"
                :key="name"
                @mousedown="take_suggestion('tools', name)"
              >
                {{ name }}
              </div>
            </div>
          </div>
          <div>
            <label>Description:</label>
            <input
              v-model="search.description.value"
              type="text"
              class="form-control"
            />
          </div>
          <div>
            <label>Result Limit:</label>
            <input
              v-model="search.limit.value"
              type="text"
              class="form-control"
            />
          </div>
        </div>
      </div>

      <div class="panel panel-default" style="float: left">
        <div class="panel-heading">
          <i class="bi bi-calendar-range"></i> Date Filters
        </div>
        <div class="panel-body">
          <!--
      <label>Newer than:</label><datepicker placeholder="Select Date"></datepicker>
      <label>Older than:</label><datepicker placeholder="Select Date"></datepicker>
      -->
        </div>
      </div>

      <div class="panel panel-default" style="float: right">
        <div class="panel-heading">
          <i class="bi bi-lightning-charge-fill"></i> Actions
        </div>
        <div class="panel-body">
          <button class="btn btn-default" @click="navigate('diff')">
            View Differences
          </button>
          <button class="btn btn-default" @click="aggregate()">
            Aggregate
          </button>
          <button class="btn btn-default" @click="navigate('patch')">
            Patch Analysis
          </button>
          <button class="btn btn-default" @click="summary()">
            Report Summary
          </button>
        </div>
      </div>
    </div>
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
            :class="{ active: sortKey == 'created' }"
            style="width: 80px"
            @click="sortBy('created')"
          >
            Created
          </th>
          <th
            :class="{ active: sortKey == 'repository' }"
            style="width: 50px"
            @click="sortBy('repository')"
          >
            Repository
          </th>
          <th
            :class="{ active: sortKey == 'revision' }"
            style="width: 100px"
            @click="sortBy('revision')"
          >
            Revision
          </th>
          <th
            :class="{ active: sortKey == 'branch' }"
            style="width: 50px"
            @click="sortBy('branch')"
          >
            Branch
          </th>
          <th
            :class="{ active: sortKey == 'tools' }"
            style="width: 50px"
            @click="sortBy('tools')"
          >
            Tools
          </th>
          <th
            :class="{ active: sortKey == 'description' }"
            style="width: 150px"
            @click="sortBy('description')"
          >
            Description
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="collection in ordered_collections"
          :id="collection.id"
          :key="collection.id"
          @click="collection_click_handler(collection.id)"
        >
          <td>
            <a :href="`${collection.id}/browse`">{{ collection.id }}</a>
          </td>
          <td>{{ formatDate(collection.created) }}</td>
          <td>
            <a :href="`../repositories/`">{{ collection.repository }}</a>
          </td>
          <td>{{ collection.revision }}</td>
          <td>{{ collection.branch }}</td>
          <td>{{ collection.tools }}</td>
          <td>{{ collection.description }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import _ from "lodash";
import swal from "sweetalert";
import { defineComponent } from "vue";
import "../../public/css/covmanager.css";

import { collectionAggregate, collectionList } from "../../api";
import { E_SERVER_ERROR, formatClientTimestamp } from "../../helpers";
import { HashParamManager } from "../../params";

let URLS = {
  collections_api: "/covmanager/collections/api/",
  diff: "/covmanager/collections/diff/",
  patch: "/covmanager/collections/patch/",
  aggregate: "/covmanager/collections/aggregate/api/",
  repository_search: "/covmanager/repositories/search/api/",
  tools_search: "/covmanager/tools/search/api/",
};

let pmanager = new HashParamManager();
export default defineComponent({
  data() {
    return {
      collections: null,
      sortKey: "",
      reverse: false,
      block_fetch: true,
      search_initialized: false,

      search: {
        branch: { value: "", contains: true },
        description: { value: "", contains: true },
        repository: { value: "", contains: true, postfix: "__name" },
        revision: { value: "", contains: true },
        tools: { value: "", contains: true, postfix: "__name" },
        limit: { value: "10", contains: false },
      },

      suggestions: {
        repository: { value: [], enabled: false },
        tools: { value: [], enabled: false },
      },

      selected_collections: [],
    };
  },
  computed: {
    ordered_collections() {
      return _.orderBy(
        this.collections,
        [this.sortKey],
        [this.reverse ? "desc" : "asc"],
      );
    },
  },
  watch: {
    // This handles all search updates
    search: { handler: "fetch", deep: true },

    // Watches for changes to values that need suggestions
    "search.repository.value": function () {
      this.update_suggestions("repository");
    },
    "search.tools.value": function () {
      this.update_suggestions("tools");
    },
    collections: function () {
      /* Whenever our search results change, deselect everything */
      this.selected_collections = [];
      for (const collection of this.collections) {
        const target = document.getElementById(collection.id);
        if (target) target.classList.remove("collection-selected");
      }
    },
  },
  created() {
    const self = this;
    pmanager.forEach(function (k, v) {
      // TODO: This is a shortcut that saves us iterating through this.search
      // for every key that we are trying to map to a field in our search
      // object, but this won't work once we have more postfixes.
      k = k.replace(/__contains$/, "");
      k = k.replace(/__name$/, "");

      if (k != "" && k in self.search) {
        self.search[k].value = v;
      }
    });

    self.fetch();
  },
  methods: {
    apiParam: function () {
      const queryParams = {};

      for (let k in this.search) {
        const obj = this.search[k];
        const v = obj.value;
        queryParams[k] = obj.value;

        if ("postfix" in obj) {
          k += obj.postfix;
        }

        if ("contains" in obj && obj.contains) {
          k += "__contains";
        }

        pmanager.update_value(k, v);
      }

      let query = pmanager.get_query();

      if (query) {
        pmanager.update_hash();
      }

      const queryObject = Object.fromEntries(new URLSearchParams(query));

      return queryObject;
    },
    fetch: _.throttle(function () {
      this.loading = true;
      collectionList(this.apiParam())
        .then((json) => {
          this.collections = json["results"];
          this.loading = false;
          this.block_fetch = false;
        })
        .catch(() => {
          swal("Oops", E_SERVER_ERROR, "error");
          this.loading = false;
        });
    }, 500),
    navigate: function (dst) {
      let ids = [];

      if (this.selected_collections.length > 0) {
        ids = this.selected_collections;
      } else {
        for (const element of this.ordered_collections) {
          ids.push(element.id);
        }
      }

      if (ids) {
        let url = URLS[dst] + "#ids=" + ids.join(",");
        if (window.location.hash) {
          url += "&" + window.location.hash.substring(1);
        }

        const win = window.open(url, "_blank");
        win.focus();
      }
    },
    sortBy: function (sortKey) {
      this.reverse = this.sortKey === sortKey ? !this.reverse : false;
      this.sortKey = sortKey;
    },
    update_suggestions: _.throttle(function (key) {
      fetch(URLS[key + "_search"] + "?name=" + this.search[key].value, {
        method: "GET",
        credentials: "same-origin",
      })
        .then((response) => {
          if (response.ok) {
            return response.json();
          }
          swal("Oops", E_SERVER_ERROR, "error");
        })
        .then((json) => {
          this.suggestions[key].value = json["results"];
        });
    }, 500),
    take_suggestion: function (key, val) {
      this.suggestions[key].enabled = false;
      this.suggestions[key].value = [];
      this.search[key].value = val;
    },
    aggregate: function () {
      let ids = [];

      if (this.selected_collections.length > 0) {
        ids = this.selected_collections;
      } else {
        for (const element of this.ordered_collections) {
          ids.push(element.id);
        }
      }

      if (ids) {
        swal({
          title: "Create Collection Aggregation",
          text: "Enter optional new description for result collection",
          content: "input",
          buttons: true,
        }).then((description) => {
          if (!description) {
            /* User pressed cancel button */
            return;
          }

          // Call API, get new collection id back, then navigate to it
          this.loading = true;

          let data = {
            ids: ids.join(","),
          };
          if (description) {
            data["description"] = description;
          }

          collectionAggregate({ data })
            .then((response) => {
              this.loading = false;
              if (response.ok) {
                return response.json();
              }
              swal("Oops", E_SERVER_ERROR, "error");
            })
            .then((json) => {
              let newid = json["newid"];
              if (newid) {
                window.open(json["newid"] + "/browse", "_self");
              } else {
                swal("Oops", E_SERVER_ERROR, "error");
              }
            })
            .catch(() => {
              this.loading = false;
              swal("Oops", E_SERVER_ERROR, "error");
            });
        });
      }
    },
    summary: function () {
      let target_collection = null;

      if (this.selected_collections.length == 1) {
        target_collection = this.selected_collections[0];
      } else if (this.collections.length == 1) {
        target_collection = this.collections[0].pk;
      } else {
        swal(
          "Error",
          "Function requires exactly one collection to be selected.",
          "error",
        );
        return;
      }

      window.open(`${target_collection}/summary/`, "_blank").focus();
    },
    collection_click_handler: function (id) {
      let self = this;
      let idx = self.selected_collections.indexOf(id);
      let target = document.getElementById(id);

      if (idx < 0) {
        self.selected_collections.push(id);
        if (target) target.classList.add("collection-selected");
      } else {
        self.selected_collections.splice(idx, 1);
        if (target) target.classList.remove("collection-selected");
      }
    },
    formatDate: function (datetime) {
      return formatClientTimestamp(datetime);
    },
  },
});
</script>
