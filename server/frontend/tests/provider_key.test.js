import Vue from "vue";
import { fireEvent, render } from "@testing-library/vue";
import ProviderKey from "../src/components/ProviderKey.vue";
import { whoAmI } from "../src/bugzilla_api.js";

// This line will mock all calls to functions in ../src/bugzilla_api.js
jest.mock("../src/bugzilla_api.js");

// Mocking localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

afterEach(() => {
  localStorage.clear();
  jest.resetAllMocks();
});

test("providerKey displays an empty input when there isn't an API key in the localStorage", async () => {
  // There is an APIKey in the storage but not for the provider 1
  localStorage.setItem("provider-2-api-key", "mysuperapikey");
  const { getByPlaceholderText } = await render(ProviderKey, {
    props: {
      providerId: 1,
      providerHostname: "myprovider.com",
    },
  });

  const input = getByPlaceholderText("API key...");
  expect(input.value).toBe("");
});

test("providerKey displays a filled input when there is an API key in the localStorage", async () => {
  localStorage.setItem("provider-1-api-key", "mysuperapikey");
  const { getByPlaceholderText } = await render(ProviderKey, {
    props: {
      providerId: 1,
      providerHostname: "myprovider.com",
    },
  });

  const input = getByPlaceholderText("API key...");
  expect(input.value).toBe("mysuperapikey");
});

test("providerKey can add a new API key in the localStorage", async () => {
  whoAmI.mockResolvedValue({ real_name: "Bob Bob", nick: "bobby" });
  const { getByText, getByPlaceholderText } = await render(ProviderKey, {
    props: {
      providerId: 1,
      providerHostname: "myprovider.com",
    },
  });
  const input = getByPlaceholderText("API key...");
  expect(input.value).toBe("");

  const key = "mysuperapikey";
  // Typing in the input and saving
  await fireEvent.update(input, key);
  await fireEvent.click(getByText("Save"));

  await Vue.nextTick();
  expect(whoAmI).toHaveBeenCalledTimes(1);
  expect(whoAmI).toHaveBeenCalledWith({
    hostname: "myprovider.com",
    key,
  });
  expect(input.value).toBe(key);
  expect(localStorage.getItem("provider-1-api-key")).toBe(key);
  getByText(/Welcome /);
});

test("providerKey can update an existing API key in the localStorage", async () => {
  localStorage.setItem("provider-1-api-key", "mysuperapikey");
  whoAmI.mockResolvedValue({ real_name: "Bob", nick: "Bobby" });
  const { getByText, getByPlaceholderText } = await render(ProviderKey, {
    props: {
      providerId: 1,
      providerHostname: "myprovider.com",
    },
  });
  const input = getByPlaceholderText("API key...");
  expect(input.value).toBe("mysuperapikey");

  const key = "myotherapikey";
  // Typing in the input and saving
  await fireEvent.update(input, key);
  await fireEvent.click(getByText("Save"));

  await Vue.nextTick();
  expect(whoAmI).toHaveBeenCalledTimes(1);
  expect(whoAmI).toHaveBeenCalledWith({
    hostname: "myprovider.com",
    key,
  });
  expect(input.value).toBe(key);
  expect(localStorage.getItem("provider-1-api-key")).toBe(key);
  getByText(/Welcome /);
});

test("providerKey displays an error if the entered API key is invalid", async () => {
  whoAmI.mockImplementation(() => {
    throw new Error();
  });
  const { getByText, getByPlaceholderText } = await render(ProviderKey, {
    props: {
      providerId: 1,
      providerHostname: "myprovider.com",
    },
  });
  const input = getByPlaceholderText("API key...");
  expect(input.value).toBe("");

  const key = "mysuperapikey";
  // Typing in the input and saving
  await fireEvent.update(input, key);
  await fireEvent.click(getByText("Save"));

  await Vue.nextTick();
  expect(whoAmI).toHaveBeenCalledTimes(1);
  expect(whoAmI).toHaveBeenCalledWith({
    hostname: "myprovider.com",
    key,
  });
  expect(input.value).toBe(key);
  expect(localStorage.getItem("provider-1-api-key")).toBeNull();
  getByText(
    /Your API key wasn't saved because an error occurred while contacting/
  );
});

test("providerKey can remove an existing API key from the localStorage", async () => {
  localStorage.setItem("provider-1-api-key", "mysuperapikey");
  const { getByTitle, getByPlaceholderText } = await render(ProviderKey, {
    props: {
      providerId: 1,
      providerHostname: "myprovider.com",
    },
  });
  const input = getByPlaceholderText("API key...");
  expect(input.value).toBe("mysuperapikey");

  await fireEvent.click(getByTitle("Remove key"));

  expect(input.value).toBe("");
  expect(localStorage.getItem("provider-1-api-key")).toBeNull();
});
