<template>
  <div>
    <input
      :id="inputId"
      v-model="value"
      class="form-control dropdown-toggle"
      maxlength="1023"
      :name="inputName"
      type="text"
      data-toggle="dropdown"
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
            @click="updateValue(user.email)"
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
import { defineComponent, onMounted, ref, watch } from "vue";
import * as bugzillaApi from "../../bugzilla_api";

export default defineComponent({
  name: "UserDropdown",
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

  setup(props, { emit }) {
    const value = ref("");
    const suggestedUsers = ref(null);
    const loading = ref(false);
    let debouncedFetch = null;

    const updateValue = (newValue) => {
      if (props.multiple) {
        const users = value.value.split(",");
        // Removing search string
        users.pop();
        if (users.indexOf(newValue) === -1) {
          // Adding user email
          users.push(newValue);
        }
        value.value = users.join(",");
      } else {
        value.value = newValue;
      }
    };

    const fetchSuggestedUsers = async () => {
      suggestedUsers.value = null;
      loading.value = true;
      try {
        const data = await bugzillaApi.fetchSuggestedUsers({
          hostname: props.provider.hostname,
          params: { match: value.value.split(",").pop(), limit: 100 },
          headers: { "X-BUGZILLA-API-KEY": props.bugzillaToken },
        });
        suggestedUsers.value = data.users;
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      value.value = props.initialValue;
      debouncedFetch = _debounce(fetchSuggestedUsers, 1000);
    });

    watch(
      () => props.initialValue,
      (newVal) => {
        value.value = newVal;
      },
    );

    watch(
      () => value.value,
      (newVal) => {
        emit("update-value", newVal);
        if (newVal !== props.initialValue) {
          suggestedUsers.value = null;
          loading.value = true;
          debouncedFetch();
        }
      },
    );

    return {
      value,
      suggestedUsers,
      loading,
      updateValue,
    };
  },
});
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
