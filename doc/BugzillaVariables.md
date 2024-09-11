# Bugzilla - Handlebars.js variables
In the Bugzilla Bug and Comment publication forms, we use [Handlebars.js](https://handlebarsjs.com/) to dynamically render variables in the following fields:
- For bug publication: ***Custom fields*** & ***Description***.
- For comment publication: ***Comment***.

## How to use Handlebars variables
To use a Handlebars variable (as the ones listed below), you have to surround your variable with double curly brackets:
```
{{myvariable}}
```

By default, Handlebars will HTML escape the text to be rendered. If you want to render your variable as unescaped HTML, you can surround it with triple curly brackets or append a `&` character before its name:
```
{{{myvariable}}}
{{&myvariable}}
```

### Example
Presuming that `var` is a Handlebars variable and that its stored value is:
```
<h1>
  My beautiful variable
</h1>
```

The following **input**:
```
{{var}}
---
{{{var}}}
---
{{&var}}
---
{{=<% %>=}}
{{var}}
<%={{ }}=%>
```

Will render as this **output**:
```
&lt;h1&gt;
  My beautiful variable
&lt;&#x2F;h1&gt;
---
<h1>
  My beautiful variable
</h1>
---
<h1>
  My beautiful variable
</h1>
---
{{var}}
```

> To learn more about Handlebars variables, please read the [documentation](https://handlebarsjs.com/guide/).

## Bug - Available variables
> *Note: All fields are immutable unless otherwise specified.*

### In ***Description*** field
- `summary`
    - Renders the text displayed in **Summary** `<input/>`
    - Value is editable through the **Summary** form field
- `shortsig` Renders the **ReportEntry** `shortSignature` attribute
- `product` Renders the **ReportEntry** `product` attribute
- `version` Renders the **ReportEntry** `product_version` attribute if set, else display the following hint: `"(Version not available)"`
- `args` Renders the **ReportEntry** `args` attribute as JSON 
- `os` Render the **ReportEntry** `os` attribute
- `platform` Renders the **ReportEntry** `platform` attribute
- `client` Renders the **ReportEntry** `client` attribute
- `testcase`
    - If the **ReportEntry** `testcase` attribute is empty, it displays the following hint: `"(Test not available)"`
    - Else if the `testcase` content length is greater than 2048 characters or contains binary content, it displays the following hint: `"See attachment."`
    - Else, it simply renders the `testcase` content
    - Value is editable through the **Content** field located in the **Testcase form section**
- `reportdata`
    - If the **ReportEntry** `rawReportData` attribute is set, it renders its content
    - Else, it renders the **ReportEntry** `rawStderr` attribute content
    - Value is editable through the **Content** field located in the **Report data form section**
- `reportdataattached`
    - If the report data is to be attached to the bug, it displays the following hint: `"For detailed report information, see attachment."`
    - Else, it displays: `"(Report data not available)"`
    - Value is editable through the **Do not attach report data** checkbox located in the **Report data form section**
- `metadata*`
    - The `*` is to be replaced with a metadata name
    - If the metadata is available in **ReportEntry** `metadata` attribute as an object key, it renders the value of `ReportEntry.metadata[name]`
    - Else, it renders the following hint: `"(metadata{name} not available)"`
    - **e.g:** With `ReportEntry.metadata = {"path": "test/path"}`, `{{metadatapath}}` renders to `"test/path"` and `{{metadataunknown}}` renders to `"(metadataunknown not available)"`

### In ***Custom fields*** field
- `metadata*`
    - The `*` is to be replaced with a metadata name
    - If the metadata is available in **ReportEntry** `metadata` attribute as an object key, it renders the value of `ReportEntry.metadata[name]`
    - Else, it renders the following hint: `"(metadata{name} not available)"`
    - **e.g:** With `ReportEntry.metadata = {"path": "test/path"}`, `{{metadatapath}}` renders to `"test/path"` and `{{metadataunknown}}` renders to `"(metadataunknown not available)"`

## Comment - Available variables
> *Note: All fields are immutable unless otherwise specified.*

### In ***Comment*** field
- `summary` Renders the **BugzillaTemplate** `summary` attribute if set, else renders the **ReportEntry** `shortSignature` attribute
- `shortsig` Renders the **ReportEntry** `shortSignature` attribute
- `product` Renders the **ReportEntry** `product` attribute
- `version` Renders the **ReportEntry** `product_version` attribute if set, else display the following hint: `"(Version not available)"`
- `args` Renders the **ReportEntry** `args` attribute as JSON
- `os` Render the **ReportEntry** `os` attribute
- `platform` Renders the **ReportEntry** `platform` attribute
- `client` Renders the **ReportEntry** `client` attribute
- `testcase`
    - If the **ReportEntry** `testcase` attribute is empty, it displays the following hint: `"(Test not available)"`
    - Else if the `testcase` content length is greater than 2048 characters or contains binary content, it displays the following hint: `"See attachment."`
    - Else, it simply renders the `testcase` content
    - Value is editable through the **Content** field located in the **Testcase form section**
- `reportdata`
    - Renders the **ReportEntry** `rawReportData` attribute if set
    - Else, it renders the **ReportEntry** `rawStderr` attribute content
    - Value is editable through the **Content** field located in the **Report data form section**
- `reportdataattached`
    - If the report data is to be attached to the bug, it displays the following hint: `"For detailed report information, see attachment."`
    - Else, it displays: `"(Report data not available)"`
    - Value is editable through the **Do not attach report data** checkbox located in the **Report data form section**
- `metadata*`
    - The `*` is to be replaced with a metadata name
    - If the metadata is available in **ReportEntry** `metadata` attribute as an object key, it renders the value of `ReportEntry.metadata[name]`
    - Else, it renders the following hint: `"(metadata{name} not available)"`
    - **e.g:** With `ReportEntry.metadata = {"path": "test/path"}`, `{{metadatapath}}` renders to `"test/path"` and `{{metadataunknown}}` renders to `"(metadataunknown not available)"`