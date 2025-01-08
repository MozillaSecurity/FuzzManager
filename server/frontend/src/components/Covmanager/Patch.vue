<template>
  <div id="main" class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-clipboard-data"></i> Coverage Collection Browser
    </div>
    <div class="panel-body">
      <div class="panel panel-default" style="float: left">
        <div class="panel-heading">
          <i class="bi bi-file-code"></i> Patch Information
        </div>
        <div class="panel-body">
          <div>
            <label>Repository:</label
            ><input
              v-model="repository_search"
              type="text"
              class="form-control bi bi-archive-fill"
              @focus="repository_suggestions_enabled = true"
              @blur="repository_suggestions_enabled = false"
              @keyup.enter="take_top_suggestion"
            />
            <div v-show="repository_suggestions_enabled">
              <div
                v-for="name in repository_suggestions"
                :key="name"
                @mousedown="set_repository(name)"
              >
                {{ name }}
              </div>
            </div>
          </div>
          <div>
            <label>Patch Revision:</label
            ><input v-model="patch_revision" type="text" class="form-control" />
          </div>
        </div>
      </div>

      <div class="panel panel-default" style="float: left">
        <div class="panel-heading">
          <i class="bi bi-funnel-fill"></i> Target Collections
        </div>
        <div class="panel-body">
          <div>
            <span
              ><b>{{ collections_count }}</b> collections selected for
              analysis.</span
            >
            <button
              class="btn btn-default"
              :disabled="!analysis_enabled"
              @click="run_analysis"
            >
              Run Analysis
            </button>
          </div>
        </div>
      </div>

      <div class="panel panel-default" style="float: right">
        <div class="panel-heading">
          <i class="bi bi-lightning-charge-fill"></i> Options
        </div>
        <div class="panel-body">
          <input id="checkbox" v-model="prepatch" type="checkbox" />
          <label for="checkbox">Prepatch Analysis (Experimental)</label>
        </div>
      </div>
    </div>

    <template v-if="loading">
      <div class="loader"></div>
    </template>
    <template v-else-if="analysis_results">
      <table class="table table-condensed table-hover table-db">
        <thead>
          <tr>
            <th style="width: 50%">Collection ID</th>
            <th>Tools</th>
            <th>Analysis Status</th>
            <th>Details</th>
            <th>Links</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="analysis_result in analysis_results"
            :key="analysis_result.collection.id"
          >
            <td>{{ analysis_result.collection.id }}</td>
            <td>{{ analysis_result.collection.tools }}</td>
            <td>
              <div v-if="analysis_result.status">Success</div>
              <div v-else>Failed</div>
            </td>
            <td>
              <div v-for="detail in analysis_result.details" :key="detail">
                {{ detail }}
              </div>
            </td>
            <td>
              <div
                v-for="(link, filename) in analysis_result.links"
                :key="filename"
              >
                <a :href="link" target="_blank">{{ filename }}</a>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>
<script>
import swal from "sweetalert";
import { defineComponent } from "vue";
import "../../public/css/covmanager.css";

import _ from "lodash";
import { E_SERVER_ERROR } from "../../helpers";
import { HashParamManager } from "../../params";

let APIURLS = {
  repository_search: "/covmanager/repositories/search/api/",
  collections: "/covmanager/collections/api/",
  collections_patch_api: "/covmanager/collections/patch/" + "api/",
  browse: "/covmanager/collections/0/browse/", // TODO: It would be nice to solve this more cleanly
};

let pmanager = new HashParamManager();

export default defineComponent({
  data() {
    return {
      repository: null,
      repository_search: "",
      repository_suggestions: [],
      repository_suggestions_enabled: false,
      patch_revision: null,
      collection_ids: [],
      collections: [],
      prepatch: false,
      analysis_results: [],
      loading: false,
    };
  },
  computed: {
    collections_count() {
      return this.collection_ids.length;
    },
    analysis_enabled() {
      return (
        this.collection_ids.length > 0 &&
        this.patch_revision &&
        this.repository != null
      );
    },
  },
  watch: {
    repository_search: "update_repository_search",
  },
  created() {
    let self = this;
    pmanager.forEach(function (k, v) {
      // Try to guess the repository from the search query
      k = k.replace(/__contains$/, "");
      k = k.replace(/__name$/, "");

      if (k == "repository") {
        self.repository_search = v;
      }
    });

    let ids = pmanager.get_value("ids", "");
    if (ids != "") {
      self.collection_ids = ids.split(",");
    } else {
      swal("Oops", "Patch analysis requires an ID list from search", "error");
    }
  },
  methods: {
    run_analysis() {
      if (this.collection_ids) {
        this.fetch_collections();
      }
    },
    update_repository_search: _.throttle(function () {
      fetch(APIURLS.repository_search + "?name=" + this.repository_search, {
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
          this.repository_suggestions = json["results"];

          if (
            this.repository_suggestions.indexOf(this.repository_search) >= 0
          ) {
            this.repository = this.repository_search;
          } else {
            this.repository = null;
          }
        });
    }, 500),
    set_repository(name) {
      this.repository_suggestions = [];
      this.repository_suggestions_enabled = false;
      this.repository_search = name;
      this.repository = name;
    },
    take_top_suggestion() {
      if (this.repository_suggestions?.length) {
        this.set_repository(this.repository_suggestions[0]);
      }
    },
    fetch_collections: _.throttle(function () {
      this.loading = true;

      fetch(
        APIURLS.collections +
          "?ids=" +
          this.collection_ids.join(",") +
          "&repository__name=" +
          this.repository,
        {
          method: "GET",
          credentials: "same-origin",
        },
      )
        .then((response) => {
          if (response.ok) {
            return response.json();
          }
          swal("Oops", E_SERVER_ERROR, "error");
        })
        .then((json) => {
          this.collections = json["results"];
          let analysis_results = [];

          let self = this;
          const requests = this.collections
            .reverse()
            .map(function (collection) {
              return fetch(
                APIURLS.collections_patch_api +
                  collection.id +
                  "/" +
                  self.patch_revision +
                  (self.prepatch ? "?prepatch=1" : ""),
                {
                  method: "GET",
                  credentials: "same-origin",
                },
              )
                .then((response) => {
                  if (response.ok) {
                    return response.json();
                  }
                  swal("Oops", E_SERVER_ERROR, "error");
                })
                .then((json) => {
                  if (!json) {
                    return;
                  }

                  let analysis_result = {
                    collection: collection,
                    status: true,
                    details: [],
                    links: {},
                  };

                  if ("results" in json) {
                    analysis_result.details.push(
                      json["percentage_missed"] + " %",
                    );

                    for (const element of json["results"]) {
                      let result = element;
                      if (result["missed"]) {
                        let link = APIURLS.browse.replace(
                          "/0/",
                          "/" + collection.id + "/",
                        );
                        let highlight_lines = result["missed"];
                        link += "#p=" + result["filename"];
                        link += "&s=" + highlight_lines[0];
                        link += "&hl=" + highlight_lines.join(",");
                        analysis_result.links[result["filename"]] = link;
                      }
                    }
                  } else if ("error" in json) {
                    analysis_result.status = false;
                    analysis_result.details.push(json["error"]);
                    if ("filename" in json) {
                      analysis_result.details.push(json["filename"]);
                    }
                  }

                  analysis_results.push(analysis_result);
                });
            });

          Promise.all(requests).then(() => {
            this.analysis_results = analysis_results;
            this.loading = false;
          });
        });
    }, 500),
  },
});
</script>
