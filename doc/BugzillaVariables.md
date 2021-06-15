# Bugzilla - Mustache.js variables
In Bugzilla Bug and Comment publication forms, we use [Mustache.js](https://github.com/janl/mustache.js/) to dynamically render various variables in the following fields:
- For bug publication: ***Custom fields*** & ***Description***.
- For comment publication: ***Comment***.

## How to use Mustache variables
To use a Mustache variable (as the ones listed below), you have to surround your variable with double curly brackets:
```
{{myvariable}}
```

Mustache natively HTML-escape the text to be rendered, if you want to render your variable as unescaped HTML, you can surround it with triple curly brackets or append a `&` character before its name:
```
{{{myvariable}}}
{{&myvariable}}
```

If you **don't** want Mustache to interpret your variable, you can change the default delimiter, which is `{{}}`, and restore it immediately after:
```
{{=<% %>=}}
{{myvariable}}
<%={{ }}=%>
```

### Example
Presuming that `var` is a Mustache variable and that its stored value is:
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

> To learn more about Mustache variables, please read the [documentation](https://github.com/janl/mustache.js/#variables).

## Bug - Available variables
### In ***Description*** field
- `summary`: Renders the text displayed in **Summary** `<input/>`. Value is editable through the **Summary** form field.
- `shortsig`: Renders the **CrashEntry** `shortSignature` attribute. Value isn't editable.
- `product`: Renders the **CrashEntry** `product` attribute. Value isn't editable.
- `version`: Renders the **CrashEntry** `product_version` attribute if set, else display the following hint: `"(Version not available)"`. Value isn't editable.
- `args`: Renders the **CrashEntry** `args` attribute as JSON. Value isn't editable.
- `os`: Render the **CrashEntry** `os` attribute. Value isn't editable.
- `platform`: Renders the **CrashEntry** `platform` attribute. Value isn't editable.
- `client`: Renders the **CrashEntry** `client` attribute. Value isn't editable.
- `testcase`: 
    - If the **CrashEntry** `testcase` attribute is empty, it displays the following hint: `"(Test not available)"`
    - Else if the `testcase` content length is greater than 2048 characters, it displays the following hint: `"See attachment."`
    - Else, it simply renders the `testcase` content.
    - Value is editable through the **Content** field located in the **Testcase form section**.
- `crashdata`:
    - If the **CrashEntry** `rawCrashData` attribute is set, it renders its content
    - Else, it renders the **CrashEntry** `rawStderr` attribute content.
    - Value is editable through the **Content** field located in the **Crash data form section**.
- `crashdataattached`:
    - If the crash data is to be attached to the bug, it displays the following hint: `"For detailed crash information, see attachment."`.
    - Else, it displays: `"(Crash data not available)"`.
    - Value is editable through the **Do not attach crash data** checkbox located in the **Crash data form section**.
- `metadata*`:
    - The `*` is to be replaced with a metadata name.
    - If the metadata is available in **CrashEntry** `metadata` attribute as an object key, it renders the value of `CrashEntry.metadata[name]`.
    - Else, it renders the following hint: `"(metadata{name} not available)"`.
    - **e.g:** With `CrashEntry.metadata = {"path": "test/path"}`, `{{metadatapath}}` renders to `"test/path"` and `{{metadataunknown}}` renders to `"(metadataunknown not available)"`.
    - Values aren't editable.

### In ***Custom fields*** field
- `metadata*`:
    - The `*` is to be replaced with a metadata name.
    - If the metadata is available in **CrashEntry** `metadata` attribute as an object key, it renders the value of `CrashEntry.metadata[name]`.
    - Else, it renders the following hint: `"(metadata{name} not available)"`.
    - **e.g:** With `CrashEntry.metadata = {"path": "test/path"}`, `{{metadatapath}}` renders to `"test/path"` and `{{metadataunknown}}` renders to `"(metadataunknown not available)"`.
    - Values aren't editable.

## Comment - Available variables
### In ***Comment*** field
- `summary`: Renders the **BugzillaTemplate** `summary` attribute if set, else renders the **CrashEntry** `shortSignature` attribute. Value isn't editable.
- `shortsig`: Renders the **CrashEntry** `shortSignature` attribute. Value isn't editable.
- `product`: Renders the **CrashEntry** `product` attribute. Value isn't editable.
- `version`: Renders the **CrashEntry** `product_version` attribute if set, else display the following hint: `"(Version not available)"`. Value isn't editable.
- `args`: Renders the **CrashEntry** `args` attribute as JSON. Value isn't editable.
- `os`: Render the **CrashEntry** `os` attribute. Value isn't editable.
- `platform`: Renders the **CrashEntry** `platform` attribute. Value isn't editable.
- `client`: Renders the **CrashEntry** `client` attribute. Value isn't editable.
- `testcase`: 
    - If the **CrashEntry** `testcase` attribute is empty, it displays the following hint: `"(Test not available)"`
    - Else if the `testcase` content length is greater than 2048 characters, it displays the following hint: `"See attachment."`
    - Else, it simply renders the `testcase` content.
    - Value is editable through the **Content** field located in the **Testcase form section**.
- `crashdata`:
    - If the **CrashEntry** `rawCrashData` attribute is set, it renders its content
    - Else, it renders the **CrashEntry** `rawStderr` attribute content.
    - Value is editable through the **Content** field located in the **Crash data form section**.
- `crashdataattached`:
    - If the crash data is to be attached to the bug, it displays the following hint: `"For detailed crash information, see attachment."`.
    - Else, it displays: `"(Crash data not available)"`.
    - Value is editable through the **Do not attach crash data** checkbox located in the **Crash data form section**.
- `metadata*`:
    - The `*` is to be replaced with a metadata name.
    - If the metadata is available in **CrashEntry** `metadata` attribute as an object key, it renders the value of `CrashEntry.metadata[name]`.
    - Else, it renders the following hint: `"(metadata{name} not available)"`.
    - **e.g:** With `CrashEntry.metadata = {"path": "test/path"}`, `{{metadatapath}}` renders to `"test/path"` and `{{metadataunknown}}` renders to `"(metadataunknown not available)"`.
    - Values aren't editable.