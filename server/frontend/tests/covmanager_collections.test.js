import { render } from "@testing-library/vue";
import { nextTick } from "vue";
import { collectionList } from "../src/api";
import Collections from "../src/components/Covmanager/Collections.vue";
import { collectionData } from "./fixtures";

// This line will mock all calls to functions in ../src/api.js
jest.mock("../src/api.js");

test("renders collection table successfully", async () => {
  collectionList.mockResolvedValue(collectionData);

  const wrapper = render(Collections);

  // Wait for the next tick to ensure all promises are resolved
  await nextTick();

  // Check if the API was called
  expect(collectionList).toHaveBeenCalledTimes(1);

  // Check if the table is rendered
  const table = wrapper.container.querySelector("table");
  expect(table).not.toBe(undefined);

  // Check if the correct number of rows are rendered
  const rows = table.querySelectorAll("tbody tr");
  expect(rows.length).toBe(2);

  // Verify the content of the first row
  const firstRowCells = rows[0].querySelectorAll("td");

  expect(firstRowCells[0].textContent).toBe("1");
  expect(firstRowCells[2].textContent).toBe("cov-example");
  expect(firstRowCells[3].textContent).toBe(
    "adab95a85e138f792631f19d939dfd1102197acc",
  );
  expect(firstRowCells[4].textContent).toBe("main");
  expect(firstRowCells[5].textContent).toBe("");
  expect(firstRowCells[6].textContent).toBe("update");

  //
  const firstRow = wrapper.container.querySelector("tbody tr");
  await firstRow.click();

  await nextTick();

  // Check if the row is selected
  expect(firstRow.classList).toContain("collection-selected");
});
