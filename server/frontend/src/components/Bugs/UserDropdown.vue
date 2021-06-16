<template>
  <div>
    <input
      :id="inputId"
      class="form-control dropdown-toggle"
      maxlength="1023"
      :name="inputName"
      type="text"
      data-toggle="dropdown"
      v-model="value"
    />
    <ul class="dropdown dropdown-menu" aria-labelledby="inputId">
      <template v-if="loading">
        <li>
          <option disabled>Loading user suggestions...</option>
        </li>
      </template>
      <template v-else>
        <template v-if="!suggestedUsers">
          <li>
            <option disabled>Type something to load user suggestions</option>
          </li>
        </template>
        <template v-else-if="!suggestedUsers.length">
          <li>
            <option disabled>No user matched your search</option>
          </li>
        </template>
        <template v-else>
          <li
            v-for="user in suggestedUsers"
            :key="user.id"
            v-on:click="updateValue(user.email)"
          >
            <div>
              <img
                class="user-img"
                :src="user.gravatar"
                alt="test"
                width="25px"
                height="25px"
              />
              <span class="user-info">
                {{ user.real_name ? user.real_name + " ― " : "" }}
                <strong>{{ user.email }}</strong>
              </span>
            </div>
          </li>
        </template>
      </template>
    </ul>
  </div>
</template>

<script>
import _debounce from "lodash/debounce";
import * as bugzillaApi from "../../bugzilla_api";

export default {
  props: {
    inputId: {
      type: String,
      required: true,
    },
    inputName: {
      type: String,
      required: true,
    },
    provider: {
      type: Object,
      required: true,
    },
    bugzillaToken: {
      type: String,
      required: true,
    },
    initialValue: {
      type: String,
      required: true,
    },
    multiple: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  data: () => ({
    value: "",
    suggestedUsers: null,
    loading: false,
  }),
  mounted() {
    this.value = this.initialValue;
    this.debouncedFetch = _debounce(this.fetchSuggestedUsers, 1000);
  },
  methods: {
    updateValue(value) {
      if (this.multiple) {
        const users = this.value.split(",");
        // Removing search string
        users.pop();
        if (users.indexOf(value) == -1) {
          // Adding user email
          users.push(value);
        }
        this.value = users.join(",");
      } else {
        this.value = value;
      }
    },
    async fetchSuggestedUsers() {
      this.suggestedUsers = null;
      this.loading = true;
      try {
        const data = await bugzillaApi.fetchSuggestedUsers({
          hostname: this.provider.hostname,
          params: { match: this.value.split(",").pop(), limit: 100 },
          headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
        });
        this.suggestedUsers = data.users;
      } finally {
        this.loading = false;
      }
    },
  },
  watch: {
    initialValue: function () {
      this.value = this.initialValue;
    },
    value: function () {
      this.$emit("update-value", this.value);
      if (this.value !== this.initialValue) {
        this.suggestedUsers = null;
        this.loading = true;
        this.debouncedFetch();
      }
    },
  },
};
</script>

<style scoped>
.dropdown {
  margin-left: 1.5rem;
  padding: 1rem;
  width: max-content;
  overflow-y: auto;
  max-height: 400px;
}
.dropdown > li {
  padding-top: 0.5rem;
  cursor: pointer;
}
.dropdown > li:first-child {
  padding-top: 0rem;
}
.user-img {
  border-radius: 25%;
}
.user-info {
  vertical-align: middle;
  margin-left: 0.75rem;
}
</style>
