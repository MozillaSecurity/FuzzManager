import { nextTick } from "vue";
import { fireEvent, render } from "@testing-library/vue";
import Inbox from "../src/components/Notifications/Inbox.vue";
import InaccessibleBug from "../src/components/Notifications/InaccessibleBug.vue";
import {
  dismissAllNotifications,
  dismissNotification,
  listUnreadNotifications,
} from "../src/api.js";
import {
  emptyNotifications,
  inaccessibleBugNotification,
  unreadNotifications,
} from "./fixtures.js";
// This line will mock all calls to functions in ../src/api.js
jest.mock("../src/api.js");

afterEach(jest.resetAllMocks);

test("inbox displays an error if notification fetching failed", async () => {
  listUnreadNotifications.mockImplementation(() => {
    throw new Error();
  });
  const { findByText } = await render(Inbox);

  expect(listUnreadNotifications).toHaveBeenCalledTimes(1);
  expect(listUnreadNotifications).toHaveBeenCalledWith({
    limit: 25,
    offset: "0",
  });
  findByText((content) =>
    content.startsWith(
      "An error occurred while fetching unread notifications: ",
    ),
  );
});

test("inbox has no notifications", async () => {
  listUnreadNotifications.mockResolvedValue(emptyNotifications);
  const { findByText } = await render(Inbox);

  expect(listUnreadNotifications).toHaveBeenCalledTimes(1);
  expect(listUnreadNotifications).toHaveBeenCalledWith({
    limit: 25,
    offset: "0",
  });
  findByText("No unread notification.");
});

test("inbox has two unread notifications", async () => {
  listUnreadNotifications.mockResolvedValue(unreadNotifications);
  const { findByText } = await render(Inbox);

  expect(listUnreadNotifications).toHaveBeenCalledTimes(1);
  expect(listUnreadNotifications).toHaveBeenCalledWith({
    limit: 25,
    offset: "0",
  });
  findByText("Inaccessible bug");
  findByText(unreadNotifications.results[0].description);
});

test("inbox displays a functional button to dismiss all notifications", async () => {
  listUnreadNotifications.mockResolvedValue(unreadNotifications);
  dismissAllNotifications.mockResolvedValue();
  const { findByText, queryByText } = await render(Inbox);

  findByText("Inaccessible bug");

  fireEvent.click(await findByText("Dismiss all notifications"));

  expect(dismissAllNotifications).toHaveBeenCalledTimes(1);
  await findByText("No unread notification.");
  expect(queryByText("Inaccessible bug")).toBeNull();
  expect(queryByText("Dismiss all notifications")).toBeNull();
});

test("inbox displays an error if dismissing all notifications failed", async () => {
  listUnreadNotifications.mockResolvedValue(unreadNotifications);
  dismissAllNotifications.mockImplementation(() => {
    throw new Error();
  });
  const { findByText } = await render(Inbox);

  findByText("Inaccessible bug");

  fireEvent.click(await findByText("Dismiss all notifications"));

  expect(dismissAllNotifications).toHaveBeenCalledTimes(1);
  // Notifications are still here
  findByText("Inaccessible bug");
  // An error is displayed
  findByText((content) =>
    content.startsWith(
      "An error occurred while marking all notifications as read: ",
    ),
  );
});

test("inbox intercepts simple dismiss event from child component", async () => {
  listUnreadNotifications.mockResolvedValue(unreadNotifications);
  dismissNotification.mockResolvedValue();
  const { findByText, queryByText, findAllByTitle } = await render(Inbox);

  findByText("Inaccessible bug");

  (await findAllByTitle("Dismiss")).forEach((b) => fireEvent.click(b));

  expect(dismissNotification).toHaveBeenCalledTimes(2);
  await findByText("No unread notification.");
  expect(queryByText("Inaccessible bug")).toBeNull();
});

test("inbox displays an error if dismissing one notification failed", async () => {
  listUnreadNotifications.mockResolvedValue(unreadNotifications);
  dismissNotification.mockImplementation(() => {
    throw new Error();
  });
  const { findByText, findAllByTitle } = await render(Inbox);

  findByText("Inaccessible bug");

  (await findAllByTitle("Dismiss")).forEach((b) => fireEvent.click(b));

  expect(dismissNotification).toHaveBeenCalledTimes(2);
  // Notifications are still here
  findByText("Inaccessible bug");
  // An error is displayed
  findByText((content) =>
    content.startsWith(
      "An error occurred while marking notification 2 as read: ",
    ),
  );
});

test("inaccessibleBug renders a 'View external bug' button with a redirection", async () => {
  const { getByText } = await render(InaccessibleBug, {
    props: { notification: inaccessibleBugNotification },
  });

  getByText("Inaccessible bug");
  const buttonLink = getByText("View external bug");
  expect(buttonLink).toHaveProperty(
    "href",
    inaccessibleBugNotification.external_bug_url,
  );
  expect(buttonLink).toHaveProperty("target", "_blank");
});

test("inaccessibleBug emits a 'remove-notification' event for a successful dismiss", async () => {
  const { emitted, getByText, getByTitle } = await render(InaccessibleBug, {
    props: { notification: inaccessibleBugNotification },
  });

  getByText("Inaccessible bug");
  await fireEvent.click(getByTitle("Dismiss"));
  expect(emitted()["remove-notification"]).toBeTruthy();
  expect(emitted()["remove-notification"].length).toBe(1);
  expect(emitted()["remove-notification"][0]).toEqual([
    inaccessibleBugNotification.id,
  ]);
});

test("inaccessibleBug emits a 'update-dismiss-error' event for a failed dismiss", async () => {
  dismissNotification.mockImplementation(() => {
    throw new Error();
  });
  const { emitted, getByText, getByTitle } = await render(InaccessibleBug, {
    props: { notification: inaccessibleBugNotification },
  });

  getByText("Inaccessible bug");
  await fireEvent.click(getByTitle("Dismiss"));
  await nextTick();
  expect(emitted()["update-dismiss-error"]).toBeTruthy();
  expect(emitted()["update-dismiss-error"].length).toBe(1);
  expect(emitted()["update-dismiss-error"][0]).toEqual([
    `An error occurred while marking notification ${inaccessibleBugNotification.id} as read: Error`,
  ]);
});
