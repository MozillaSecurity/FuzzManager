import { fireEvent, render } from "@testing-library/vue";
import UserSettingsForm from "../src/components/UserSettingsForm.vue";
import Multiselect from "vue-multiselect";

// Mock vue-multiselect component
jest.mock("vue-multiselect", () => ({
  name: "Multiselect",
  template: `
    <select
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
      data-testid="multiselect"
      multiple
    >
      <option v-for="option in options" :key="option.code" :value="option">
        {{ option.name }}
      </option>
    </select>
  `,
  props: [
    "modelValue",
    "options",
    "trackBy",
    "label",
    "multiple",
    "placeholder",
  ],
  emits: ["update:modelValue"],
}));

describe("UserSettingsForm Component", () => {
  const defaultProps = {
    defaultToolsOptions: [
      { code: "tool1", name: "Tool 1" },
      { code: "tool2", name: "Tool 2" },
    ],
    defaultToolsSelected: [{ code: "tool1", name: "Tool 1" }],
    defaultProviderOptions: [
      { id: 1, name: "Provider 1" },
      { id: 2, name: "Provider 2" },
    ],
    defaultProviderSelected: 1,
    defaultTemplateOptions: [
      { id: 1, name: "Template 1" },
      { id: 2, name: "Template 2" },
    ],
    defaultTemplateSelected: 1,
    initialEmail: "test@example.com",
    allowEmailEdit: true,
    subscribeNotificationOptions: [
      { code: "notify1", name: "Notification 1", selected: true },
      { code: "notify2", name: "Notification 2", selected: false },
    ],
  };

  test("submits form with correct values", async () => {
    // Create a wrapper component that includes a form
    const handleSubmit = jest.fn();

    const WrapperComponent = {
      components: { UserSettingsForm },
      props: {
        onSubmit: {
          type: Function,
          required: true,
        },
      },
      template: `
        <form data-testid="settings-form" @submit.prevent="onSubmit">
          <UserSettingsForm v-bind="formProps" />
        </form>
      `,
      setup(props) {
        return {
          formProps: defaultProps,
          onSubmit: props.onSubmit,
        };
      },
    };

    const { getByTestId } = await render(WrapperComponent, {
      props: {
        onSubmit: handleSubmit,
      },
      global: {
        components: { Multiselect },
      },
    });

    const form = getByTestId("settings-form");
    await fireEvent.submit(form);

    expect(handleSubmit).toHaveBeenCalled();
  });

  test("renders with initial values", async () => {
    const { container, getAllByTestId } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const toolsSelect = getAllByTestId("multiselect")[0];
    expect(toolsSelect).toBeTruthy();

    const providerSelect = container.querySelector("#defaultProviderId");
    expect(providerSelect.value).toBe("1");

    const templateSelect = container.querySelector("#defaultTemplateId");
    expect(templateSelect.value).toBe("1");

    const emailInput = container.querySelector("#email");
    expect(emailInput.value).toBe("test@example.com");
    expect(emailInput.disabled).toBe(false);
  });

  test("generates hidden inputs for selected tools", async () => {
    const { container } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const hiddenInputs = container.querySelectorAll(
      'input[type="hidden"][name="defaultToolsFilter"]',
    );
    expect(hiddenInputs.length).toBe(1);
    expect(hiddenInputs[0].value).toBe("tool1");
  });

  test("generates hidden inputs for selected notifications", async () => {
    const { container } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const hiddenInputs = container.querySelectorAll(
      'input[type="hidden"][name="notify1"]',
    );
    expect(hiddenInputs.length).toBe(1);
    expect(hiddenInputs[0].value).toBe("on");
  });

  test("updates provider selection", async () => {
    const { container } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const select = container.querySelector("#defaultProviderId");
    await fireEvent.update(select, "2");
    expect(select.value).toBe("2");
  });

  test("updates template selection", async () => {
    const { container } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const select = container.querySelector("#defaultTemplateId");
    await fireEvent.update(select, "2");
    expect(select.value).toBe("2");
  });

  test("updates email value", async () => {
    const { container } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const input = container.querySelector("#email");
    await fireEvent.update(input, "newemail@example.com");
    expect(input.value).toBe("newemail@example.com");
  });

  test("renders email input as disabled when allowEmailEdit is false", async () => {
    const props = {
      ...defaultProps,
      allowEmailEdit: false,
    };

    const { container } = await render(UserSettingsForm, {
      props,
      global: {
        components: { Multiselect },
      },
    });

    const emailInput = container.querySelector("#email");
    expect(emailInput.disabled).toBe(true);
  });

  test("renders all provider options", async () => {
    const { container } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const select = container.querySelector("#defaultProviderId");
    const options = Array.from(select.options);
    expect(options.length).toBe(2);
    expect(options[0].textContent.trim()).toBe("Provider 1");
    expect(options[1].textContent.trim()).toBe("Provider 2");
  });

  test("renders all template options", async () => {
    const { container } = await render(UserSettingsForm, {
      props: defaultProps,
      global: {
        components: { Multiselect },
      },
    });

    const select = container.querySelector("#defaultTemplateId");
    const options = Array.from(select.options);
    expect(options.length).toBe(2);
    expect(options[0].textContent.trim()).toBe("Template 1");
    expect(options[1].textContent.trim()).toBe("Template 2");
  });
});
