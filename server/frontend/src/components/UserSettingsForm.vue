<template>
  <div class="form-group">
    <label for="defaultToolsFilter">Default Tools Filter</label>
    <multiselect
      id="defaultToolsFilter"
      v-model="defaultToolsFilter"
      :options="defaultToolsOptions"
      :track-by="'code'"
      :label="'name'"
      :multiple="true"
      placeholder="Select tools"
    />
    <strong v-if="formErrors.defaultToolsFilter" class="error-message">
      {{ formErrors.defaultToolsFilter.join(", ") }}
    </strong>

    <!-- Use hidden field, since `multiselect` component does not render in a format that can be accepted by django -->
    <div v-for="(option, index) in defaultToolsFilter" :key="index">
      <input type="hidden" name="defaultToolsFilter" :value="option.code" />
    </div>
  </div>

  <div class="row">
    <div class="form-group col-md-6">
      <label for="defaultProvider">Default Provider</label>
      <select
        id="defaultProviderId"
        v-model="defaultProvider"
        name="defaultProviderId"
        class="form-control"
      >
        <option
          v-for="provider in defaultProviderOptions"
          :key="provider.id"
          :value="provider.id"
        >
          {{ provider.name }}
        </option>
      </select>
      <strong v-if="formErrors.defaultProviderId" class="error-message">
        {{ formErrors.defaultProviderId.join(", ") }}
      </strong>
    </div>

    <div class="form-group col-md-6">
      <label for="defaultTemplate">Default Template</label>
      <select
        id="defaultTemplateId"
        v-model="defaultTemplate"
        name="defaultTemplateId"
        class="form-control"
      >
        <option
          v-for="template in defaultTemplateOptions"
          :key="template.id"
          :value="template.id"
        >
          {{ template.name }}
        </option>
      </select>

      <strong v-if="formErrors.defaultTemplateId" class="error-message">
        {{ formErrors.defaultTemplateId.join(", ") }}
      </strong>
    </div>
  </div>

  <div class="form-group">
    <label for="email">Email</label>
    <input
      id="email"
      v-model="email"
      type="email"
      name="email"
      class="form-control"
      placeholder="Enter your email"
      :disabled="!allowEmailEdit"
    />

    <strong v-if="formErrors.email" class="error-message">
      {{ formErrors.email.join(", ") }}
    </strong>
  </div>

  <div class="form-group">
    <label for="subscribeNotifications">Subscribe to Notifications</label>
    <multiselect
      id="subscribeNotifications"
      v-model="subscribeNotifications"
      :options="subscribeNotificationOptions"
      :track-by="'code'"
      :label="'name'"
      :multiple="true"
      placeholder="Select notifications"
    />

    <!-- Generate hidden inputs for all notification options -->
    <div
      v-for="notification in subscribeNotifications"
      :key="notification.code"
    >
      <input type="hidden" :name="notification.code" :value="'on'" />
    </div>
  </div>

  <div class="form-group">
    <button type="submit" class="btn btn-danger">Save settings</button>
  </div>
</template>

<script>
import Multiselect from "vue-multiselect";

export default {
  name: "UserSettingsForm",
  components: {
    Multiselect,
  },
  props: {
    defaultToolsOptions: {
      type: Array,
      default: () => [],
    },
    defaultToolsSelected: {
      type: Array,
      default: () => [],
    },
    defaultProviderOptions: {
      type: Array,
      default: () => [],
    },
    defaultProviderSelected: {
      type: [String, Number],
      default: null,
    },
    defaultTemplateOptions: {
      type: Array,
      default: () => [],
    },
    defaultTemplateSelected: {
      type: [String, Number],
      default: null,
    },
    initialEmail: {
      type: String,
      default: "",
    },
    allowEmailEdit: {
      type: Boolean,
      default: true,
    },
    subscribeNotificationOptions: {
      type: Array,
      default: () => [],
    },
    formErrors: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      defaultToolsFilter: [...this.defaultToolsSelected],
      defaultProvider: this.defaultProviderSelected,
      defaultTemplate: this.defaultTemplateSelected,
      email: this.initialEmail,
      subscribeNotifications: this.subscribeNotificationOptions.filter(
        (option) => option.selected,
      ),
    };
  },
};
</script>

<style src="vue-multiselect/dist/vue-multiselect.css"></style>
<style scoped>
.form-group {
  margin-bottom: 20px;
}

.form-control {
  width: 100%;
}

.error-message {
  color: #d9534f;
}
</style>
